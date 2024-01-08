import hashlib
import os
import base64
import hmac
from math import ceil

# Constants
PBKDF2_COMPAT_HASH_ALGORITHM = 'SHA256'
PBKDF2_COMPAT_ITERATIONS = 12000
PBKDF2_COMPAT_SALT_BYTES = 24
PBKDF2_COMPAT_HASH_BYTES = 24


def create_hash(password, force_compat=False):
    salt = base64.b64encode(os.urandom(PBKDF2_COMPAT_SALT_BYTES)).decode('utf-8')
    algo = PBKDF2_COMPAT_HASH_ALGORITHM.lower()
    iterations = PBKDF2_COMPAT_ITERATIONS
    
    pbkdf2 = pbkdf2_default(algo, password, salt, iterations, PBKDF2_COMPAT_HASH_BYTES)
    return f"{algo}:{iterations}:{salt}:{base64.b64encode(pbkdf2).decode('utf-8')}"

def validate_password(password, hash):
    params = hash.split(':')
    if len(params) < 4:
        return False
    
    pbkdf2 = base64.b64decode(params[3])
    pbkdf2_check = pbkdf2_default(params[0], password, params[2], int(params[1]), len(pbkdf2))
    return slow_equals(pbkdf2, pbkdf2_check)

def slow_equals(a, b):
    diff = len(a) ^ len(b)
    for char_a, char_b in zip(a, b):
        # If the inputs are strings, convert characters to ASCII values
        val_a = ord(char_a) if isinstance(char_a, str) else char_a
        val_b = ord(char_b) if isinstance(char_b, str) else char_b
        
        diff |= val_a ^ val_b
    return diff == 0

def needs_upgrade(hash):
    params = hash.split(':')
    if len(params) < 4:
        return True
    
    # You can add more conditions to check if the hash needs an upgrade
    return False

def pbkdf2_default(algo, password, salt, count, key_length):
    if count <= 0 or key_length <= 0:
        raise ValueError('PBKDF2 ERROR: Invalid parameters.')
    
    if isinstance(salt, str):
        salt = salt.encode()
    
    if not algo:
        return pbkdf2_fallback(password, salt, count, key_length)
    
    algo = algo.lower()
    if algo not in hashlib.algorithms_available:
        if algo == 'sha1':
            return pbkdf2_fallback(password, salt, count, key_length)
        else:
            raise ValueError('PBKDF2 ERROR: Hash algorithm not supported.')
    
    hash_length = len(hashlib.new(algo).digest())
    block_count = ceil(key_length / hash_length)
    
    output = b''
    for i in range(1, block_count+1):
        last = salt + i.to_bytes(4, byteorder='big')
        last = xorsum = hmac.new(password.encode(), last, algo).digest()
        for j in range(1, count):
            last = hmac.new(password.encode(), last, algo).digest()
            xorsum = bytes(x ^ y for x, y in zip(xorsum, last))
        output += xorsum
    
    return output[:key_length]

def pbkdf2_fallback(password, salt, count, key_length):
    hash_length = 20  # Length of SHA-1 hash
    block_count = ceil(key_length / hash_length)
    
    if isinstance(salt, str):
        salt = salt.encode()
    
    if len(password) > 64:
        password = hashlib.sha1(password.encode()).digest().ljust(64, b'\0')
    else:
        password = password.encode().ljust(64, b'\0')
    
    opad = bytes(x ^ 0x5C for x in password)
    ipad = bytes(x ^ 0x36 for x in password)
    
    output = b''
    for i in range(1, block_count+1):
        last = salt + i.to_bytes(4, byteorder='big')
        xorsum = last = hashlib.sha1(opad + hashlib.sha1(ipad + last).digest()).digest()
        for j in range(1, count):
            last = hashlib.sha1(opad + hashlib.sha1(ipad + last).digest()).digest()
            xorsum = bytes(x ^ y for x, y in zip(xorsum, last))
        output += xorsum
    
    return output[:key_length]