import base64

from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.ciphers import algorithms, base

class SEED128:
    """
    SEED 복호화 클래스
    - FIXME: cryptography에서 45버전부터 SEED 암호화 알고리즘을 제공하지 않음.
    - KG이니시스 통합인증 데이터 복호화에 사용됨.
    - https://g0yang.tistory.com/48 코드를 참고해서 작성함.
    """
    def __init__(self, iv, key):
        self.iv = bytes(iv, encoding='utf-8')
        self.key = base64.b64decode(key)
        self.seed = algorithms.SEED(self.key)

    def decode(self, mode, text: str):
        """복호화"""
        if not text:
            return ''

        text_b64decode = base64.b64decode(text)
        cipher = base.Cipher(self.seed, mode(self.iv), backend)
        decoded = cipher.decryptor().update(text_b64decode)
        decoded = self.remove_padding(decoded)

        return decoded.decode('utf-8', errors='ignore')

    def remove_padding(self, data):
        """
        PKCS7 패딩 제거
        """
        pad_len = data[-1]
        return data[:-pad_len]
