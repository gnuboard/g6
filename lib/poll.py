"""투표 관련 기능을 제공하는 서비스 모듈입니다."""
from typing import List, Tuple

from cachetools import cached, LFUCache
from fastapi import Request
from sqlalchemy import select, insert
from sqlalchemy.orm import Session

from core.database import DBConnect, db_session
from core.models import Member, Poll, PollEtc
from lib.common import get_client_ip
from lib.service import BaseService


class PollService(BaseService):
    """
    투표 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db
        self.poll = None

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        from core.exception import AlertException, AlertCloseException
        if url:
            raise AlertException(detail, status_code, url)
        raise AlertCloseException(detail, status_code)

    def create_poll_etc(self, po_id: int, member: Member, **kwargs) -> PollEtc:
        """
        투표 기타 정보를 생성합니다.
        """
        poll = self.fetch_poll(po_id, member)
        if not poll.po_etc:
            self.raise_exception(status_code=400,
                                 detail="해당 설문조사는 기타의견을 받지 않습니다.")
        if member:
            kwargs.update(pc_name=member.mb_name)

        poll_etc = PollEtc(
            po_id=po_id,
            mb_id=(member.mb_id if member else ''),
            **kwargs
        )
        self.db.add(poll_etc)
        self.db.commit()
        self.db.refresh(poll_etc)

        return poll_etc

    def update_poll(self, po_id: int, item: int, member: Member = None) -> Poll:
        """설문조사 참여하기

        Args:
            po_id (int): 투표 ID
            item (int): 투표 항목 번호
            member (Member, optional): 회원 정보. Defaults to None.

        Returns:
            Poll: 투표 정보
        """
        poll = self.fetch_poll(po_id, member)
        mb_id = getattr(member, "mb_id", None)
        ip = get_client_ip(self.request)

        # 이미 투표한 경우
        if ip in poll.po_ips or (mb_id and mb_id in poll.mb_ids):
            self.raise_exception(
                status_code=403,
                detail=f"{poll.po_subject} 설문조사에 이미 참여하셨습니다.",
                url=f"/bbs/poll_result/{po_id}"
            )
        # 투표 참여정보 업데이트
        if member:
            poll.mb_ids = f"{poll.mb_ids},{mb_id}" if poll.mb_ids else mb_id
        else:
            poll.po_ips = f"{poll.po_ips},{ip}" if poll.po_ips else ip

        # 투표 항목에 1 증가
        setattr(poll, f"po_cnt{item}", getattr(poll, f"po_cnt{item}", 0) + 1)
        self.db.commit()
        self.db.refresh(poll)

        return poll

    def fetch_poll(self, po_id: int, member: Member = None) -> Poll:
        """투표 정보를 조회합니다."""
        if self.poll is None:
            poll = self.db.get(Poll, po_id)
            if not poll:
                self.raise_exception(
                    status_code=404, detail="투표 정보가 없습니다.")
            if poll.po_use != 1:
                self.raise_exception(
                    status_code=403, detail="진행 중인 투표가 아닙니다.")
            if not self.check_poll_permission(poll, member):
                self.raise_exception(
                    status_code=403, detail=f"권한 {poll.po_level} 이상의 회원만 접근하실 수 있습니다.")
            self.poll = poll
        return self.poll

    def fetch_other_polls(self, po_id: int) -> List[Poll]:
        """다른 투표 정보 목록을 조회합니다."""
        other_polls = self.db.scalars(
            select(Poll)
            .where(Poll.po_id != po_id)
            .order_by(Poll.po_id.desc())
        ).all()
        return other_polls

    def check_poll_permission(self, poll: Poll, member: Member = None) -> bool:
        """투표 권한을 확인합니다."""
        level = getattr(member, "mb_level", 1)
        if poll.po_level > 1 and poll.po_level > level:
            return False
        return True

    def get_poll_result(self, poll: Poll) -> Tuple[int, List[dict]]:
        """
        투표 결과를 조회합니다.

        Args:
            poll (Poll): 투표 정보

        Returns:
            Tuple[int, List[dict]]: 총 투표 수, 투표 항목 목록, 
        """
        items = [
            {
                "subject": getattr(poll, f"po_poll{i}"),
                "count": getattr(poll, f"po_cnt{i}", 0),
            }
            for i in range(1, 10) if getattr(poll, f"po_poll{i}", None)
        ]
        total_count = sum(item["count"] for item in items)

        # 각 설문조사 항목의 비율과 순위 계산
        for item in items:
            item["rank"] = sum(
                1 for i in items if i["count"] > item["count"]
            ) + 1
            item["rate"] = round(
                item["count"] / total_count * 100, 1) if total_count > 0 else 0

        return total_count, items

    def delete_poll_etc(self, po_id: int, pc_id: int, member: Member) -> None:
        """
        기타의견을 삭제합니다.
        """
        poll = self.fetch_poll(po_id, member)
        poll_etc = self.db.get(PollEtc, pc_id)

        if poll.po_id != getattr(poll_etc, "po_id", None):
            self.raise_exception(status_code=404, detail="기타의견 정보가 없습니다.")
        if poll_etc.mb_id != member.mb_id and member.mb_level != 10:
            self.raise_exception(status_code=403, detail="작성자만 삭제할 수 있습니다.")

        self.db.delete(poll_etc)
        self.db.commit()

    @staticmethod
    def fetch_latest_poll(db: Session):
        """
        사용 설정된 최신 투표 1건을 조회합니다.
        """
        latest_poll = db.scalar(
            select(Poll)
            .where(Poll.po_use == 1)
            .order_by(Poll.po_id.desc())
        )
        return latest_poll


@cached(LFUCache(maxsize=1))
def get_latest_poll():
    """
    최근 설문조사 정보 1건을 가져오는 함수
    """
    with DBConnect().sessionLocal() as db:
        return PollService.fetch_latest_poll(db)
