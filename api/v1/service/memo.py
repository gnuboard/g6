from fastapi import HTTPException

from service.memo_service import MemoService


class MemoServiceAPI(MemoService):
    """
    API 요청에 사용되는 MemoService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
