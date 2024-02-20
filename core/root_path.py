import os
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(override=True)
else:
    load_dotenv("example.env", override=True)

ENV_ROOT_PATH = os.environ.get("ENV_ROOT_PATH", "")
ROOT_PATH = "" if ENV_ROOT_PATH in ["/", ""] else ENV_ROOT_PATH