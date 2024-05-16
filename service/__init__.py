"""서비스 클래스에서 필요한 기능을 제공하는 모듈입니다."""
import abc


class BaseService(metaclass=abc.ABCMeta):
    """
    모든 서비스 클래스의 기본이 되는 추상 기반 클래스입니다.
    """
    @abc.abstractmethod
    def raise_exception(self, status_code: int, detail: str = None):
        """
        서비스 클래스에서 발생할 수 있는 예외를 처리하기 위한 추상 메서드입니다.

        Args:
            status_code (int): HTTP 상태 코드를 나타내는 정수입니다.
            detail (str, optional): 예외 상황에 대한 추가적인 설명을 제공하는 문자열입니다. Defaults to None.
        """
