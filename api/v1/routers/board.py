from typing_extensions import Annotated, Dict

from fastapi import APIRouter, Depends, Request, Path, Query, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, func, select, exists

from core.database import db_session
from core.models import Board, Group, BoardGood, Scrap
from lib.board_lib import BoardConfig, get_list, write_search_filter, is_owner, BoardFileManager
from lib.common import dynamic_create_write_table, cut_name
from lib.dependencies import common_search_query_params
from lib.member_lib import get_admin_type
from lib.template_filters import number_format
from lib.point import insert_point
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


@router.get("/{bo_table}/{wr_id}")
async def api_read_post(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    bo_table: str = Path(...),
    board: Board = Depends(get_board),
    wr_id: str = Path(...),
) -> Dict:
    """
    지정된 게시판의 글을 개별 조회합니다.
    """
    config = request.state.config
    board_config = BoardConfig(request, board)
    
    if not wr_id.isdigit():
        raise HTTPException(status_code=404, detail=f"{wr_id} : 올바르지 않은 게시글 번호입니다.")

    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise HTTPException(status_code=404, detail=f"{wr_id} : 존재하지 않는 게시글입니다.")

    member = member_info["member"]
    mb_id = member_info["mb_id"]
    member_level = member_info["member_level"]
    admin_type = get_admin_type(request, mb_id, board=board)

    if not admin_type and (member_level and member_level < board.bo_read_level):
        raise HTTPException(status_code=403, detail="글을 읽을 권한이 없습니다.")

    # 댓글은 개별조회 할 수 없도록 예외처리
    if write.wr_is_comment:
        raise HTTPException(status_code=404, detail=f"{wr_id} : 존재하지 않는 게시글입니다.")
    
    if ("secret" in write.wr_option
            and not admin_type
            and not is_owner(write, mb_id)):
        owner = False
        if write.wr_reply and mb_id:
            parent_write = db.scalar(
                select(write_model).filter_by(
                    wr_num=write.wr_num,
                    wr_reply="",
                    wr_is_comment=0
                )
            )
            if parent_write.mb_id == mb_id:
                owner = True
        if not owner:
            raise HTTPException(status_code=403, detail="비밀글로 보호된 글입니다.")
        
    # 게시글 정보 설정
    write.ip = board_config.get_display_ip(write.wr_ip)
    write.name = cut_name(request, write.wr_name)

    if config.cf_use_point:
        read_point = board.bo_read_point
        if not board_config.is_read_point(write):
            point = number_format(abs(read_point))
            message = f"게시글 읽기에 필요한 포인트({point})가 부족합니다."
            if not member:
                message += f" 로그인 후 다시 시도해주세요."

            raise HTTPException(status_code=403, detail=message)
        else:
            insert_point(request, mb_id, read_point, f"{board.bo_subject} {write.wr_id} 글읽기", board.bo_table, write.wr_id, "읽기")

    # 조회수 증가
    write.wr_hit = write.wr_hit + 1
    db.commit()

    if member:
        # 스크랩 여부 확인
        exists_scrap = db.scalar(
            exists(Scrap)
            .where(
                Scrap.mb_id == member.mb_id,
                Scrap.bo_table == bo_table,
                Scrap.wr_id == wr_id
            ).select()
        )
        if exists_scrap:
            write.is_scrap = True

        # 추천/비추천 여부 확인
        good_data = db.scalar(
            select(BoardGood)
            .filter_by(bo_table=bo_table, wr_id=wr_id, mb_id=member.mb_id)
        )
        if good_data:
            setattr(write, f"is_{good_data.bg_flag}", True)

    # 파일정보 조회
    images, normal_files = BoardFileManager(board, wr_id).get_board_files_by_type(request)

    # 링크정보 조회
    links = []
    for i in range(1, 3):
        url = getattr(write, f"wr_link{i}")
        hit = getattr(write, f"wr_link{i}_hit")
        if url:
            links.append({"no": i, "url": url, "hit": hit})

    # 댓글 목록 조회
    comments = db.scalars(
        select(write_model).filter_by(
            wr_parent=wr_id,
            wr_is_comment=1
        ).order_by(write_model.wr_comment, write_model.wr_comment_reply)
    ).all()

    for comment in comments:
        comment.name = cut_name(request, comment.wr_name)
        comment.ip = board_config.get_display_ip(comment.wr_ip)
        comment.is_reply = len(comment.wr_comment_reply) < 5 and board.bo_comment_level <= member_level
        comment.is_edit = admin_type or (member and comment.mb_id == member.mb_id)
        comment.is_del = admin_type or (member and comment.mb_id == member.mb_id) or not comment.mb_id 
        comment.is_secret = "secret" in comment.wr_option

        # 비밀댓글 처리
        session_secret_comment_name = f"ss_secret_comment_{bo_table}_{comment.wr_id}"
        parent_write = db.get(write_model, comment.wr_parent)
        if (comment.is_secret
                and not admin_type
                and not is_owner(comment, mb_id)
                and not is_owner(parent_write, mb_id)
                and not request.session.get(session_secret_comment_name)):
            comment.is_secret_content = True
            comment.save_content = "비밀글 입니다."
        else:
            comment.is_secret_content = False
            comment.save_content = comment.wr_content

    contents = jsonable_encoder(write)
    contents.update({
        "images": images,
        "normal_files": normal_files,
        "links": links,
        "comments": comments,
    })
    return contents