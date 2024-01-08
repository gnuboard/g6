from fastapi import APIRouter, Request, Query

from core.database import db_session
from core.models import Board, Group, GroupMember
from core.template import UserTemplates
from lib.board_lib import *
from lib.common import *
from lib.member_lib import get_member_level
from lib.template_filters import search_font

router = APIRouter()
templates = UserTemplates()
templates.env.filters["search_font"] = search_font


@router.get("/search")
async def search(
    request: Request,
    db: db_session,
    gr_id: str = Query(None),
    sfl: str = Query("wr_subject||wr_content"),
    stx: str = Query(...),
    sop: str = Query("and"),
    onetable: str = Query(None),
):
    """
    게시판 검색
    """
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    member_level = get_member_level(request)
    total_search_count = 0

    # 게시판 그룹 목록
    groups = db.scalars(
        select(Group)
        .order_by(Group.gr_id)
    ).all()

    # 게시판 목록
    remove_boards = []
    boards_query = (
        select(Board)
        .where(
            Board.bo_use_search == 1,
            Board.bo_list_level <= member_level,
        )
        .order_by(Board.bo_order, Board.gr_id, Board.bo_table)
    )
    if gr_id:
        boards_query = boards_query.where(Board.gr_id == gr_id)
    boards = db.scalars(boards_query).all()

    for board in boards:
        board_config = BoardConfig(request, board)
        board.subject = board_config.subject
        # 그룹접근 사용이면서 그룹관리자도 아니고 그룹회원도 아닌 경우 boards에서 제외
        group = board.group
        if group.gr_use_access and not request.state.is_super_admin:
            is_group_admin = (group.gr_admin == mb_id)
            group_member = db.scalar(
                select(GroupMember).where(
                    GroupMember.gr_id == group.gr_id,
                    GroupMember.mb_id == mb_id
                )
            )
            if not (is_group_admin or group_member):
                remove_boards.append(board)
                continue

        # 게시판 별 검색 Query 설정
        write_model = dynamic_create_write_table(board.bo_table)
        query = write_search_filter(request, write_model, search_field=sfl, keyword=stx, operator=sop)
        query = board_config.get_list_sort_query(write_model, query)
        board.search_count = db.scalar(query.add_columns(func.count()).order_by(None))

        if board.search_count > 0:
            board.writes = db.scalars(query.add_columns(write_model).limit(5)).all()
            total_search_count += board.search_count
            for write in board.writes:
                write = get_list(request, write, board_config)
                if write.wr_is_comment:
                    word = "댓글"
                    parent_write = db.get(write_model, write.wr_parent)
                    write.subject = parent_write.wr_subject
                    write.href = f"/board/{board.bo_table}/{parent_write.wr_id}?{request.query_params}#c_{write.wr_id}"
                else:
                    word = "글"
                    write.href = f"/board/{board.bo_table}/{write.wr_id}?{request.query_params}"

                if "secret" in write.wr_option:
                    write.wr_content = f"[비밀{word} 입니다.]"
        else:
            # 검색 결과가 없으면 remove_boards 추가
            remove_boards.append(board)
            continue

    # boards에서 제외된 게시판 제거
    for board in remove_boards:
        boards.remove(board)

    context = {
        "request": request,
        "onetable": onetable,
        "total_search_count": total_search_count,
        "groups": groups,
        "boards": boards,
    }
    return templates.TemplateResponse("/bbs/search.html", context)
