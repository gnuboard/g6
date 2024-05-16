import logging
import httpx

from lib.captcha.base import CaptchaBase


class ReCaptchaInvisible(CaptchaBase):
    """ google recaptcha v2 https://www.google.com/recaptcha/admin
    """

    VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
    TEMPLATE_NAME = 'recaptcha_v2_invisible.html'

    async def verify(self, captcha_response_key: str = None) -> bool:
        """ 캡차 응답 토큰을 전송하여 캡차가 성공적으로 완료되었는지 확인합니다.
        Google recaptcha verify
        Args:
            captcha_response_key (str): captcha 응답 토큰키
        """
        data = {
            'secret': self.recaptcha_secret_key,
            'response': captcha_response_key
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.VERIFY_URL, data=data)
                json_result = response.json()
                response.raise_for_status()
                return json_result.get('success', False)

            except Exception as e:
                logging.log(logging.CRITICAL, 'recaptcha invisible version error', exc_info=e)
                return False
