from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from common.board_lib import *
from common.common import *
from common.database import get_db
from common.models import Board, Group, GroupMember

router = APIRouter()
templates = MyTemplates(directory=TEMPLATES_DIR)
templates.env.filters["search_font"] = search_font


@router.get("/search")
def search(
    request: Request,
    db: Session = Depends(get_db),
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

    # 게시판 그룹 목록
    groups = db.query(Group).order_by(Group.gr_id).all()

    total_search_count = 0
    # 게시판 목록
    remove_boards = []
    boards_query = db.query(Board).filter(
        Board.bo_use_search == True,
        Board.bo_list_level <= member_level,
    ).order_by(Board.bo_order, Board.gr_id, Board.bo_table)
    if gr_id:
        boards_query = boards_query.filter(Board.gr_id == gr_id)
    boards = boards_query.all()
    for board in boards:
        board_config = BoardConfig(request, board)
        board.subject = board_config.subject
        # 그룹접근 사용이면서 그룹관리자도 아니고 그룹회원도 아닌 경우 boards에서 제외
        group = board.group
        if group.gr_use_access and not request.state.is_super_admin:
            is_group_admin = (group.gr_admin == mb_id)
            group_member = db.query(GroupMember).filter(
                GroupMember.gr_id == group.gr_id,
                GroupMember.mb_id == mb_id
            ).one_or_none()
            if not (is_group_admin or group_member):
                remove_boards.append(board)
                continue

        # 게시판 별 검색 Query 설정
        model_write = dynamic_create_write_table(board.bo_table)
        query = write_search_filter(request, model_write, search_field=sfl, keyword=stx, operator=sop)
        query = board_config.get_list_sort_query(model_write, query)
        board.search_count = query.count()

        if board.search_count > 0:
            board.writes = query.limit(5).all()
            total_search_count += board.search_count
            for write in board.writes:
                write = get_list(request, write, board_config)
                if write.wr_is_comment:
                    word = "댓글"
                    parent_write = db.get(model_write, write.wr_parent)
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

    return templates.TemplateResponse(
        f"{request.state.device}/bbs/search.html",
        {"request": request, "onetable": onetable, "total_search_count": total_search_count, "groups": groups, "boards": boards}
    )