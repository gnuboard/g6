"""쪽지 관련 기능을 제공하는 모듈입니다."""
from datetime import datetime
from typing import List, Tuple
from typing_extensions import Annotated

from fastapi import Depends, Request
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError

from core.database import db_session
from core.exception import AlertException
from core.models import Member, Memo
from lib.common import get_client_ip, is_none_datetime
from service import BaseService
from service.member_service import MemberService


class MemoService(BaseService):
    """
    회원 쪽지 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """
    def __init__(self,
                 request: Request,
                 db: db_session,
                 member_service: Annotated[MemberService, Depends()]):
        self.request = request
        self.db = db
        self.config = request.state.config
        self.member_service = member_service

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    def fetch_total_records(self, me_type: str, mb_id: str) -> int:
        """
        쪽지 목록의 총 개수를 데이터베이스에서 조회합니다.
        """
        query = self._base_memos_query(mb_id, me_type)
        return self.db.scalar(query.add_columns(func.count()).select_from(Memo))

    def fetch_memos(self, me_type: str, mb_id: str,
                    offset: int = 0, records_per_page: int = 10):
        """
        쪽지 목록을 조회합니다.
        """
        query = self._base_memos_query(mb_id, me_type)
        return self.db.scalars(
                query.add_columns(Memo)
                .order_by(Memo.me_id.desc())
                .offset(offset).limit(records_per_page)
            ).all()

    def fetch_memo(self, me_id: int):
        """
        쪽지 정보를 데이터베이스에서 조회합니다.
        """
        return self.db.scalar(select(Memo).where(Memo.me_id == me_id))

    def fetch_non_read_memo(self, mb_id: str) -> int:
        """
        읽지 않은 쪽지 수를 데이터베이스에서 조회합니다.
        """
        query = self._base_memos_query(mb_id, 'recv')
        return self.db.scalar(
            query
            .add_columns(func.count(Memo.me_id))
            .where(Memo.me_read_datetime == datetime(1, 1, 1, 0, 0, 0))
        )

    def fetch_prev_next_qa(self, me_id: int, member: Member) -> Tuple[Memo, Memo]:
        """
        이전/다음 쪽지를 데이터베이스에서 조회합니다.
        """
        memo = self.fetch_memo(me_id)
        memo_mb_column = Memo.me_recv_mb_id if memo.me_type == "recv" else Memo.me_send_mb_id
        query = select(Memo).where(
            memo_mb_column == member.mb_id,
            Memo.me_type == memo.me_type
        )
        prev_memo = self.db.scalar(query.where(Memo.me_id < me_id).order_by(Memo.me_id.desc()))
        next_memo = self.db.scalar(query.where(Memo.me_id > me_id).order_by(Memo.me_id.asc()))
        return prev_memo, next_memo

    def read_memo(self, me_id: int, member: Member):
        """
        쪽지를 조회합니다.
        - 쪽지가 로그인 회원의 것이 아니면 예외를 발생합니다.
        """
        memo = self.fetch_memo(me_id)
        if not memo:
            self.raise_exception(404, "쪽지가 존재하지 않습니다.")

        memo_mb_id = memo.me_recv_mb_id if memo.me_type == "recv" else memo.me_send_mb_id
        if not memo_mb_id == member.mb_id:
            self.raise_exception(status_code=403, detail="내 쪽지가 아닙니다.")

        return memo

    def update_read_datetime(self, memo: Memo) -> None:
        """
        쪽지 읽음 처리를 합니다.
        """
        if memo.me_type == 'recv' and is_none_datetime(memo.me_read_datetime):
            memo.me_read_datetime = datetime.now()
            send_memo = self.fetch_memo(memo.me_send_id)
            if send_memo:
                send_memo.me_read_datetime = datetime.now()
            self.db.commit()

    def update_not_read_memos(self, member: Member) -> None:
        """
        읽지 않은 쪽지 수를 갱신합니다.
        """
        try:
            self.db.execute(
                update(Member)
                .values(mb_memo_cnt=self.fetch_non_read_memo(member.mb_id))
                .where(Member.mb_id == member.mb_id)
            )
            self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            self.raise_exception(500, str(e))

    def update_memo_call(self, member: Member, target: Member) -> None:
        """실시간 쪽지 알림을 갱신합니다."""
        target.mb_memo_call = member.mb_id
        target.mb_memo_cnt = self.fetch_non_read_memo(target.mb_id)
        self.db.commit()

    def send_memo(self, member: Member, target: Member, memo: str) -> None:
        """쪽지를 전송합니다."""
        try:
            memo_dict = {
                "me_send_mb_id": member.mb_id,
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
        except SQLAlchemyError as e:
            self.db.rollback()
            self.raise_exception(500, str(e))

    def get_receive_members(self, mb_ids: List[int]) -> List[Member]:
        """쪽지를 받을 회원 목록을 조회합니다."""
        members = []
        not_found_members = []
        for mb_id in mb_ids:
            target = self.member_service.fetch_member_by_id(mb_id)
            if target and target.mb_open and not (target.mb_leave_date or target.mb_intercept_date):
                members.append(target)
            else:
                not_found_members.append(mb_id)

        if not_found_members:
            message = f"{','.join(not_found_members)} : 존재(또는 정보공개)하지 않는 회원이거나 탈퇴/차단된 회원입니다."
            self.raise_exception(status_code=400, detail=message)

        if not members:
            self.raise_exception(status_code=404, detail="쪽지를 전송할 회원이 없습니다.")

        return members

    def calculate_send_point(self, member: Member, count: int) -> int:
        """쪽지 전송에 필요한 포인트를 계산합니다."""
        send_point = getattr(self.config, "cf_memo_send_point", "0")
        total_use_point = int(send_point) * count
        if total_use_point > 0:
            if int(member.mb_point) < total_use_point:
                self.raise_exception(
                    status_code=403, detail=f"보유하신 포인트({member.mb_point})가 부족합니다.")

        return total_use_point

    def delete_memo(self, memo: Memo) -> None:
        """쪽지를 삭제합니다."""
        self.db.delete(memo)
        self.db.commit()

    def delete_memo_call(self, memo: Memo) -> None:
        """실시간 알림을 삭제합니다."""
        try:
            if is_none_datetime(memo.me_read_datetime):
                target_member = self.db.scalar(
                    select(Member)
                    .where(Member.mb_id == memo.me_recv_mb_id,
                           Member.mb_memo_call == memo.me_send_mb_id)
                )
                if target_member:
                    target_member.mb_memo_call = ''
                    self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            self.raise_exception(500, str(e))

    def _base_memos_query(self, mb_id: str, me_type: str):
        """
        쪽지 목록을 조회하는 기본 쿼리를 반환합니다.        
        """
        mb_column = Memo.me_recv_mb_id if me_type == "recv" else Memo.me_send_mb_id
        return select().where(mb_column == mb_id, Memo.me_type == me_type)
