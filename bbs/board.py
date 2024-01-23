# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.
import datetime
import html as htmllib
import os
from datetime import datetime
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, File, Form, Path, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import asc, desc, exists, func, select, update

from core.database import db_session
from core.exception import AlertException
from core.formclass import WriteForm, WriteCommentForm
from core.models import AutoSave, Board, BoardGood, Group, Scrap
from core.template import UserTemplates
from lib.board_lib import *
from lib.common import *
from lib.dependencies import (
    check_group_access, common_search_query_params, get_board, get_write,
    validate_captcha, validate_token
)
from lib.pbkdf2 import create_hash
from lib.point import delete_point, insert_point
from lib.template_filters import datetime_format, number_format
from lib.template_functions import get_paging
from lib.g5_compatibility import G5Compatibility

router = APIRouter()
templates = UserTemplates()
templates.env.filters["set_image_width"] = set_image_width
templates.env.filters["url_auto_link"] = url_auto_link
templates.env.globals["get_admin_type"] = get_admin_type
templates.env.globals["get_unique_id"] = get_unique_id
templates.env.globals["board_config"] = BoardConfig
templates.env.globals["get_list_thumbnail"] = get_list_thumbnail
templates.env.globals["captcha_widget"] = captcha_widget

FILE_DIRECTORY = "data/file/"


@router.get("/group/{gr_id}")
async def group_board_list(
    request: Request,
    db: db_session,
    gr_id: str = Path(...)
):
    """
    게시판그룹의 모든 게시판 목록을 보여준다.
    """
    # 게시판 그룹 정보 조회
    group = db.get(Group, gr_id)
    if not group:
        raise AlertException(f"{gr_id} : 존재하지 않는 게시판그룹입니다.", 404)

    # 게시판관리자 검증
    # TODO: 이 부분을 간단하게 개선 => 회원 클래스??
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    member_level = get_member_level(request)
    admin_type = get_admin_type(request, mb_id, group=group)

    # FIXME: 모바일/PC 분기처리
    if not admin_type and request.state.device == 'mobile':
        raise AlertException(f"{group.gr_subject} 그룹은 모바일에서만 접근할 수 있습니다.", 400, url="/")
    
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

    context = {
        "request": request,
        "group": group,
        "boards": boards,
        "render_latest_posts": render_latest_posts
    }
    return templates.TemplateResponse("/board/group.html", context)


