import logging
import httpx


class ReCaptchaV2:
    """ google recaptcha v2 https://www.google.com/recaptcha/admin
    """

    VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
    TEMPLATE_NAME = 'recaptcha_v2.html'

    @classmethod
    async def verify(cls, recaptcha_secret_key, captcha_response_key: str = None) -> bool:
        """ 캡차 응답 토큰을 전송하여 캡차가 성공적으로 완료되었는지 확인합니다.
        Google recaptcha verify
        Args:
            recaptcha_secret_key (str): recaptcha 비밀키
            captcha_response_key (str): captcha 응답 토큰키
        """
        data = {
            'secret': recaptcha_secret_key,
            'response': captcha_response_key
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(cls.VERIFY_URL, data=data)
                json_result = response.json()
                response.raise_for_status()
                return json_result.get('success', False)

            except Exception as e:
                logging.log(logging.CRITICAL, 'recaptcha v2 error', exc_info=e)
                return False
