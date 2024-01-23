from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, Form, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List

from core.database import DBConnect, db_session
from core.exception import AlertException
from core.models import Board, BoardNew, Scrap, BoardFile, BoardGood
from core.formclass import BoardForm
from core.template import AdminTemplates
from lib.common import *
from lib.board_lib import BoardFileManager
from lib.dependencies import (
    common_search_query_params, get_board, validate_token
)
from lib.template_functions import (
    get_editor_select, get_group_select, 
    get_member_level_select, get_paging, get_skin_select, 
)


router = APIRouter()
templates = AdminTemplates()
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_member_level_select'] = get_member_level_select

BOARD_MENU_KEY = "300100"
FILE_DIRECTORY = "data/file/"


@router.get("/board_list")
async def board_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    게시판관리 목록
    """
    request.session["menu_key"] = BOARD_MENU_KEY

    result = select_query(
        request,
        Board,
        search_params,
        same_search_fields=["gr_id", "bo_table"],
    )

    context = {
        "request": request,
        "boards": result['rows'],
        "total_count": result['total_count'],
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("board_list.html", context)


@router.post("/board_list_update", dependencies=[Depends(validate_token)])
async def board_list_update(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    gr_id: List[str] = Form(None, alias="gr_id[]"),
    bo_table: List[str] = Form(None, alias="bo_table[]"),
    bo_skin: List[str] = Form(None, alias="bo_skin[]"),
    bo_mobile_skin: List[str] = Form(None, alias="bo_mobile_skin[]"),
    bo_subject: List[str] = Form(None, alias="bo_subject[]"),
    bo_read_point: List[str] = Form(None, alias="bo_read_point[]"),
    bo_write_point: List[str] = Form(None, alias="bo_write_point[]"),
    bo_comment_point: List[str] = Form(None, alias="bo_comment_point[]"),
    bo_download_point: List[str] = Form(None, alias="bo_download_point[]"),
    bo_use_sns: List[int] = Form(None, alias="bo_use_sns[]"),
    bo_use_search: List[int] = Form(None, alias="bo_use_search[]"),
    bo_order: List[str] = Form(None, alias="bo_order[]"),
    bo_device: List[str] = Form(None, alias="bo_device[]"),
):
    """
    게시판관리 목록 일괄수정
    """
    for i in checks:
        board = db.get(Board, bo_table[i])
        if board:
            board.gr_id = gr_id[i]
            board.bo_skin = bo_skin[i]
            board.bo_mobile_skin = bo_mobile_skin[i]
            board.bo_subject = bo_subject[i]
            board.bo_read_point = int(
                bo_read_point[i]) if bo_read_point[i] is not None and is_integer_format(bo_read_point[i]) else 0
            board.bo_write_point = int(
                bo_write_point[i]) if bo_write_point[i] is not None and is_integer_format(bo_write_point[i]) else 0
            board.bo_comment_point = int(
                bo_comment_point[i]) if bo_comment_point[i] is not None and is_integer_format(bo_comment_point[i]) else 0
            board.bo_download_point = int(
                bo_download_point[i]) if bo_download_point[i] is not None and is_integer_format(bo_download_point[i]) else 0
            board.bo_use_sns = get_from_list(bo_use_sns, i, 0)
            board.bo_use_search = get_from_list(bo_use_search, i, 0)
            board.bo_order = int(
                bo_order[i]) if bo_order[i] is not None and bo_order[i].isdigit() else 0
            board.bo_device = bo_device[i] if bo_device[i] is not None else ""
            db.commit()

            # 최신글 캐시 삭제
            FileCache().delete_prefix(f'latest-{board.bo_table}')

    url = "/admin/board_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 302)


@router.post("/board_list_delete", dependencies=[Depends(validate_token)])
async def board_list_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    bo_table: List[str] = Form(None, alias="bo_table[]"),
):
    """
    게시판관리 목록 일괄삭제
    """
    from lib.common import _created_models

    for i in checks:
        board = db.get(Board, bo_table[i])
        if board:
            # 게시판 관리 레코드 삭제
            db.delete(board)
            # 최신글 삭제
            db.execute(delete(BoardNew).where(BoardNew.bo_table == board.bo_table))
            # 스크랩 삭제
            db.execute(delete(Scrap).where(Scrap.bo_table == board.bo_table))
            # 파일 삭제
            db.execute(delete(BoardFile).where(BoardFile.bo_table == board.bo_table))
            # 좋아요 기록 삭제
            db.execute(delete(BoardGood).where(BoardGood.bo_table == board.bo_table))

            db.commit()

            # 게시판 테이블 삭제
            write_model = dynamic_create_write_table(table_name=board.bo_table, create_table=False)
            write_model.__table__.indexes.clear()  # 인덱스까지 삭제해야 동일한 table로 재생성시 에러가 안남
            write_model.__table__.drop(DBConnect().engine)
            _created_models.pop(board.bo_table, None)  # 동적 모델 캐싱 삭제

            # 최신글 캐시 삭제
            FileCache().delete_prefix(f'latest-{board.bo_table}')

    url = "/admin/board_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/board_form")
async def board_form(request: Request, db: db_session):
    """
    게시판 등록 폼
    """
    config = request.state.config
    board = {
        "bo_table": "",
        "bo_count_delete": 1,
        "bo_count_modify": 1,
        "bo_read_point": config.cf_read_point,
        "bo_write_point": config.cf_write_point,
        "bo_comment_point": config.cf_comment_point,
        "bo_download_point": config.cf_download_point,
        "bo_gallery_cols": 4,
        "bo_gallery_width": 200,
        "bo_gallery_height": 150,
        "bo_mobile_gallery_width": 125,
        "bo_mobile_gallery_height": 100,
        "bo_table_width": 100,
        "bo_page_rows": config.cf_page_rows,
        "bo_mobile_page_rows": config.cf_mobile_page_rows,
        "bo_subject_len": 60,
        "bo_mobile_subject_len": 30,
        "bo_new": 24,
        "bo_hot": 100,
        "bo_image_width": 600,
        "bo_upload_count": 2,
        "bo_upload_size": 1048576,
        "bo_reply_order": 1,
        "bo_use_search": 1,
        "bo_skin": "basic",
        "bo_mobile_skin": "basic",
        "bo_use_secret": 0,
    }

    context = {
        "request": request,
        "board": board,
        "config": config,
    }
    return templates.TemplateResponse("board_form.html", context)


@router.get("/board_form/{bo_table}")
async def board_form(
    request: Request,
    board: Annotated[Board, Depends(get_board)],
):
    """
    게시판 수정 폼
    """
    context = {
        "request": request,
        "board": board,
        "config": request.state.config,
    }
    return templates.TemplateResponse("board_form.html", context)


@router.post("/board_form_update", dependencies=[Depends(validate_token)])
async def board_form_update(
    request: Request,
    db: db_session,
    action: str = Form(...),
    bo_table: str = Form(...),
    form_data: BoardForm = Depends(),
    chk_grp: List[str] = Form([], alias="chk_grp[]"),
    chk_all: List[str] = Form([], alias="chk_all[]"),
):
    """
    게시판 설정 등록, 수정 처리
    """
    # 등록
    if action == "w":
        existing_board = db.get(Board, bo_table)
        if existing_board:
            raise AlertException(f"{bo_table} 게시판아이디가 이미 존재합니다. (등록불가)", 400)

        # 게시판 설정 등록
        new_board = Board(bo_table=bo_table, **form_data.__dict__)
        db.add(new_board)
        db.commit()

        # 게시판 테이블 생성
        dynamic_create_write_table(table_name=bo_table, create_table=True)

    # 수정
    elif action == "u":
        existing_board = db.get(Board, bo_table)
        if not existing_board:
            raise AlertException(f"{bo_table} 게시판아이디가 존재하지 않습니다. (수정불가)", 404)

        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(existing_board, field, value)
        db.commit()

    else:
        raise AlertException("잘못된 접근입니다.", 400)

    # 그룹적용 체크한 항목이 있다면
    if chk_grp:
        boards = db.scalars(
            select(Board).where(Board.gr_id == form_data.gr_id)
        )
        for board in boards:
            for field in chk_grp:
                setattr(board, field, getattr(form_data, field))
            db.commit()

    # 전체적용 체크한 항목이 있다면
    if chk_all:
        boards = db.scalars(select(Board)).all()
        for board in boards:
            for field in chk_all:
                setattr(board, field, getattr(form_data, field))
            db.commit()

    # 최신글 캐시 삭제
    FileCache().delete_prefix(f'latest-{bo_table}')

    url = f"/admin/board_form/{bo_table}"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/board_copy/{bo_table}")
async def board_copy(
    request: Request,
    board: Annotated[Board, Depends(get_board)],
):
    """
    게시판 복사 폼
    """
    context = {
        "request": request,
        "board": board
    }
    return templates.TemplateResponse("board_copy.html", context)


@router.post("/board_copy_update", dependencies=[Depends(validate_token)])
async def board_copy_update(
    request: Request,
    db: db_session,
    origin_board: Annotated[Board, Depends(get_board)],
    bo_table: str = Form(...),
    target_table: str = Form(...),
    target_subject: str = Form(...),
    copy_case: str = Form(...),
):
    """
    게시판 복사 처리
    """
    target_board = db.get(Board, target_table)
    if target_board:
        raise AlertException(f"{bo_table} 게시판이 이미 존재합니다.", 404)

    # 복사될 레코드의 모든 필드를 딕셔너리로 변환
    target_dict = {key: value for key, value in origin_board.__dict__.items() if not key.startswith('_')}
    
    target_dict['bo_table'] = target_table
    target_dict['bo_subject'] = target_subject

    target_board = Board(**target_dict)
    db.add(target_board)
    db.commit()

    # 새로운 게시판 테이블 생성
    origin_write_model = dynamic_create_write_table(table_name=bo_table, create_table=False)
    target_write_model = dynamic_create_write_table(table_name=target_table, create_table=True)
    # 복사 유형을 '구조와 데이터' 선택시 테이블의 레코드 모두 복사
    if copy_case == 'schema_data_both':
        writes = db.scalars(select(origin_write_model)).all()
        for write in writes:
            copy_data = {column.name: getattr(write, column.name) for column in write.__table__.columns}

            # write 객체로 target_write 테이블에 레코드 추가
            db.execute(target_write_model.__table__.insert(), copy_data)
            db.commit()
            file_manager = BoardFileManager(origin_board, write.wr_id)
            if file_manager.is_exist(bo_table, write.wr_id):
                file_manager.copy_board_files(FILE_DIRECTORY, target_table, write.wr_id)

    content = """
    <script>
        window.opener.location.href = "/admin/board_list";
        window.close();
    </script>
    """

    return HTMLResponse(content=content)
