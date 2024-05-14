"""포인트 관련 기능을 제공하는 서비스 모듈입니다."""
import uuid
from datetime import datetime, timedelta
from typing import List
from typing_extensions import Annotated

from fastapi import Depends, Request
from sqlalchemy import delete, func, select, update

from core.database import db_session
from core.exception import AlertException
from core.models import Member, Point
from service import BaseService
from service.member_service import MemberService


class PointService(BaseService):
    """포인트 서비스 클래스"""
    MAX_DATE = "9999-12-31"

    def __init__(
            self,
            request: Request,
            db: db_session,
            member_service: Annotated[MemberService, Depends()]
        ):
        self.request = request
        self.config = request.state.config
        self.db = db
        self.member_service = member_service

        self.use_point = getattr(request.state.config, "cf_use_point", 1)  # 포인트 사용여부
        self.point_term = getattr(request.state.config, "cf_point_term", 0)  # 포인트 유효기간(일)

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        raise AlertException(status_code=status_code, detail=detail, url=url)

    def fetch_total_records(self, member: Member) -> int:
        """
        포인트 목록의 총 개수를 데이터베이스에서 조회합니다.
        """
        return member.points.count()

    def fetch_points(self, member: Member, offset: int = 0, per_page: int = 10):
        """
        포인트 목록을 데이터베이스에서 조회합니다.
        """
        return (member.points
                .order_by(Point.po_id.desc())
                .offset(offset).limit(per_page)
                .all())

    def calculate_sum(self, points: List[Point]) -> dict:
        """
        포인트 목록의 합계를 계산합니다.
        """
        positive = 0
        negative = 0
        for point in points:
            if point.po_point > 0:
                positive += point.po_point
            else:
                negative += point.po_point

        return {"positive": positive, "negative": negative}

    def save_point(self, mb_id: str, point: int, content: str = "",
                   rel_table: str = "", rel_id: str = "", rel_action: str = "",
                   expire: int = 0) -> None:
        """
        포인트를 적립합니다.
        """
        if not self.use_point:  # 포인트 사용여부 체크
            return None
        if point == 0:  # 포인트가 0일 경우
            return None

        member = self.member_service.fetch_member_by_id(mb_id)
        if not member:  # 회원정보가 없을 경우
            return None

        if rel_table or rel_id or rel_action:  # 동일한 내용으로 포인트를 적립한 내역 체크
            point_row = self._fetch_point_by_relation(mb_id, rel_table,
                                                      str(rel_id), rel_action)
            if point_row:
                return None

        # 포인트 내역 추가
        if point > 0:
            po_expired = 0
            po_expire_date = datetime.strptime(self.MAX_DATE, '%Y-%m-%d')
            if self.point_term > 0:
                expire_days = expire if expire > 0 else self.point_term
                after_datetime = timedelta(days=expire_days - 1)
                po_expire_date = (datetime.now() + after_datetime).strftime('%Y-%m-%d')
        else:
            po_expired = 1
            po_expire_date = datetime.now()

        mb_point = self.get_total_point(mb_id)
        po_mb_point = mb_point + point

        new_point = Point(
            mb_id=mb_id,
            po_content=content,
            po_point=point,
            po_use_point=0,
            po_mb_point=po_mb_point,
            po_expired=po_expired,
            po_expire_date=po_expire_date,
            po_rel_table=rel_table,
            po_rel_id=str(rel_id),
            po_rel_action=rel_action
        )
        self.db.add(new_point)

        # 회원 포인트 갱신
        self.member_service.update_member_point(mb_id, po_mb_point)

    def get_total_point(self, mb_id: str) -> int:
        """
        회원의 포인트 총합
        """
        # 만료된 포인트들을 소진 처리
        expire_point = self._fetch_expire_points(mb_id)
        if expire_point > 0:
            self._insert_expire_point(mb_id, expire_point)

        # 만료된 포인트 내역 업데이트
        self._update_expired_points(mb_id)

        # 포인트 총합
        point_sum = self.db.scalar(
            select(func.sum(Point.po_point))
            .where(Point.mb_id == mb_id)
        )

        return int(point_sum) if point_sum else 0

    def insert_use_point(self, mb_id: str, point: int, po_id: int = None) -> None:
        """
        사용한 포인트 내역 입력&업데이트
        """
        using_point = abs(point)
        # 사용할 수 있는 포인트 내역 조회
        query = (
            select(Point).where(
                Point.mb_id == mb_id,
                Point.po_expired == 0,
                Point.po_point > Point.po_use_point
            )
        )
        if po_id:
            query.where(Point.po_id != po_id)

        order_list = [Point.po_id.asc()]
        if self.point_term:
            order_list.insert(0, Point.po_expire_date.asc())

        points = self.db.scalars(query.order_by(*order_list)).all()

        # 포인트 사용처리
        for row in points:
            row_point = row.po_point
            used_point = row.po_use_point

            if (row_point - used_point) > using_point:
                self.db.execute(
                    update(Point).values(po_mb_point=Point.po_mb_point + using_point)
                    .where(Point.po_id == row.po_id)
                )
                self.db.commit()
            else:
                deduction_point = row_point - used_point
                self.db.execute(
                    update(Point).values(
                        po_use_point=(Point.po_use_point + deduction_point),
                        po_expired=100
                    ).where(Point.po_id == row.po_id)
                )
                self.db.commit()
                using_point -= deduction_point

    def delete_point(self, mb_id: str, rel_table: str, rel_id: str, rel_action: str) -> None:
        """
        포인트 내역 삭제
        """
        result = False

        # 포인트 내역정보
        row = self._fetch_point_by_relation(mb_id, rel_table, rel_id, rel_action)
        if row:
            if row.po_point and row.po_point > 0:
                abs_po_point = abs(row.po_point)
                self.delete_use_point(row.mb_id, abs_po_point)
            else:
                if row.po_use_point and row.po_use_point > 0:
                    self.insert_use_point(row.mb_id, row.po_use_point, row.po_id)

            delete_result = self.db.execute(
                delete(Point).where(
                    Point.mb_id == mb_id,
                    Point.po_rel_table == rel_table,
                    Point.po_rel_id == str(rel_id),
                    Point.po_rel_action == rel_action
                )
            )
            self.db.commit()

            if delete_result.rowcount > 0:
                result = True

                # po_mb_point에 반영
                if row.po_point:
                    self.db.execute(
                        update(Point).values(
                            po_mb_point=Point.po_mb_point - row.po_point
                        )
                        .where(Point.mb_id == mb_id, Point.po_id > row.po_id)
                    )
                    self.db.commit()

                # 회원 포인트 총합 갱신
                sum_point = self.get_total_point(mb_id)
                self.member_service.update_member_point(mb_id, sum_point)

        return result

    def delete_use_point(self, mb_id: str, point: int) -> None:
        """
        사용포인트 삭제
        """
        point1 = abs(point)
        query = select(Point).where(
            Point.mb_id == mb_id,
            Point.po_expired != 1,
            Point.po_use_point > 0
        )
        order_list = [Point.po_id.desc()]
        if self.point_term:
            order_list.insert(0, Point.po_expire_date.desc())

        points = self.db.scalars(query.order_by(*order_list)).all()

        for row in points:
            point2 = row.po_use_point
            if (row.po_expired == 100
                and (row.po_expire_date == self.MAX_DATE
                     or row.po_expire_date >= datetime.now())):
                po_expired = 0
            else:
                po_expired = row.po_expired

            if point2 > point1:
                self.db.execute(
                    update(Point).values(
                        po_use_point=Point.po_use_point - point1,
                        po_expired=po_expired
                    )
                    .where(Point.po_id == row.po_id)
                )
                self.db.commit()
                break

            self.db.execute(
                update(Point).values(
                    po_use_point=0,
                    po_expired=po_expired
                )
                .where(Point.po_id == row.po_id)
            )
            self.db.commit()
            point1 = point1 - point2

    def delete_expire_point(self, mb_id: str, point: int):
        """
        소멸 포인트 삭제
        """
        point1 = abs(point)
        points = self.db.scalars(
            select(Point).where(
                Point.mb_id == mb_id,
                Point.po_expired == 1,
                Point.po_point >= 0,
                Point.po_use_point > 0
            ).order_by(Point.po_expire_date.desc(), Point.po_id.desc())
        ).all()

        for row in points:
            point2 = row.po_use_point
            po_expired = 0
            po_expire_date = self.MAX_DATE
            if self.point_term > 0:
                expired = timedelta(days=self.point_term - 1)
                po_expire_date = (datetime.now() + expired).strftime('%Y-%m-%d')
        
            if point2 > point1:
                self.db.execute(
                    update(Point).values(
                        po_use_point=Point.po_use_point - point1,
                        po_expired=po_expired,
                        po_expire_date=po_expire_date
                    )
                    .where(Point.po_id == row.po_id)
                )
                self.db.commit()
                break

            self.db.execute(
                update(Point).values(
                    po_use_point=0,
                    po_expired=po_expired,
                    po_expire_date=po_expire_date
                )
                .where(Point.po_id == row.po_id)
            )
            self.db.commit()
            point1 = point1 - point2

    def _fetch_point_by_relation(self, mb_id: str,
                                 rel_table: str, rel_id: str, rel_action: str):
        """
        포인트 적립 내용으로 내역을 조회합니다.
        """
        return self.db.scalar(
            select(Point)
            .where(Point.mb_id == mb_id,
                    Point.po_rel_table == rel_table,
                    Point.po_rel_id == rel_id,
                    Point.po_rel_action == rel_action)
        )

    def _fetch_expire_points(self, mb_id: str) -> int:
        """
        회원의 만료 예정 포인트 얻기
        """
        if self.point_term <= 0:
            return 0

        point_sum = self.db.scalar(
            select(func.sum(Point.po_point - Point.po_use_point))
            .where(Point.mb_id == mb_id,
                   Point.po_expired == 0,
                   Point.po_expire_date < datetime.now())
        )

        return int(point_sum) if point_sum else 0

    def _insert_expire_point(self, mb_id: str, point: int) -> None:
        """
        만료된 포인트만큼 포인트를 소멸시킵니다.
        """
        member = self.member_service.fetch_member_by_id(mb_id)
        mb_point = member.mb_point if member else 0
        expired_point = point * (-1)
        new_point = Point(
            mb_id=mb_id,
            po_content='포인트 소멸',
            po_point=expired_point,
            po_use_point=0,
            po_mb_point=mb_point + expired_point,
            po_expired=1,
            po_rel_table='@expire',
            po_rel_id=str(mb_id),
            po_rel_action='expire-' + str(uuid.uuid4()),
        )
        self.db.add(new_point)
        self.db.commit()

        # 포인트를 사용한 경우 포인트 내역에 사용금액 기록
        # TODO: 주석처리된 이유를 확인해야 함
        if expired_point < 0:
            # insert_use_point(mb_id, point)
            pass

    def _update_expired_points(self, mb_id: str) -> None:
        if self.point_term <= 0:
            return None

        self.db.execute(
            update(Point).values(po_expired=1)
            .where(Point.mb_id == mb_id,
                   Point.po_expired != 1,
                   Point.po_expire_date != self.MAX_DATE,
                   Point.po_expire_date < datetime.now()
            )
        )
        self.db.commit()

        return None
