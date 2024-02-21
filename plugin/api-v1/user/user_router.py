import re
from fastapi import APIRouter, HTTPException, Query
from starlette.requests import Request

from core.template import theme_asset, UserTemplates
from lib.common import dynamic_create_write_table
from lib.pbkdf2 import create_hash
from .. import plugin_config
from ..plugin_config import module_name

from sqlalchemy import or_, select, update, delete, func, DateTime
from core.database import db_session
from core.models import Board, Member
from pydantic import BaseModel
from datetime import datetime


router = APIRouter()

templates = UserTemplates()
templates.env.globals["theme_asset"] = theme_asset

# 모든 게시판 목록을 가져오는 API
@router.get("/boards")
async def read_boards(request: Request, db: db_session, page: int = Query(default=1, ge=1)):
    """
    게시판 목록을 가져오는 API
    """
    # 기본 쿼리 생성
    query = select(Board.bo_table, Board.bo_subject).order_by(Board.bo_table.asc()).limit(10).offset((page - 1) * 10)
    # 쿼리 실행 및 결과 반환
    boards = db.execute(query).mappings().all()
    return {"data": boards}

# 게시판의 글을 가져오는 API
@router.get("/boards/{bo_table}")
async def read_posts(request: Request, db: db_session, bo_table: str, page: int = Query(default=1, ge=1)):
    """
    게시판의 글 목록을 가져오는 API
    """
    query = select(Board).where(Board.bo_table == bo_table)
    board = db.execute(query).scalars().first()
    if not board:
        raise HTTPException(status_code=404, detail=f"Board {bo_table} not found.")

    write_model = dynamic_create_write_table(bo_table)
    query = select(
        write_model.wr_id, 
        write_model.wr_num, 
        write_model.wr_subject, 
        write_model.wr_content, 
        write_model.wr_name, 
        write_model.wr_datetime, 
        # IP 주소 중간 부분 마스킹
        # func.regexp_replace(write_model.wr_ip, '(\\d+)\\.(\\d+)\\.(\\d+)\\.(\\d+)', '\\1.*.*.\\4').label('masked_ip')
        write_model.wr_ip
        ).where(write_model.wr_is_comment == 0).order_by(write_model.wr_num.asc()).limit(10).offset((page - 1) * 10)
    posts = db.execute(query).mappings().all()
    # for post in posts:
    # #     # wr_ip 111.222.333.444 의 가운데 두자리를 * 로 변경
    # #     # 222.333 을 *.* 로 변경.. 정규식으로 처리하는게 더 좋을듯
    #     post["wr_ip"] = re.sub(r'(\d+\.)\d+\.\d+(\.\d+)', r'\1*.*\2', post["wr_ip"])

    # 수정 가능한 딕셔너리 리스트로 변환
    posts_dicts = [dict(post) for post in posts]

    # posts_dicts 내 각 딕셔너리 항목을 순회하며 수정
    for post_dict in posts_dicts:
        # 예시: 'wr_ip' 필드 수정
        post_dict['wr_ip'] = re.sub(r'(\d+\.)\d+\.\d+(\.\d+)', r'\1*.*\2', post_dict['wr_ip'])

    return {"data": posts_dicts}


# @router.get("/boards")
# async def read_boards(request: Request, db: db_session, order_by: str = Query(None)):
#     """
#     게시판 목록을 가져오는 API, 동적으로 정렬 조건 적용
#     유효하지 않은 필드명으로 정렬을 시도할 경우 에러 메시지 반환
#     """
#     # Board 모델의 유효한 필드 목록
#     valid_fields = [column.name for column in Board.__table__.columns]

#     # 기본 쿼리 생성
#     query = select(Board.bo_table, Board.bo_subject)
    
#     # order_by 매개변수가 유효한 필드인지 확인
#     if order_by:
#         if order_by in valid_fields:
#             # 동적으로 정렬 조건 추가
#             order_by_field = getattr(Board, order_by)
#             query = query.order_by(order_by_field.asc())
#         else:
#             # 유효하지 않은 필드명으로 정렬을 시도한 경우 에러 반환
#             # raise HTTPException(status_code=400, detail=f"Invalid order_by field: {order_by}. Valid fields are: {valid_fields}")
#             raise HTTPException(status_code=400, detail=f"Invalid order_by field: {order_by}.")

#     # 수정된 쿼리 실행 및 결과 반환
#     boards = db.execute(query).mappings().all()
#     return {"data": boards}

@router.get("/users")
# def show(request: Request):
#     return {"message": "GET users"}
async def read_users(
    request: Request,
    db: db_session,
    page: int = Query(default=1, ge=1)):
    """
    사용자 요청을 처리하는 경로.
    - page: 쿼리 파라미터로 받은 페이지 번호 (기본값: 1, 1 이상이어야 함)
    """
    # 사용자 데이터를 10개씩 가져옵니다.
    query = select(Member).order_by(Member.mb_no).limit(10).offset((page - 1) * 10)
    # 관리자 데이터가 있어야 되는데 어디갔지?
    # query = select(Member).where(or_(Member.mb_id == "admin", Member.mb_id == "test"))
    members = db.scalars(query).all()
    # 여기에 페이지 번호에 따라 사용자 데이터를 가져오는 로직을 구현합니다.
    # 예를 들어, 페이지 번호에 따라 데이터베이스에서 사용자 정보를 조회할 수 있습니다.
    return {"page": page, "data": members}


class UserCreate(BaseModel):
    mb_id: str
    mb_password: str
    mb_name: str
    mb_nick: str
    mb_ip: str
    mb_datetime: datetime


@router.post("/users")
# def show(request: Request):
#     return templates.TemplateResponse(
#         f"{plugin_config.TEMPLATE_PATH}/user_demo.html",
#         {
#             "request": request,
#             "title": f"Hello plugin Template!",
#             "content": f"Hello {module_name}!",
#         })
async def add_user(
    user: UserCreate, 
    db: db_session,):

    user.mb_password = create_hash(user.mb_password)
    db_user = Member(
        mb_id=user.mb_id,
        mb_password=user.mb_password,
        mb_name=user.mb_name,
        mb_nick=user.mb_nick,
        mb_ip=user.mb_ip,
        mb_datetime=user.mb_datetime
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user