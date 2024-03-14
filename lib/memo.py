import abc
from datetime import datetime
from typing import List

from fastapi import Request
from sqlalchemy import func, select, update

from core.database import db_session
from core.models import Member, Memo
from lib.common import get_client_ip, is_none_datetime


class BaseService(metaclass=abc.ABCMeta):
    """
    TODO: member_lib.py 에서 사용되는 BaseService 클래스와 통합할 예정입니다.
    """
    @abc.abstractmethod
    def raise_exception(self, status_code: int, detail: str = None):
        pass


class MemoService(BaseService):
    """
    회원 쪽지 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    - TODO: 쪽지 조회, 읽음처리 기능을 작업할 예정 (API, 기존코드 통합)
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db
        self.memo = None

    def raise_exception(self, status_code: int = 400, detail: str = None):
        from core.exception import AlertException
        raise AlertException(detail, status_code)

    def fetch_memo(self, me_id: int):
        """
        쪽지 정보를 데이터베이스에서 조회합니다.
        """
        if self.memo is None:
            memo = self.db.get(Memo, me_id)
            if not memo:
                self.raise_exception(404, "쪽지가 존재하지 않습니다.")
            self.memo = memo
        return self.memo

    def fetch_non_read_memo(self, mb_id: str) -> int:
        """
        읽지 않은 쪽지 수를 데이터베이스에서 조회합니다.
        """
        return self.db.scalar(
            select(func.count(Memo.me_id))
            .where(
                Memo.me_recv_mb_id == mb_id,
                Memo.me_read_datetime == datetime(1, 1, 1, 0, 0, 0),
                Memo.me_type == 'recv'
            )
        )

    def update_not_read_memos(self, mb_id: str) -> None:
        """
        읽지 않은 쪽지 수를 갱신합니다.
        """
        try:
            self.db.execute(
                update(Member)
                .values(mb_memo_cnt=self.fetch_non_read_memo(mb_id))
                .where(Member.mb_id == mb_id)
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.raise_exception(500, str(e))

    def update_memo_call(self, memo: Memo) -> None:
        """실시간 알림을 삭제합니다."""
        try:
            if is_none_datetime(memo.me_read_datetime):
                target_member = self.db.scalar(
                    select(Member).where(Member.mb_id == memo.me_recv_mb_id,
                                         Member.mb_memo_call == memo.me_send_mb_id)
                )
                if target_member:
                    target_member.mb_memo_call = ''
                    self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.raise_exception(500, str(e))

    def read_memo(self, me_id: int, login_member: Member):
        """
        쪽지를 조회합니다.
        - 쪽지가 로그인 회원의 것이 아니면 예외를 발생합니다.
        """
        memo = self.fetch_memo(me_id)
        memo_mb_id = memo.me_recv_mb_id if memo.me_type == "recv" else memo.me_send_mb_id
        if not memo_mb_id == login_member.mb_id:
            self.raise_exception(status_code=403, detail="내 쪽지가 아닙니다.")
        return memo

    def get_send_members(self, mb_ids: List[int]) -> List[Member]:
        """쪽지를 전송할 회원 목록을 조회합니다."""
        members = []
        not_found_members = []
        for mb_id in mb_ids:
            target = self.db.scalar(select(Member).where(Member.mb_id == mb_id))
            if target and target.mb_open and not (target.mb_leave_date or target.mb_intercept_date):
                members.append(target)
            else:
                not_found_members.append(mb_id)

        if not_found_members:
            self.raise_exception(status_code=400,
                                 detail=f"{','.join(not_found_members)} : 존재(또는 정보공개)하지 않는 회원이거나 탈퇴/차단된 회원입니다.")

        return members

    def get_send_point(self, current_member: Member, count: int) -> int:
        """쪽지 전송에 필요한 포인트를 계산합니다."""
        config = self.request.state.config
        total_use_point = int(config.cf_memo_send_point) * count
        if total_use_point > 0:
            if int(current_member.mb_point) < total_use_point:
                self.raise_exception(
                    status_code=403, detail=f"보유하신 포인트({current_member.mb_point})가 부족합니다.")

        return total_use_point

    def send_memo(self, sender: Member, target: Member, memo: str) -> None:
        """쪽지를 전송합니다."""
        try:
            memo_dict = {
                "me_send_mb_id": sender.mb_id,
                "me_recv_mb_id": target.mb_id,
                "me_memo": memo,
                "me_send_ip": get_client_ip(self.request),
            }
            memo_send = Memo(me_type='send', **memo_dict)
            self.db.add(memo_send)
            self.db.commit()
            memo_recv = Memo(me_type='recv', me_send_id=memo_send.me_id, **memo_dict)
            self.db.add(memo_recv)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.raise_exception(500, str(e))
