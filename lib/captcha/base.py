import abc

from core.models import Config


class CaptchaBase(metaclass=abc.ABCMeta):
    VERIFY_URL = None
    TEMPLATE_NAME = None

    def __init__(self, config: Config) -> None:
        self.recaptcha_secret_key = config.cf_recaptcha_secret_key

    @abc.abstractmethod
    def verify(self, captcha_response_key: str = None) -> bool:
        """캡차 인증을 수행하는 구현 메서드"""
        pass