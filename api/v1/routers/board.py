from typing_extensions import Annotated, Dict

from fastapi import APIRouter, Depends, Request, Path, Query, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, func, select

from core.database import db_session
from core.models import Board, Group
from lib.board_lib import BoardConfig, get_list, write_search_filter
from lib.common import dynamic_create_write_table
from lib.dependencies import common_search_query_params
from lib.member_lib import get_admin_type
from api.v1.dependencies.board import get_member_info, get_board, get_group


router = APIRouter()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

@router.get("/group/{gr_id}")
async def api_group_board_list(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    gr_id: str = Path(...),
    group: Group = Depends(get_group),
) -> Dict:
    """
    게시판그룹의 모든 게시판 목록을 보여줍니다.
    """
    mb_id = member_info["mb_id"]
    member_level = member_info["member_level"]
    admin_type = get_admin_type(request, mb_id, group=group)

    # 그룹별 게시판 목록 조회
    query = (
        select(Board)
        .where(
            Board.gr_id == gr_id,
            Board.bo_list_level <= member_level,
            Board.bo_device != 'mobile'
        )
        .order_by(Board.bo_order)
    )
    # 인증게시판 제외
    if not admin_type:
        query = query.filter_by(bo_use_cert="")

    boards = db.scalars(query).all()
    return jsonable_encoder({"group": group, "boards": boards})


@router.get("/{bo_table}")
async def api_list_post(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    bo_table: str = Path(...),
    board: Board = Depends(get_board),
    spt: int = Query(None),
    search_params: dict = Depends(common_search_query_params),
) -> Dict:
    """
    지정된 게시판의 글 목록을 보여준다.
    """

    # 게시판 정보 조회
    config = request.state.config
    board_config = BoardConfig(request, board)

    mb_id = member_info["mb_id"]
    member_level = member_info["member_level"]
    admin_type = get_admin_type(request, mb_id, board=board)
    
    if not admin_type and member_level < board.bo_list_level:
        raise HTTPException(status_code=403, detail=f"접근 권한이 없습니다.")

    board.subject = board_config.subject
    sca = request.query_params.get("sca")
    sfl = search_params['sfl']
    stx = search_params['stx']
    sst = search_params['sst']
    sod = search_params['sod']
    current_page = search_params['current_page']
    page_rows = board_config.page_rows

    # 게시판 테이블 모델 생성
    write_model = dynamic_create_write_table(bo_table)

    # 공지 게시글 목록 조회
    notice_writes = []
    if current_page == 1:
        notice_ids = board_config.get_notice_list()
        notice_query = select(write_model).where(write_model.wr_id.in_(notice_ids))
        if sca:
            notice_query = notice_query.where(write_model.ca_name == sca)
        notice_writes = [get_list(request, write, board_config) for write in db.scalars(notice_query).all()]

    # 게시글 목록 조회
    query = write_search_filter(request, write_model, sca, sfl, stx)
    # 정렬
    if sst and hasattr(write_model, sst):
        if sod == "desc":
            query = query.order_by(desc(sst))
        else:
            query = query.order_by(asc(sst))
    else:
        query = board_config.get_list_sort_query(write_model, query)

    # 검색일 경우 검색단위 갯수 설정
    prev_spt = None
    next_spt = None
    if (sca or (sfl and stx)):  # 검색일 경우
        search_part = int(config.cf_search_part) or 10000
        min_spt = db.scalar(
            select(func.coalesce(func.min(write_model.wr_num), 0)))
        spt = int(request.query_params.get("spt", min_spt))
        prev_spt = spt - search_part if spt > min_spt else None
        next_spt = spt + search_part if spt + search_part < 0 else None

        # wr_num 컬럼을 기준으로 검색단위를 구분합니다. (wr_num은 음수)
        query = query.where(write_model.wr_num.between(spt, spt + search_part))

        # 검색 내용에 댓글이 잡히는 경우 부모 글을 가져오기 위해 wr_parent를 불러오는 subquery를 이용합니다.
        subquery = select(query.add_columns(write_model.wr_parent).distinct().order_by(None).subquery().alias("subquery"))
        query = select().where(write_model.wr_id.in_(subquery))
    else:   # 검색이 아닌 경우
        query = query.where(write_model.wr_is_comment == 0)

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * page_rows
    # 최종 쿼리 결과를 가져옵니다.
    writes = db.scalars(
        query.add_columns(write_model)
        .offset(offset).limit(page_rows)
    ).all()
    # 전체 게시글 갯수 조회
    total_count = db.scalar(query.add_columns(func.count()).order_by(None))

    # 게시글 정보 수정
    for write in writes:
        write.num = total_count - offset - (writes.index(write))
        write = get_list(request, write, board_config)

    contents = jsonable_encoder({
        "categories": board_config.get_category_list(),
        "board": board,
        "notice_writes": notice_writes,
        "writes": writes,
        "total_count": total_count,
        "current_page": search_params['current_page'],
        "prev_spt": prev_spt,
        "next_spt": next_spt,
    })

    return contents