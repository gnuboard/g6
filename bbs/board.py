# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.
import datetime
from datetime import datetime
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, Form, Path, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select, update

from core.database import db_session
from core.exception import AlertException
from core.formclass import WriteCommentForm
from core.models import Board, BoardGood, Group, Scrap
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
from lib.g5_compatibility import G5Compatibility
from lib.html_sanitizer import content_sanitizer
from response_handlers.board import (
    ListPostTemplate, CreatePostTemplate, ReadPostTemplate,
    UpdatePostTemplate, DeletePostTemplate
)


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
    bo_table: Annotated[str, Path(...)],
    board: Annotated[Board, Depends(get_board)],
    search_params: Annotated[dict, Depends(common_search_query_params)],
):
    list_post_template = ListPostTemplate(
        request, db, bo_table, board, request.state.login_member, search_params
    )
    return list_post_template.response()


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
        if not parent_write:
            raise AlertException("답변할 글이 존재하지 않습니다.", 404)

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


@router.post("/write_update/{bo_table}", dependencies=[Depends(validate_token), Depends(check_group_access)])
async def create_post(
    create_post_template: Annotated[CreatePostTemplate, Depends()],
):
    return create_post_template.response()


@router.post("/write_update/{bo_table}/{wr_id}", dependencies=[Depends(validate_token), Depends(check_group_access)])
async def update_post(
    update_post_template: Annotated[UpdatePostTemplate, Depends()],
):
    return update_post_template.response()


@router.get("/{bo_table}/{wr_id}", dependencies=[Depends(check_group_access)])
async def read_post(
    read_post_template: Annotated[ReadPostTemplate, Depends()]
):
    return read_post_template.response()


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
    delete_post_template = DeletePostTemplate(
        request, db, bo_table, board, wr_id, write, request.state.login_member
    )
    return delete_post_template.response()


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
        comment.wr_content = content_sanitizer.get_cleaned_data(form.wr_content)
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

        comment.wr_content = content_sanitizer.get_cleaned_data(form.wr_content)
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