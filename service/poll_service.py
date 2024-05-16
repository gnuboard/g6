"""설문조사 관련 기능을 제공하는 서비스 모듈입니다."""
from typing import List, Tuple

from cachetools import LRUCache, cached
from cachetools.keys import hashkey
from fastapi import Request
from sqlalchemy import select

from core.database import db_session
from core.exception import AlertException, AlertCloseException
from core.models import Member, Poll, PollEtc
from lib.common import get_client_ip
from service import BaseService


class PollService(BaseService):
    """
    설문조사 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db
        self.poll = None

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        if url:
            raise AlertException(detail, status_code, url)
        raise AlertCloseException(detail, status_code)

    def create_poll_etc(self, poll: Poll, member: Member, **kwargs) -> PollEtc:
        """
        설문조사 기타 정보를 생성합니다.
        """
        if member:
            kwargs.update(pc_name=member.mb_name)

        poll_etc = PollEtc(
            po_id=poll.po_id,
            mb_id=(member.mb_id if member else ''),
            **kwargs
        )
        self.db.add(poll_etc)
        self.db.commit()
        self.db.refresh(poll_etc)

        return poll_etc

    def update_poll(self, poll: Poll, item: int, member: Member = None) -> Poll:
        """설문조사 참여하기

        Args:
            poll (Poll): 설문조사 정보
            item (int): 설문조사 항목 번호
            member (Member, optional): 회원 정보. Defaults to None.

        Returns:
            Poll: 설문조사 정보
        """
        # 설문조사 참여정보 업데이트
        if member:
            mb_id = member.mb_id
            poll.mb_ids = f"{poll.mb_ids},{mb_id}" if poll.mb_ids else mb_id
        else:
            ip = get_client_ip(self.request)
            poll.po_ips = f"{poll.po_ips},{ip}" if poll.po_ips else ip

        # 설문항목에 1 증가
        setattr(poll, f"po_cnt{item}", getattr(poll, f"po_cnt{item}", 0) + 1)
        self.db.commit()
        self.db.refresh(poll)

        return poll

    def fetch_poll(self, po_id: int) -> Poll:
        """설문조사 정보를 데이터베이스에서 조회합니다."""
        return self.db.get(Poll, po_id)

    def read_poll(self, po_id: int) -> Poll:
        """설문조사 정보를 조회합니다."""
        poll = self.fetch_poll(po_id)
        if not poll:
            self.raise_exception(status_code=404, detail="설문조사 정보가 없습니다.")
        return poll

    def fetch_other_polls(self, po_id: int) -> List[Poll]:
        """다른 설문조사 정보 목록을 조회합니다."""
        return self.db.scalars(
            select(Poll)
            .where(Poll.po_id != po_id, Poll.po_use == 1)
            .order_by(Poll.po_id.desc())
        ).all()

    def calculate_poll_result(self, poll: Poll) -> Tuple[int, List[dict]]:
        """
        설문조사 결과를 조회합니다.

        Returns:
            Tuple[int, List[dict]]: 총 투표 수, 설문항목 목록
        """
        # 존재하는 설문항목만 list로 변환
        items = [
            {
                "subject": getattr(poll, f"po_poll{i}"),
                "count": getattr(poll, f"po_cnt{i}", 0),
            }
            for i in range(1, 10) if getattr(poll, f"po_poll{i}", None)
        ]
        total_count = sum(item["count"] for item in items)

        # 각 설문항목의 비율과 순위 계산
        for item in items:
            item["rank"] = sum(1 for i in items if i["count"] > item["count"]) + 1
            item["rate"] = round(item["count"] / total_count * 100, 1) if total_count > 0 else 0

        return total_count, items

    def read_poll_etc(self, pc_id: int) -> PollEtc:
        """
        기타의견을 조회합니다.
        """
        poll_etc = self.db.get(PollEtc, pc_id)
        if not poll_etc:
            self.raise_exception(status_code=404, detail="기타의견 정보가 없습니다.")
        return poll_etc

    def delete_poll_etc(self, poll_etc: PollEtc) -> None:
        """
        기타의견을 삭제합니다.
        """
        self.db.delete(poll_etc)
        self.db.commit()

    @cached(LRUCache(maxsize=1), key=lambda _: hashkey("latest_poll"))
    def fetch_latest_poll(self):
        """
        사용 설정된 최신 설문조사 1건을 조회합니다.
        """
        latest_poll = self.db.scalar(
            select(Poll)
            .where(Poll.po_use == 1)
            .order_by(Poll.po_id.desc())
        )
        return latest_poll


class ValidatePollService(BaseService):
    """
    설문조사 관련 유효성 검사를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        if url:
            raise AlertException(detail, status_code, url)
        raise AlertCloseException(detail, status_code)

    def check_level(self, poll: Poll, member: Member = None) -> bool:
        """
        설문조사 권한레벨을 확인합니다.
        """
        member_level = getattr(member, "mb_level", 1)
        if member_level < poll.po_level:
            self.raise_exception(
                status_code=403,
                detail=f"권한 {poll.po_level} 이상의 회원만 접근하실 수 있습니다."
            )

    def is_used(self, poll: Poll) -> bool:
        """
        사용 설정된 설문조사인지 확인합니다.
        """
        if poll.po_use != 1:
            self.raise_exception(status_code=403, detail="진행 중인 설문조사가 아닙니다.")

    def is_participated(self, poll: Poll, member: Member = None) -> bool:
        """
        설문조사에 이미 참여한 회원인지 확인합니다.
        """
        ip = get_client_ip(self.request)
        mb_id = getattr(member, "mb_id", None)
        po_ip_list = poll.po_ips.split(",") if poll.po_ips else []
        mb_id_list = poll.mb_ids.split(",") if poll.mb_ids else []

        if (ip in po_ip_list) or (mb_id in mb_id_list):
            self.raise_exception(
                status_code=409,
                detail=f"{poll.po_subject} 설문조사에 이미 참여하셨습니다.",
                url=f"/bbs/poll_result/{poll.po_id}"
            )

    def is_used_etc(self, poll: Poll) -> bool:
        """
        기타의견을 받는 설문조사인지 확인합니다.
        """
        if not poll.po_etc:
            self.raise_exception(
                status_code=400,
                detail="해당 설문조사는 기타의견을 사용하지 않습니다."
            )

    def is_etc_owner(self, poll_etc: PollEtc, member: Member) -> bool:
        """
        기타의견 작성자인지 확인합니다.
        """
        if poll_etc.mb_id != member.mb_id and member.mb_level != 10:
            self.raise_exception(
                status_code=403,
                detail="작성자만 삭제할 수 있습니다.")