@router.get("/{bo_table}")
async def list_post(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(..., title="게시판 아이디"),
    spt: int = Query(None, title="검색단위"),
    search_params: dict = Depends(common_search_query_params),
):
    """
    지정된 게시판의 글 목록을 보여준다.
    """
    # 게시판 정보 조회
    config = request.state.config
    board_config = BoardConfig(request, board)

    if not board_config.is_list_level():
        raise AlertException("목록을 볼 권한이 없습니다.", 403)

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
        subquery = query.add_columns(write_model.wr_parent).distinct().order_by(None).subquery().alias("subquery")
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

    context = {
        "request": request,
        "categories": board_config.get_category_list(),
        "board": board,
        "board_config": board_config,
        "notice_writes": notice_writes,
        "writes": writes,
        "total_count": total_count,
        "current_page": search_params['current_page'],
        "paging": get_paging(request, search_params['current_page'], total_count, page_rows),
        "is_write": board_config.is_write_level(),
        "table_width": board_config.get_table_width,
        "gallery_width": board_config.gallery_width,
        "gallery_height": board_config.gallery_height,
        "prev_spt": prev_spt,
        "next_spt": next_spt,
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/list_post.html", context)


@router.post("/list_delete/{bo_table}", dependencies=[Depends(validate_token)])
async def list_delete(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글을 일괄 삭제한다.
    """
    # 게시판 관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=board)
    if not admin_type:
        raise AlertException("게시판 관리자 이상 접근이 가능합니다.", 403)

    # 게시글 조회
    write_model = dynamic_create_write_table(bo_table)
    writes = db.scalars(
        select(write_model)
        .where(write_model.wr_id.in_(wr_ids))
    ).all()
    for write in writes:
        db.delete(write)
        # 원글 포인트 삭제
        if not delete_point(request, write.mb_id, board.bo_table, write.wr_id, "쓰기"):
            insert_point(request, write.mb_id, board.bo_write_point * (-1), f"{board.bo_subject} {write.wr_id} 글 삭제")
        
        # 파일 삭제
        BoardFileManager(board, write.wr_id).delete_board_files()

        # TODO: 댓글 삭제
    db.commit()

    # 최신글 캐시 삭제
    FileCache().delete_prefix(f'latest-{bo_table}')

    # TODO: 게시글 삭제시 같이 삭제해야할 것들 추가

    query_params = request.query_params
    url = f"/board/{bo_table}"
    return RedirectResponse(
        set_url_query_params(url, query_params), status_code=303)


@router.post("/move/{bo_table}")
async def move_post(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    sw: str = Form(...),
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글 복사/이동
    """
    # 게시판 관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=board)
    if not admin_type:
        raise AlertException("게시판 관리자 이상 접근이 가능합니다.", 403)

    # 게시판 목록 조회
    query = select(Board).join(Group).order_by(Board.gr_id, Board.bo_order, Board.bo_table)
    # 관리자가 속한 게시판 목록만 조회
    if admin_type == "group":
        query = query.where(Group.gr_admin == mb_id)
    elif admin_type == "board":
        query = query.where(Board.bo_admin == mb_id)
    boards = db.scalars(query).all()

    context = {
        "request": request,
        "sw": sw,
        "act": "이동" if sw == "move" else "복사",
        "boards": boards,
        "current_board": board,
        "wr_ids": ','.join(wr_ids)
    }
    return templates.TemplateResponse("/board/move.html", context)


@router.post("/move_update/", dependencies=[Depends(validate_token)])
async def move_update(
    request: Request,
    db: db_session,
    origin_board: Annotated[Board, Depends(get_board)],
    origin_bo_table: str = Form(..., alias="bo_table"),
    sw: str = Form(...),
    wr_ids: str = Form(..., alias="wr_id_list"),
    target_bo_tables: list = Form(..., alias="chk_bo_table[]"),
):
    """
    게시글 복사/이동
    """
    config = request.state.config
    act = "이동" if sw == "move" else "복사"

    # 게시판관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=origin_board)
    if not admin_type:
        raise AlertException("게시판 관리자 이상 접근이 가능합니다.", 403)

    # 입력받은 정보를 토대로 게시글을 복사한다.
    write_model = dynamic_create_write_table(origin_bo_table)
    origin_writes = db.scalars(
        select(write_model)
        .where(write_model.wr_id.in_(wr_ids.split(',')))
    ).all()

    # 게시글 복사/이동 작업 반복
    file_cache = FileCache()
    for target_bo_table in target_bo_tables:
        for origin_write in origin_writes:
            target_write_model = dynamic_create_write_table(target_bo_table)
            target_write = target_write_model()

            # 복사/이동 로그 기록
            if not origin_write.wr_is_comment and config.cf_use_copy_log:
                nick = cut_name(request, member.mb_nick)
                log_msg = f"[이 게시물은 {nick}님에 의해 {datetime_format(datetime.now()) } {origin_board.bo_subject}에서 {act} 됨]"
                if "html" in origin_write.wr_option:
                    log_msg = f'<div class="content_{sw}">' + log_msg + '</div>'
                else:
                    log_msg = '\n' + log_msg

            # 게시글 복사
            initial_field = ["wr_id", "wr_parent"]
            for field in origin_write.__table__.columns.keys():
                if field in initial_field:
                    continue
                elif field == 'wr_content':
                    target_write.wr_content = origin_write.wr_content + log_msg
                elif field == 'wr_num':
                    target_write.wr_num = get_next_num(target_bo_table)
                else:
                    setattr(target_write, field, getattr(origin_write, field))

            if sw == "copy":
                target_write.wr_good = 0
                target_write.wr_nogood = 0
                target_write.wr_hit = 0
                target_write.wr_datetime = datetime.now()

            # 게시글 추가
            db.add(target_write)
            db.commit()
            # 부모아이디 설정
            target_write.wr_parent = target_write.wr_id
            db.commit()

            if sw == "move":
                # 최신글 이동
                db.execute(
                    update(BoardNew)
                    .where(BoardNew.bo_table == origin_board.bo_table, BoardNew.wr_id == origin_write.wr_id)
                    .values(bo_table=target_bo_table, wr_id=target_write.wr_id, wr_parent=target_write.wr_id)
                )
                # 게시글
                if not origin_write.wr_is_comment:
                    # 추천데이터 이동
                    db.execute(
                        update(BoardGood)
                        .where(BoardGood.bo_table == target_bo_table, BoardGood.wr_id == target_write.wr_id)
                        .values(bo_table=target_bo_table, wr_id=target_write.wr_id)
                    )
                    # 스크랩 이동
                    db.execute(
                        update(Scrap)
                        .where(Scrap.bo_table == target_bo_table, Scrap.wr_id == target_write.wr_id)
                        .values(bo_table=target_bo_table, wr_id=target_write.wr_id)
                    )
                # 기존 데이터 삭제
                db.delete(origin_write)
                db.commit()

            # 파일이 존재할 경우
            file_manager = BoardFileManager(origin_board, origin_write.wr_id)
            if file_manager.is_exist():
                if sw == "move":
                    file_manager.move_board_files(FILE_DIRECTORY, target_bo_table, target_write.wr_id)
                else:
                    file_manager.copy_board_files(FILE_DIRECTORY, target_bo_table, target_write.wr_id)

        # 최신글 캐시 삭제
        file_cache.delete_prefix(f'latest-{target_bo_table}')

    # 원본 게시판 최신글 캐시 삭제
    file_cache.delete_prefix(f'latest-{origin_bo_table}')

    context = {
        "request": request,
        "errors": f"해당 게시물을 선택한 게시판으로 {act} 하였습니다."
    }
    return templates.TemplateResponse("alert_close.html", context)


@router.get("/write/{bo_table}", dependencies=[Depends(check_group_access)])
async def write_form_add(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    parent_id: int = Query(None)
):
    """
    게시글을 작성하는 form을 보여준다.
    """
    # 게시판 정보 조회
    board_config = BoardConfig(request, board)

    parent_write = None
    if parent_id:
        # 답글 작성권한 검증
        if not board_config.is_reply_level():
            raise AlertException("답변글을 작성할 권한이 없습니다.", 403)

        # 답글 생성가능여부 검증
        write_model = dynamic_create_write_table(bo_table)
        parent_write = db.get(write_model, parent_id)
        generate_reply_character(board, parent_write)
    else:
        if not board_config.is_write_level():
            raise AlertException("글을 작성할 권한이 없습니다.", 403)

    # TODO: 포인트 검증

    # 게시판 제목 설정
    board.subject = board_config.subject
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board_config.select_editor

    # 게시판 관리자 확인
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=board)

    context = {
        "request": request,
        "categories": board_config.get_category_list(),
        "board": board,
        "write": None,
        "is_notice": True if admin_type and not parent_id else False,
        "is_html": board_config.is_html_level(),
        "is_secret": 1 if is_secret_write(parent_write) else board.bo_use_secret,
        "secret_checked": "checked" if is_secret_write(parent_write) else "",
        "is_mail": board_config.use_email,
        "recv_email_checked": "checked",
        "is_link": board_config.is_link_level(),
        "is_file": board_config.is_upload_level(),
        "is_file_content": bool(board.bo_use_file_content),
        "files": BoardFileManager(board).get_board_files_by_form(),
        "is_use_captcha": board_config.use_captcha,
        "write_min": board_config.write_min,
        "write_max": board_config.write_max,
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/write_form.html", context)


@router.get("/write/{bo_table}/{wr_id}", dependencies=[Depends(check_group_access)])
async def write_form_edit(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    wr_id: int = Path(...)
):
    """
    게시글을 작성하는 form을 보여준다.
    """
    board_config = BoardConfig(request, board)

    # 게시판 관리자 확인
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=board)

    # 게시판 수정 권한
    if not board_config.is_write_level():
        raise AlertException("글을 수정할 권한이 없습니다.", 403)
    if not board_config.is_modify_by_comment(wr_id):
        raise AlertException(f"이 글과 관련된 댓글이 {board.bo_count_modify}건 이상 존재하므로 수정 할 수 없습니다.", 403)

    if not admin_type:
        # 익명 글
        if not write.mb_id:
            if not request.session.get(f"ss_edit_{bo_table}_{wr_id}"):
                query_params = request.query_params
                url = f"/bbs/password/update/{bo_table}/{write.wr_id}"
                return RedirectResponse(
                    set_url_query_params(url, query_params), status_code=303)
        # 회원 글
        elif write.mb_id and not is_owner(write, mb_id):
            raise AlertException("본인 글만 수정할 수 있습니다.", 403)

    # 게시판 제목 설정
    board.subject = board_config.subject
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board_config.select_editor

    # HTML 설정
    html_checked = ""
    html_value = ""
    if "html1" in write.wr_option:
        html_checked = "checked"
        html_value = "html1"
    elif "html2" in write.wr_option:
        html_checked = "checked"
        html_value = "html2"

    context = {
        "request": request,
        "categories": board_config.get_category_list(),
        "board": board,
        "write": write,
        "is_notice": True if not write.wr_reply and admin_type else False,
        "notice_checked": "checked" if board_config.is_board_notice(wr_id) else "",
        "is_html": board_config.is_html_level(),
        "html_checked": html_checked,
        "html_value": html_value,
        "is_secret": 1 if is_secret_write(write) else board.bo_use_secret,
        "secret_checked": "checked" if is_secret_write(write) else "",
        "is_mail": board_config.use_email,
        "recv_email_checked": "checked" if "mail" in write.wr_option else "",
        "is_link": board_config.is_link_level(),
        "is_file": board_config.is_upload_level(),
        "is_file_content": bool(board.bo_use_file_content),
        "files": BoardFileManager(board, wr_id).get_board_files_by_form(),
        "is_use_captcha": False,
        "write_min": board_config.write_min,
        "write_max": board_config.write_max,
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/write_form.html", context)


@router.post(
        "/write_update/{bo_table}",
        dependencies=[Depends(validate_token), Depends(check_group_access)])
async def write_update(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    recaptcha_response: str = Form("", alias="g-recaptcha-response"),
    bo_table: str = Path(...),
    wr_id: str = Form(None),
    parent_id: int = Form(None),
    uid: str = Form(None),
    notice: bool = Form(False),
    html: str = Form(""),
    mail: str = Form(""),
    secret: str = Form(""),
    form_data: WriteForm = Depends(),
    files: List[UploadFile] = File(None, alias="bf_file[]"),
    file_content: list = Form(None, alias="bf_content[]"),
    file_dels: list = Form(None, alias="bf_file_del[]"),
):
    """
    게시글을 Table 추가한다.
    """
    config = request.state.config
    board_config = BoardConfig(request, board)

    # 게시판 관리자 확인
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=board)

    # 비밀글 사용여부 체크
    if not admin_type:
        if not board.bo_use_secret and "secret" in secret and "secret" in html and "secret" in mail:
            raise AlertException("비밀글 미사용 게시판 이므로 비밀글로 등록할 수 없습니다.", 403)
        # 비밀글 옵션에 따라 비밀글 설정
        if board.bo_use_secret == 2:
            secret = "secret"

    # 게시글 내용 검증
    subject_filter_word = filter_words(request, form_data.wr_subject)
    content_filter_word = filter_words(request, form_data.wr_content)
    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise AlertException(f"제목/내용에 금지단어({word})가 포함되어 있습니다.", 400)
    
    # Stored XSS 방지
    form_data.wr_subject = htmllib.escape(form_data.wr_subject)

    # 게시글 테이블 정보 조회
    write_model = dynamic_create_write_table(bo_table)
    # 옵션 설정
    options = [opt for opt in [html, secret, mail] if opt]
    form_data.wr_option = ",".join(map(str, options))

    # 링크 설정
    if not board_config.is_link_level():
        form_data.wr_link1 = ""
        form_data.wr_link2 = ""

    exists_write = db.scalar(
        exists(write_model)
        .where(write_model.wr_id == wr_id).select()
    )
    # 글 등록
    if not exists_write:
        # 글쓰기 간격 검증
        if not is_write_delay(request):
            raise AlertException("너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.", 400)

        # Captcha 검증
        if board_config.use_captcha:
            await validate_captcha(request, recaptcha_response)

        # 글 작성 권한 검증
        if parent_id:
            if not board_config.is_reply_level():
                raise AlertException("답변글을 작성할 권한이 없습니다.", 403)
            parent_write = db.get(write_model, parent_id)
        else:
            if not board_config.is_write_level():
                raise AlertException("글을 작성할 권한이 없습니다.", 403)
            parent_write = None

        # 포인트 검사
        if config.cf_use_point:
            write_point = board.bo_write_point
            if not board_config.is_write_point():
                point = number_format(abs(write_point))
                message = f"글 작성에 필요한 포인트({point})가 부족합니다."
                if not member:
                    message += f"\\n로그인 후 다시 시도해주세요."

                raise AlertException(message, 403)

        form_data.wr_password = create_hash(form_data.wr_password) if form_data.wr_password else ""
        form_data.wr_name = board_config.set_wr_name(member, form_data.wr_name)
        form_data.wr_email = getattr(member, "mb_email", form_data.wr_email)
        form_data.wr_homepage = getattr(member, "mb_homepage", form_data.wr_homepage)

        write = write_model(
            wr_num=parent_write.wr_num if parent_write else get_next_num(bo_table),
            wr_reply=generate_reply_character(board, parent_write) if parent_write else "",
            wr_datetime=datetime.now(),
            mb_id=request.state.login_member.mb_id if member else '',
            wr_ip=request.client.host,
            **form_data.__dict__
        )
        db.add(write)
        db.commit()

        write.wr_parent = write.wr_id  # 부모아이디 설정
        board.bo_count_write = board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        db.commit()

        # 글 작성 시간 기록
        set_write_delay(request)

        # 비밀글은 세션 생성
        if secret:
            request.session[f"ss_secret_{bo_table}_{write.wr_id}"] = True

        # 새글 추가
        insert_board_new(bo_table, write)

        # 글작성 포인트 부여(답변글은 댓글 포인트로 부여)
        if member:
            point = board.bo_comment_point if parent_write else board.bo_write_point
            content = f"{board.bo_subject} {write.wr_id} 글" + ("답변" if parent_write else "쓰기")
            insert_point(request, member.mb_id, point, content, board.bo_table, write.wr_id, "쓰기")

        # 메일 발송
        if board_config.use_email:
            send_write_mail(request, board, write, parent_write)

    # 글 수정
    else:
        if not board_config.is_modify_by_comment(wr_id):
            raise AlertException(f"이 글과 관련된 댓글이 {board.bo_count_modify}건 이상 존재하므로 수정 할 수 없습니다.", 403)

        write = get_write(db, bo_table, wr_id)

        form_data.wr_password = create_hash(form_data.wr_password) if form_data.wr_password else ""

        for field, value in form_data.__dict__.items():
            if value:
                setattr(write, field, value)

        # 분류 수정 시 댓글/답글도 같이 수정
        if form_data.ca_name:
            db.execute(
                update(write_model).where(write_model.wr_parent == wr_id)
                .values(ca_name=form_data.ca_name)
            )
            db.commit()

    # 공지글 설정
    board.bo_notice = board_config.set_board_notice(write.wr_id, notice)
    # 자동저장 글 삭제
    if uid:
        db.execute(delete(AutoSave).where(AutoSave.as_uid == uid))
    db.commit()

    # 업로드 권한 검증
    if board_config.is_upload_level():
        # 업로드 파일처리
        file_manager = BoardFileManager(board, write.wr_id)
        directory = os.path.join(FILE_DIRECTORY, bo_table)
        wr_file = write.wr_file

        # 경로 생성
        make_directory(directory)

        # 파일 삭제
        if file_dels:
            for bf_no in file_dels:
                file_manager.delete_board_file(bf_no)
                wr_file -= 1

        # 파일 업로드 처리 및 파일정보 저장
        exclude_file = {"size": [], "ext": []}
        for file in files:
            index = files.index(file)
            if file.filename:
                # 관리자가 아니면서 설정한 업로드 사이즈보다 크거나 업로드 가능 확장자가 아니면 업로드하지 않음
                if not admin_type:
                    if not file_manager.is_upload_size(file):
                        exclude_file["size"].append(file.filename)
                        continue
                    if not file_manager.is_upload_extension(request, file):
                        exclude_file["ext"].append(file.filename)
                        continue

                board_file = file_manager.get_board_file(index)
                bf_content = file_content[index] if file_content else ""
                filename = file_manager.get_filename(file.filename)
                if board_file:
                    # 기존파일 삭제
                    file_manager.remove_file(board_file.bf_file)
                    # 파일 업로드 및 정보 업데이트
                    file_manager.upload_file(directory, filename, file)
                    file_manager.update_board_file(board_file, directory, filename, file, bf_content)
                else:
                    # 파일 업로드 및 정보 추가
                    file_manager.upload_file(directory, filename, file)
                    file_manager.insert_board_file(index, directory, filename, file, bf_content)
                    wr_file += 1

        # 파일 개수 업데이트
        write.wr_file = wr_file
        db.commit()

    # 최신글 캐시 삭제
    FileCache().delete_prefix(f'latest-{bo_table}')

    # 글쓰기 후 이동할 URL
    query_params = remove_query_params(request, "parent_id")
    url = f"/board/{bo_table}/{write.wr_id}"
    redirect_url = set_url_query_params(url, query_params)

    # exclude_file이 존재하면 파일 업로드 실패 메시지 출력
    if exclude_file:
        msg = ""
        if exclude_file.get("size"):
            msg += f"{','.join(exclude_file['size'])} 파일은 업로드 용량({board.bo_upload_size}byte)을 초과하였습니다.\\n"
        if exclude_file.get("ext"):
            msg += f"{','.join(exclude_file['ext'])} 파일은 업로드 가능 확장자가 아닙니다.\\n"
        if msg:
            raise AlertException(msg, 400, redirect_url)

    return RedirectResponse(redirect_url, status_code=303)


@router.get("/{bo_table}/{wr_id}", dependencies=[Depends(check_group_access)])
async def read_post(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    wr_id: int = Path(...)
):
    """
    게시글을 1개 읽는다.
    """
    config = request.state.config
    board_config = BoardConfig(request, board)
    
    # 게시판 설정
    board.subject = board_config.subject
    write_model = dynamic_create_write_table(bo_table)

    # 게시판 관리자 확인
    member: Member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    member_level = get_member_level(request)
    admin_type = get_admin_type(request, mb_id, board=board)

    # 댓글은 개별조회 할 수 없도록 예외처리
    if write.wr_is_comment:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

    # 읽기 권한 검증
    if not board_config.is_read_level():
        raise AlertException("글을 읽을 권한이 없습니다.", 403)

    # 비밀글 검증
    session_secret_name = f"ss_secret_{bo_table}_{wr_id}"
    if ("secret" in write.wr_option
            and not admin_type
            and not is_owner(write, mb_id)
            and not request.session.get(session_secret_name)):
        # 부모글이 본인글이라면 열람 가능
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
            query_params = request.query_params
            url = f"/bbs/password/view/{bo_table}/{write.wr_id}"
            return RedirectResponse(
                set_url_query_params(url, query_params), status_code=303)

        request.session[session_secret_name] = True

    # 게시글 정보 설정
    write.ip = board_config.get_display_ip(write.wr_ip)
    write.name = cut_name(request, write.wr_name)

    # 세션 체크
    # 한번 읽은 게시글은 세션만료까지 조회수, 포인트 처리를 하지 않는다.
    session_name = f"ss_view_{bo_table}_{wr_id}"
    if not request.session.get(session_name) and mb_id != write.mb_id:
        # 포인트 검사
        if config.cf_use_point:
            read_point = board.bo_read_point
            if not board_config.is_read_point(write):
                point = number_format(abs(read_point))
                message = f"게시글 읽기에 필요한 포인트({point})가 부족합니다."
                if not member:
                    message += f"\\n로그인 후 다시 시도해주세요."

                raise AlertException(message, 403)
            else:
                insert_point(request, mb_id, read_point, f"{board.bo_subject} {write.wr_id} 글읽기", board.bo_table, write.wr_id, "읽기")

        # 조회수 증가
        write.wr_hit = write.wr_hit + 1
        db.commit()

        request.session[session_name] = True

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

    # 이전글 다음글 조회
    prev = None
    next = None
    sca = request.query_params.get("sca")
    sfl = request.query_params.get("sfl")
    stx = request.query_params.get("stx")
    if not board.bo_use_list_view:
        query = select(write_model).where(write_model.wr_is_comment == 0)
        if sca:
            query = query.where(write_model.ca_name == sca)
        if sfl and stx and hasattr(write_model, sfl):
            query = query.where(getattr(write_model, sfl).like(f"%{stx}%"))
         # 같은 wr_num 내에서 이전글 조회
        prev = db.scalar(
            query.where(
                write_model.wr_num == write.wr_num,
                write_model.wr_reply < write.wr_reply,
            ).order_by(desc(write_model.wr_reply))
        )
        if not prev:
            prev = db.scalar(
                query.where(write_model.wr_num < write.wr_num)
                .order_by(desc(write_model.wr_num))
            )
        # 같은 wr_num 내에서 다음글 조회
        next = db.scalar(
            query.where(
                write_model.wr_num == write.wr_num,
                write_model.wr_reply > write.wr_reply,
            ).order_by(asc(write_model.wr_reply))
        )
        if not next:
            next = db.scalar(
                query.where(write_model.wr_num > write.wr_num)
                .order_by(asc(write_model.wr_num))
            )

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

    # TODO: 전체목록보이기 사용 => 게시글 목록 부분을 분리해야함
    write_list = None
    # if member_level >= board.bo_list_level and board.bo_use_list_view:
    #     write_list = list_post(request, db, bo_table, search_params={
    #         "current_page": 1,
    #         "sca": request.query_params.get("sca"),
    #         "sfl": request.query_params.get("sfl"),
    #         "stx": request.query_params.get("stx"),
    #         "sst": request.query_params.get("sst"),
    #         "sod": request.query_params.get("sod"),
    #     }).body.decode("utf-8")

    context = {
        "request": request,
        "board": board,
        "write": write,
        "write_list": write_list,
        "comments": comments,
        "prev": prev,
        "next": next,
        "images": images,
        "files": images + normal_files,
        "links": links,
        "is_write": board_config.is_write_level(),
        "is_reply": board_config.is_reply_level(),
        "is_comment_write": board_config.is_comment_level(),
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/read_post.html", context)


# 게시글 삭제
@router.get("/delete/{bo_table}/{wr_id}", dependencies=[Depends(validate_token)])
async def delete_post(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    wr_id: int = Path(...),
):
    """
    게시글을 삭제한다.
    """
    board_config = BoardConfig(request, board)

    if not board_config.is_delete_by_comment(wr_id):
        raise AlertException(f"이 글과 관련된 댓글이 {board.bo_count_delete}건 이상 존재하므로 삭제 할 수 없습니다.", 403)

    # 게시글 삭제 처리
    delete_write(request, bo_table, write)

    # request.query_params에서 token 제거
    query_params = remove_query_params(request, "token")
    return RedirectResponse(
        set_url_query_params(f"/board/{bo_table}", query_params), status_code=303)


@router.get("/{bo_table}/{wr_id}/download/{bf_no}", dependencies=[Depends(check_group_access)])
async def download_file(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    bf_no: int = Path(...),
):
    """첨부파일 다운로드

    Args:
        db (Session): DB 세션. Depends로 주입
        bo_table (str): 게시판 테이블명
        wr_id (int): 게시글 아이디
        bf_no (int): 파일 순번

    Raises:
        AlertException: 파일이 존재하지 않을 경우

    Returns:
        FileResponse: 파일 다운로드
    """
    config = request.state.config
    board_config = BoardConfig(request, board)

    if not board_config.is_download_level():
        raise AlertException("다운로드 권한이 없습니다.", 403)

    # 파일 정보 조회
    file_manager = BoardFileManager(board, wr_id)
    board_file = file_manager.get_board_file(bf_no)
    if not board_file:
        raise AlertException("파일이 존재하지 않습니다.", 404)

    # 회원 정보
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)

    # 게시물당 포인트가 한번만 차감되도록 세션 설정
    session_name = f"ss_down_{bo_table}_{wr_id}"
    if not request.session.get(session_name):
        # 포인트 검사
        if config.cf_use_point:
            download_point = board.bo_download_point
            if not board_config.is_download_point(write):
                point = number_format(abs(download_point))
                message = f"파일 다운로드에 필요한 포인트({point})가 부족합니다."
                if not member:
                    message += f"\\n로그인 후 다시 시도해주세요."

                raise AlertException(message, 403)
            else:
                insert_point(request, mb_id, download_point, f"{board.bo_subject} {write.wr_id} 파일 다운로드", board.bo_table, write.wr_id, "다운로드")

        request.session[session_name] = True

    download_session_name = f"ss_down_{bo_table}_{wr_id}_{board_file.bf_no}"
    if not request.session.get(download_session_name):
        # 다운로드 횟수 증가
        file_manager.update_download_count(board_file)
        # 파일 다운로드 세션 설정
        request.session[download_session_name] = True

    return FileResponse(board_file.bf_file, filename=board_file.bf_source)


@router.post(
        "/write_comment_update/{bo_table}",
        dependencies=[Depends(validate_token), Depends(check_group_access)])
async def write_comment_update(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    form: WriteCommentForm = Depends(),
    recaptcha_response: str = Form("", alias="g-recaptcha-response"),
):
    """
    댓글 등록
    """
    config = request.state.config
    board_config = BoardConfig(request, board)
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    write_model = dynamic_create_write_table(bo_table)
    compatible_instance = G5Compatibility(db)
    now = compatible_instance.get_wr_last_now(write_model.__tablename__)

    # 댓글 내용 검증
    filter_word = filter_words(request, form.wr_content)
    if filter_word:
        raise AlertException(f"내용에 금지단어({filter_word})가 포함되어 있습니다.", 400)

    if form.w == "c":
        # 글쓰기 간격 검증
        if not is_write_delay(request):
            raise AlertException("너무 빠른 시간내에 댓글을 연속해서 올릴 수 없습니다.", 400)

        # 비회원은 Captcha 유효성 검사
        if not member:
            await validate_captcha(request, recaptcha_response)

        # 댓글 작성 권한 검증
        if not board_config.is_comment_level():
            raise AlertException("댓글을 작성할 권한이 없습니다.", 403)
        
        # 포인트 검사
        comment_point = board.bo_comment_point
        if config.cf_use_point:
            if not board_config.is_comment_point():
                point = number_format(abs(comment_point))
                message = f"댓글 작성에 필요한 포인트({point})가 부족합니다."
                if not member:
                    message += f"\\n로그인 후 다시 시도해주세요."

                raise AlertException(message, 403)

        # 댓글 객체 생성
        comment = write_model()

        if form.comment_id:
            parent_comment = db.get(write_model, form.comment_id)
            if not parent_comment:
                raise AlertException(f"{form.comment_id} : 존재하지 않는 댓글입니다.", 404)

            comment.wr_comment_reply = generate_reply_character(board, parent_comment)
            comment.wr_comment = parent_comment.wr_comment
        else:
            comment.wr_comment = db.scalar(
                select(func.coalesce(func.max(write_model.wr_comment), 0) + 1)
                .where(
                    write_model.wr_parent == form.wr_id,
                    write_model.wr_is_comment == 1
                ))

        # 댓글 추가정보 등록
        comment.ca_name = write.ca_name
        comment.wr_option = form.wr_secret
        comment.wr_num = write.wr_num
        comment.wr_parent = form.wr_id
        comment.wr_is_comment = 1
        comment.wr_content = htmllib.escape(form.wr_content)
        comment.mb_id = getattr(member, "mb_id", "")
        comment.wr_password = create_hash(form.wr_password) if form.wr_password else ""
        comment.wr_name = board_config.set_wr_name(member, form.wr_name)
        comment.wr_email = getattr(member, "mb_email", "")
        comment.wr_homepage = getattr(member, "mb_homepage", "")
        comment.wr_datetime = comment.wr_last = now
        comment.wr_ip = request.client.host
        db.add(comment)

        # 글 작성 시간 기록
        set_write_delay(request)

        # 게시글에 댓글 수 증가
        write.wr_comment = write.wr_comment + 1
        db.commit()

        # 새글 추가
        insert_board_new(bo_table, comment)

        # 포인트 처리
        if member:
            insert_point(request, mb_id, comment_point, f"{board.bo_subject} {comment.wr_parent}-{comment.wr_id} 댓글쓰기", board.bo_table, comment.wr_id, "댓글")

        # 메일 발송
        if board_config.use_email:
            send_write_mail(request, board, comment, write)

    elif form.w == "cu":
        # 댓글 수정
        comment = db.get(write_model, form.comment_id)
        if not comment:
            raise AlertException(f"{form.comment_id} : 존재하지 않는 댓글입니다.", 404)

        comment.wr_content = htmllib.escape(form.wr_content)
        comment.wr_option = form.wr_secret or "html1"
        comment.wr_last = now
        db.commit()

    query_params = request.query_params
    url = f"/board/{bo_table}/{form.wr_id}"
    return RedirectResponse(
        set_url_query_params(url, query_params), status_code=303)


@router.get("/delete_comment/{bo_table}/{wr_id}", dependencies=[Depends(validate_token)])
async def delete_comment(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    comment: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    comment_id: int = Path(..., alias="wr_id"),
):
    """
    댓글 삭제
    """
    write_model = dynamic_create_write_table(bo_table)

    # 게시판관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=board)

    # request.query_params에서 token 제거
    query_params = remove_query_params(request, "token")

    # 게시글 삭제 권한 검증
    if not admin_type:
        # 익명 댓글
        if not comment.mb_id:
            if not request.session.get(f"ss_delete_comment_{bo_table}_{comment_id}"):
                url = f"/bbs/password/comment-delete/{bo_table}/{comment_id}"
                raise AlertException("삭제할 권한이 없습니다.", 403,
                                     set_url_query_params(url, query_params))
        # 회원 댓글
        elif comment.mb_id and not is_owner(comment, mb_id):
            raise AlertException("본인 댓글만 삭제할 수 있습니다.", 403)

    # 댓글 삭제
    db.delete(comment)
    db.commit()

    # 게시글에 댓글 수 감소
    db.execute(
        update(write_model).values(wr_comment=write_model.wr_comment - 1)
        .where(write_model.wr_id == comment.wr_parent)
    )
    db.commit()

    query_params = request.query_params
    url = f"/board/{bo_table}/{comment.wr_parent}"
    return RedirectResponse(
        set_url_query_params(url, query_params), status_code=303)


@router.get("/{bo_table}/{wr_id}/link/{no}")
async def link_url(
    request: Request,
    db: db_session,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    no: int = Path(...)
):
    """
    게시글에 포함된 링크이동
    """
    # 링크정보 조회
    url = getattr(write, f"wr_link{no}")
    if not url:
        raise AlertException("링크가 존재하지 않습니다.", 404)

    # 링크 세션 설정
    link_session_name = f"ss_link_{bo_table}_{wr_id}_{no}"
    if not request.session.get(link_session_name):
        # 링크 횟수 증가
        link_hit = getattr(write, f"wr_link{no}_hit", 0) + 1
        setattr(write, f"wr_link{no}_hit", link_hit)
        db.commit()
        request.session[link_session_name] = True

    # url에 http가 없으면 붙여줌
    if not url.startswith("http"):
        url = "http://" + url

    # 새 창의 외부 URL로 이동
    return RedirectResponse(url, status_code=303)