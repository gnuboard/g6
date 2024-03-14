"""회원 관련 유틸리티 함수를 제공합니다."""
from lib.member_lib import MemberService


class MemberServiceAPI(MemberService):
    """
    API 요청에 사용되는 MemberService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.

    ### Example

    ```python
        @router.get("/members/{mb_id}")
        async def read_member(
            member_service: Annotated[MemberServiceAPI, Depends()],
            current_member: Annotated[Member, Depends(get_current_member)]
        ):
            return member_service.get_member_profile(current_member)
    ```
    """
    def raise_exception(self, status_code: int, detail: str = None):
        super().raise_exception(status_code, detail)