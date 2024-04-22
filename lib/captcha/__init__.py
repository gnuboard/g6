from core.models import Config
from lib.captcha.recaptcha_inv import ReCaptchaInvisible
from lib.captcha.recaptcha_v2 import ReCaptchaV2


def get_current_captcha_cls(config: Config):
    """캡챠 클래스를 반환하는 함수
    Args:
        config (Config) : config 모델
    Returns:
        Optional[class]: 캡차 클래스 or None
    """
    captcha_name = getattr(config, "cf_captcha", "")
    if captcha_name == "recaptcha":
        return ReCaptchaV2
    elif captcha_name == "recaptcha_inv":
        return ReCaptchaInvisible
    else:
        return None


def captcha_widget(request) -> str:
    """템플릿에서 캡차 출력
    Args:
        request (Request): FastAPI Request
    Returns:
        str: 캡차 템플릿 or ''
    """
    cls = get_current_captcha_cls(request.state.config)
    if cls:
        return cls.TEMPLATE_NAME

    return ''  # 템플릿 출력시 비어있을때는 빈 문자열
