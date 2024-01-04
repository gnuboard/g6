import uuid
from datetime import datetime, timedelta

from fastapi import Request
from sqlalchemy import delete, desc, exists, func, select, update

from core.database import DBConnect
from core.models import Member, Point
from lib.member_lib import get_member


def insert_point(request: Request,
                 mb_id: str, point: int, content: str = '',
                 rel_table: str = '', rel_id: str = '', rel_action: str = '',
                 expire: int = 0) -> int:
    """포인트 증감 처리

    Args:
        request (Request): FastAPI Request 객체
        mb_id (str): 회원아이디
        point (int): 증감 포인트
        content (str, optional): 포인트 내용. Defaults to ''.
        rel_table (str, optional): 포인트 관련 테이블. Defaults to ''.
        rel_id (str, optional): 포인트 관련 테이블의 ID. Defaults to ''.
        rel_action (str, optional): 포인트 관련 테이블의 활동. Defaults to ''.
        expire (int, optional): 포인트 유효기간. Defaults to 0.

    Returns:
        int: 성공시 1, 실패시 0
    """
    db = DBConnect().sessionLocal()
    config = request.state.config

    # 포인트를 사용하지 않는다면 종료
    if not config.cf_use_point:
        return 0

    # 포인트가 없다면 업데이트를 할 필요가 없으므로 종료
    if point == 0:
        return 0

    # 회원아이디가 없다면 종료
    if mb_id == '':
        return 0

    # 회원정보가 없다면 종료
    member = db.scalar(select(Member).filter_by(mb_id=mb_id))
    if not member:
        return 0

    if rel_table or rel_id or rel_action:
        existing_point = db.scalar(
            exists(Point.po_id)
            .where(
                Point.mb_id == mb_id,
                Point.po_rel_table == rel_table,
                Point.po_rel_id == str(rel_id),
                Point.po_rel_action == rel_action
            )
            .select()
        )
        if existing_point:
            return -1

    # 포인트 건별 생성
    current_time = datetime.now()
    po_expire_date = datetime.strptime('9999-12-31', '%Y-%m-%d')
    if config.cf_point_term > 0:
        expire_days = expire if expire > 0 else config.cf_point_term
        after_datetime = timedelta(days=expire_days - 1)
        po_expire_date = (current_time + after_datetime).strftime('%Y-%m-%d')

    mb_point = get_point_sum(request, mb_id)
    po_expired = 0
    if point < 0:
        po_expired = 1
        po_expire_date = current_time
    po_mb_point = mb_point + point

    new_point = Point(
        mb_id=mb_id,
        po_datetime=current_time,
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
    db.add(new_point)

    db.execute(
        update(Member).values(mb_point=po_mb_point)
        .where(Member.mb_id == mb_id)
    )
    db.commit()
    db.close()

    return 1


def get_expire_point(request: Request, mb_id: str) -> int:
    """소멸 포인트 얻기"""
    config = request.state.config

    if config.cf_point_term <= 0:
        return 0

    db = DBConnect().sessionLocal()
    point_sum = db.scalar(
        select(func.sum(Point.po_point - Point.po_use_point))
        .where(
            Point.mb_id == mb_id,
            Point.po_expired == 0,
            Point.po_expire_date < datetime.now()
        )
    )
    db.close()
    return int(point_sum) if point_sum else 0


def get_point_sum(request: Request, mb_id: str) -> int:
    """포인트 내역 합계"""
    config = request.state.config
    db = DBConnect().sessionLocal()
    current_time = datetime.now()

    if config.cf_point_term > 0:
        expire_point = get_expire_point(request, mb_id)
        if expire_point > 0:
            member = get_member(mb_id)
            point = expire_point * (-1)
            new_point = Point(
                mb_id=mb_id,
                po_datetime=current_time.strftime("%Y-%m-%d %H:%M:%S"),
                po_content='포인트 소멸',
                po_point=expire_point * (-1),
                po_use_point=0,
                po_mb_point=member.mb_point + point,
                po_expired=1,
                po_expire_date=current_time,
                po_rel_table='@expire',
                po_rel_id=str(mb_id),
                po_rel_action='expire-' + str(uuid.uuid4()),
            )
            db.add(new_point)
            db.commit()

            # 포인트를 사용한 경우 포인트 내역에 사용금액 기록
            # TODO: 주석처리된 이유를 확인해야 함
            if point < 0:
                # insert_use_point(mb_id, point)
                pass

        # 유효기간이 있을 때 기간이 지난 포인트 expired 체크
        db.execute(
            update(Point).values(po_expired=1)
            .where(
                Point.mb_id == mb_id,
                Point.po_expired != 1,
                Point.po_expire_date != '9999-12-31',
                Point.po_expire_date < current_time
            )
        )
        db.commit()

    # 포인트합
    point_sum = db.scalar(
        select(func.sum(Point.po_point))
        .filter_by(mb_id=mb_id)
    )
    db.close()

    return int(point_sum) if point_sum else 0


def insert_use_point(request: Request,
                     mb_id: str, point: int, po_id: str = "") -> None:
    """사용포인트 입력

    Args:
        request (Request): FastAPI Request 객체
        mb_id (str): 회원아이디
        point (int): 사용포인트
        po_id (str, optional): 포인트 내역 ID. Defaults to "".
    """
    config = request.state.config
    db = DBConnect().sessionLocal()
    point1 = abs(point)

    query = (
        select(Point.po_id, Point.po_point, Point.po_use_point)
        .where(
            Point.mb_id == mb_id,
            Point.po_id != po_id,
            Point.po_expired == 0,
            Point.po_point > Point.po_use_point
        )
    )
    if config.cf_point_term:
        query = query.order_by(Point.po_expire_date.asc(), Point.po_id.asc())
    else:
        query = query.order_by(Point.po_id.asc())
    rows = db.scalars(query).all()

    for row in rows:
        point2 = row.po_point
        point3 = row.po_use_point

        if (point2 - point3) > point1:
            db.execute(
                update(Point).values(
                    po_mb_point=Point.po_mb_point + point1
                )
                .where(Point.po_id == row.po_id)
            )
            db.commit()
        else:
            point4 = point2 - point3
            db.execute(
                update(Point).values(
                    po_use_point=(Point.po_use_point + point4),
                    po_expired=100
                )
                .where(Point.po_id == row.po_id)
            )
            db.commit()
            point1 = point1 - point4

    db.close()


def delete_point(request: Request,
                 mb_id: str,
                 rel_table: str, rel_id: str, rel_action: str) -> bool:
    """포인트 삭제

    Args:
        request (Request): FastAPI Request 객체
        mb_id (str): 회원아이디
        rel_table (str): 포인트 관련 테이블.
        rel_id (str): 포인트 관련 테이블의 ID.
        rel_action (str): 포인트 관련 테이블의 활동.

    Returns:
        bool: 성공시 True, 실패시 False
    """
    db = DBConnect().sessionLocal()
    result = False

    if rel_table or rel_id or rel_action:
        # 포인트 내역정보
        row = db.scalar(
            select(Point)
            .where(
                Point.mb_id == mb_id,
                Point.po_rel_table == rel_table,
                Point.po_rel_id == str(rel_id),
                Point.po_rel_action == rel_action
            )
        )
        if row:
            if row.po_point and row.po_point > 0:
                abs_po_point = abs(row.po_point)
                delete_use_point(request, row.mb_id, abs_po_point)
            else:
                if row.po_use_point and row.po_use_point > 0:
                    insert_use_point(request, row.mb_id,
                                     row.po_use_point, row.po_id)

            delete_result = db.execute(
                delete(Point)
                .where(
                    Point.mb_id == mb_id,
                    Point.po_rel_table == rel_table,
                    Point.po_rel_id == str(rel_id),
                    Point.po_rel_action == rel_action
                )
            )
            db.commit()

            if delete_result.rowcount > 0:
                result = True

                # po_mb_point에 반영
                if row.po_point:
                    db.execute(
                        update(Point).values(
                            po_mb_point=Point.po_mb_point - row.po_point
                        )
                        .where(Point.mb_id == mb_id, Point.po_id > row.po_id)
                    )
                    db.commit()

                # 포인트 내역의 합을 구하고
                sum_point = get_point_sum(request, mb_id)

                # 포인트 UPDATE
                db.execute(
                    update(Member).values(mb_point=sum_point)
                    .where(Member.mb_id == mb_id)
                )
                db.commit()
    db.close()

    return result


def delete_use_point(request: Request, mb_id: str, point: int):
    """사용포인트 삭제

    Args:
        request (Request): FastAPI Request 객체
        mb_id (str): 회원아이디
        point (int): 사용포인트
    """
    config = request.state.config
    db = DBConnect().sessionLocal()
    current_time = datetime.now()

    point1 = abs(point)
    query = select(Point).where(
        Point.mb_id == mb_id,
        Point.po_expired != 1,
        Point.po_use_point > 0
    )
    if config.cf_point_term:
        query = query.order_by(desc(Point.po_expire_date), desc(Point.po_id))
    else:
        query = query.order_by(desc(Point.po_id))
    rows = db.scalars(query).all()

    for row in rows:
        point2 = row.po_use_point
        if row.po_expired == 100 and (row.po_expire_date == '9999-12-31' or row.po_expire_date >= current_time):
            po_expired = 0
        else:
            po_expired = row.po_expired

        if point2 > point1:
            db.execute(
                update(Point).values(
                    po_use_point=Point.po_use_point - point1,
                    po_expired=po_expired
                )
                .where(Point.po_id == row.po_id)
            )
            db.commit()
            break
        else:
            db.execute(
                update(Point).values(
                    po_use_point=0,
                    po_expired=po_expired
                )
                .where(Point.po_id == row.po_id)
            )
            db.commit()
            point1 = point1 - point2

    db.close()


def delete_expire_point(request: Request, mb_id: str, point: int):
    """소멸포인트 삭제

    Args:
        request (Request): FastAPI Request 객체
        mb_id (str): 회원아이디
        point (int): 소멸포인트
    """
    config = request.state.config
    db = DBConnect().sessionLocal()
    current_time = datetime.now()

    point1 = abs(point)
    rows = db.scalars(
        select(Point).where(
            Point.mb_id == mb_id,
            Point.po_expired == 1,
            Point.po_point >= 0,
            Point.po_use_point > 0
        ).order_by(desc(Point.po_expire_date), desc(Point.po_id))
    ).all()
    for row in rows:
        point2 = row.po_use_point
        po_expired = 0
        po_expire_date = '9999-12-31'
        if config.cf_point_term > 0:
            expired = timedelta(days=config.cf_point_term - 1)
            po_expire_date = (current_time + expired).strftime('%Y-%m-%d')
    
        if point2 > point1:
            db.execute(
                update(Point).values(
                    po_use_point=Point.po_use_point - point1,
                    po_expired=po_expired,
                    po_expire_date=po_expire_date
                )
                .where(Point.po_id == row.po_id)
            )
            db.commit()
            break
        else:
            db.execute(
                update(Point).values(
                    po_use_point=0,
                    po_expired=po_expired,
                    po_expire_date=po_expire_date
                )
                .where(Point.po_id == row.po_id)
            )
            db.commit()
            point1 = point1 - point2

    db.close()
