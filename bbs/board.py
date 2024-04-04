# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.
from typing_extensions import Annotated, List

from fastapi import APIRouter, Depends, Request, Form, Path, Query, File, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from core.database import db_session
from core.exception import AlertException
from core.formclass import WriteForm, WriteCommentForm
from core.models import Board, Group, Member, WriteBaseModel
from core.template import UserTemplates
from lib.member_lib import get_admin_type
from lib.board_lib import (
    set_image_width, url_auto_link, BoardConfig, get_list_thumbnail,
    render_latest_posts, generate_reply_character, is_secret_write,
    BoardFileManager, is_owner, insert_board_new, set_write_delay
)
from lib.common import (
    set_url_query_params, get_unique_id, captcha_widget, remove_query_params
)
from lib.dependencies import (
    check_group_access, common_search_query_params,
    validate_captcha, validate_token, check_login_member,
    get_write, get_login_member
)
from lib.template_functions import get_paging
from service.board import (
    ListPostService, CreatePostService, ReadPostService,
    UpdatePostService, DeletePostService, GroupBoardListService,
    CommentService, DeleteCommentService, ListDeleteService,
    MoveUpdateService, DownloadFileService
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
    group_board_list_service = GroupBoardListService(
        request, db, gr_id, request.state.login_member
    )
    group = group_board_list_service.group
    group_board_list_service.check_mobile_only()
    boards = group_board_list_service.get_boards_in_group()

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
    search_params: Annotated[dict, Depends(common_search_query_params)],
):
    """해당 게시판의 게시글 목록을 보여준다."""
    list_post_service = ListPostService(
        request, db, bo_table, request.state.login_member, search_params
    )
    board = list_post_service.board

    context = {
        "request": request,
        "categories": list_post_service.categories,
        "board": board,
        "board_config": list_post_service,
        "notice_writes": list_post_service.get_notice_writes(search_params),
        "writes": list_post_service.get_writes(search_params),
        "total_count": list_post_service.get_total_count(),
        "current_page": search_params['current_page'],
        "paging": get_paging(request, search_params['current_page'], list_post_service.get_total_count(), list_post_service.page_rows),
        "is_write": list_post_service.is_write_level(),
        "table_width": list_post_service.get_table_width,
        "gallery_width": list_post_service.gallery_width,
        "gallery_height": list_post_service.gallery_height,
        "prev_spt": list_post_service.prev_spt,
        "next_spt": list_post_service.next_spt,
    }

    return templates.TemplateResponse(f"/board/{board.bo_skin}/list_post.html", context)


@router.post("/list_delete/{bo_table}", dependencies=[Depends(validate_token)])
async def list_delete(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글을 일괄 삭제한다.
    """
    list_delete_service = ListDeleteService(
        request, db, bo_table, request.state.login_member
    )
    list_delete_service.validate_admin_authority()
    list_delete_service.delete_writes(wr_ids)

    query_params = request.query_params
    url = f"/board/{bo_table}"
    return RedirectResponse(
        set_url_query_params(url, query_params), status_code=303)


@router.post("/move/{bo_table}")
async def move_post(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    sw: str = Form(...),
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글 복사/이동
    """
    move_update_service = MoveUpdateService(
        request, db, bo_table, request.state.login_member, sw
    )
    # 게시판 관리자 검증
    mb_id = move_update_service.mb_id
    admin_type = move_update_service.admin_type
    move_update_service.validate_admin_authority()

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
        "act": move_update_service.act,
        "boards": boards,
        "current_board": move_update_service.board,
        "wr_ids": ','.join(wr_ids)
    }
    return templates.TemplateResponse("/board/move.html", context)


@router.post("/move_update/", dependencies=[Depends(validate_token)])
async def move_update(
    request: Request,
    db: db_session,
    origin_bo_table: str = Form(..., alias="bo_table"),
    sw: str = Form(...),
    wr_ids: str = Form(..., alias="wr_id_list"),
    target_bo_tables: list = Form(..., alias="chk_bo_table[]"),
):
    """
    게시글 복사/이동
    """
    member = request.state.login_member
    move_update_service = MoveUpdateService(
        request, db, origin_bo_table, member, sw
    )
    move_update_service.validate_admin_authority()
    origin_writes = move_update_service.get_origin_writes(wr_ids)
    move_update_service.move_copy_post(target_bo_tables, origin_writes)
    context = {
        "request": request,
        "errors": f"해당 게시물을 선택한 게시판으로 {move_update_service.act} 하였습니다."
    }
    return templates.TemplateResponse("alert_close.html", context)


@router.get("/write/{bo_table}", dependencies=[Depends(check_group_access)])
async def write_form_add(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    parent_id: int = Query(None)
):
    """
    게시글을 작성하는 form을 보여준다.
    """
    create_post_service = CreatePostService(
        request, db, bo_table, request.state.login_member
    )

    board = create_post_service.board
    parent_write = None
    if parent_id:
        parent_write = create_post_service.get_parent_post(parent_id)
        generate_reply_character(board, parent_write)
    else:
        create_post_service.validate_write_level()

    # TODO: 포인트 검증

    # 게시판 제목 설정
    board.subject = create_post_service.subject
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = create_post_service.select_editor

    # 게시판 관리자 확인
    admin_type = create_post_service.admin_type

    context = {
        "request": request,
        "categories": create_post_service.get_category_list(),
        "board": board,
        "write": None,
        "is_notice": True if admin_type and not parent_id else False,
        "is_html": create_post_service.is_html_level(),
        "is_secret": 1 if is_secret_write(parent_write) else board.bo_use_secret,
        "secret_checked": "checked" if is_secret_write(parent_write) else "",
        "is_mail": create_post_service.use_email,
        "recv_email_checked": "checked",
        "is_link": create_post_service.is_link_level(),
        "is_file": create_post_service.is_upload_level(),
        "is_file_content": bool(board.bo_use_file_content),
        "files": BoardFileManager(board).get_board_files_by_form(),
        "is_use_captcha": create_post_service.use_captcha,
        "write_min": create_post_service.write_min,
        "write_max": create_post_service.write_max,
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/write_form.html", context)


@router.get("/write/{bo_table}/{wr_id}", dependencies=[Depends(check_group_access)])
async def write_form_edit(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    wr_id: int = Path(...)
):
    """
    게시글을 작성하는 form을 보여준다.
    """
    update_post_service = UpdatePostService(
        request, db, bo_table, request.state.login_member, wr_id,
    )

    board = update_post_service.board
    write = update_post_service.get_write(wr_id)

    # 게시판 수정 권한
    update_post_service.validate_write_level()
    update_post_service.validate_restrict_comment_count()

    # 게시판 관리자 확인
    admin_type = update_post_service.admin_type
    if not admin_type:
        # 익명 글
        if not write.mb_id:
            if not request.session.get(f"ss_edit_{bo_table}_{wr_id}"):
                query_params = request.query_params
                url = f"/bbs/password/update/{bo_table}/{write.wr_id}"
                return RedirectResponse(
                    set_url_query_params(url, query_params), status_code=303)
        # 회원 글
        elif write.mb_id and not is_owner(write, update_post_service.mb_id):
            raise AlertException("본인 글만 수정할 수 있습니다.", 403)

    # 게시판 제목 설정
    board.subject = update_post_service.subject
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = update_post_service.select_editor

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
        "categories": update_post_service.get_category_list(),
        "board": board,
        "write": write,
        "is_notice": True if not write.wr_reply and admin_type else False,
        "notice_checked": "checked" if update_post_service.is_board_notice(wr_id) else "",
        "is_html": update_post_service.is_html_level(),
        "html_checked": html_checked,
        "html_value": html_value,
        "is_secret": 1 if is_secret_write(write) else board.bo_use_secret,
        "secret_checked": "checked" if is_secret_write(write) else "",
        "is_mail": update_post_service.use_email,
        "recv_email_checked": "checked" if "mail" in write.wr_option else "",
        "is_link": update_post_service.is_link_level(),
        "is_file": update_post_service.is_upload_level(),
        "is_file_content": bool(board.bo_use_file_content),
        "files": BoardFileManager(board, wr_id).get_board_files_by_form(),
        "is_use_captcha": False,
        "write_min": update_post_service.write_min,
        "write_max": update_post_service.write_max,
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/write_form.html", context)


@router.post("/write_update/{bo_table}", dependencies=[Depends(validate_token), Depends(check_group_access)])
async def create_post(
    request: Request,
    db: db_session,
    form_data: Annotated[WriteForm, Depends()],
    member: Annotated[Member, Depends(check_login_member)],
    bo_table: str = Path(...),
    parent_id: int = Form(None),
    notice: bool = Form(False),
    secret: str = Form(""),
    html: str = Form(""),
    mail: str = Form(""),
    uid: str = Form(None),
    files: List[UploadFile] = File(None, alias="bf_file[]"),
    file_content: list = Form(None, alias="bf_content[]"),
    file_dels: list = Form(None, alias="bf_file_del[]"),
    recaptcha_response: str = Form("", alias="g-recaptcha-response"),
):
    """게시글을 작성한다."""
    create_post_service = CreatePostService(
        request, db, bo_table, member
    )
    create_post_service.validate_captcha(recaptcha_response)
    create_post_service.validate_write_delay()
    create_post_service.validate_write_level()
    create_post_service.validate_secret_board(secret, html, mail)
    create_post_service.validate_post_content(form_data.wr_subject)
    create_post_service.validate_post_content(form_data.wr_content)
    create_post_service.is_write_level()
    create_post_service.arrange_data(form_data, secret, html, mail)
    write = create_post_service.save_write(parent_id, form_data)
    insert_board_new(bo_table, write)
    create_post_service.add_point(write)
    create_post_service.send_write_mail_(write, parent_id)
    create_post_service.set_notice(write.wr_id, notice)
    set_write_delay(create_post_service.request)
    create_post_service.delete_auto_save(uid)
    create_post_service.save_secret_session(write.wr_id, secret)
    create_post_service.upload_files(write, files, file_content, file_dels)
    create_post_service.delete_cache()
    redirect_url = create_post_service.get_redirect_url(write)
    db.commit()
    return RedirectResponse(redirect_url, status_code=303)


@router.post("/write_update/{bo_table}/{wr_id}", dependencies=[Depends(validate_token), Depends(check_group_access)])
async def update_post(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    bo_table: str = Path(...),
    wr_id: str = Path(...),
    notice: bool = Form(False),
    secret: str = Form(""),
    html: str = Form(""),
    mail: str = Form(""),
    form_data: WriteForm = Depends(),
    uid: str = Form(None),
    files: List[UploadFile] = File(None, alias="bf_file[]"),
    file_content: list = Form(None, alias="bf_content[]"),
    file_dels: list = Form(None, alias="bf_file_del[]"),
):
    """게시글을 수정한다."""
    update_post_service = UpdatePostService(
        request, db, bo_table, member, wr_id,
    )
    write = get_write(db, bo_table, wr_id)
    update_post_service.validate_author(write)
    update_post_service.validate_restrict_comment_count()
    update_post_service.validate_secret_board(secret, html, mail)
    update_post_service.validate_post_content(form_data.wr_subject)
    update_post_service.validate_post_content(form_data.wr_content)
    update_post_service.arrange_data(form_data, secret, html, mail)
    update_post_service.save_secret_session(wr_id, secret)
    update_post_service.save_write(write, form_data)
    update_post_service.set_notice(write.wr_id, notice)
    update_post_service.delete_auto_save(uid)
    update_post_service.upload_files(write, files, file_content, file_dels)
    update_post_service.update_children_category(form_data)
    update_post_service.delete_cache()
    redirect_url = update_post_service.get_redirect_url(write)
    db.commit()

    return RedirectResponse(redirect_url, status_code=303)


@router.get("/{bo_table}/{wr_id}", dependencies=[Depends(check_group_access)])
async def read_post(
    request: Request,
    db: db_session,
    write: Annotated[WriteBaseModel, Depends(get_write)],
    member: Annotated[Member, Depends(check_login_member)],
    bo_table: str = Path(...),
    wr_id: int = Path(...),
):
    """게시글을 읽는다."""
    read_post_service = ReadPostService(request, db, bo_table, wr_id, member)
    board = read_post_service.board
    read_post_service.request.state.editor = read_post_service.select_editor
    read_post_service.validate_secret_with_session()
    read_post_service.validate_repeat_with_session()
    read_post_service.block_read_comment()
    read_post_service.validate_read_level()
    read_post_service.check_scrap()
    read_post_service.check_is_good()
    prev, next = read_post_service.get_prev_next()
    db.commit()
    context = {
        "request": read_post_service.request,
        "board": board,
        "write": write,
        "write_list": read_post_service.write_list,
        "prev": prev,
        "next": next,
        "images": read_post_service.images,
        "files": read_post_service.images + read_post_service.normal_files,
        "links": read_post_service.get_links(),
        "comments": read_post_service.get_comments(),
        "is_write": read_post_service.is_write_level(),
        "is_reply": read_post_service.is_reply_level(),
        "is_comment_write": read_post_service.is_comment_level(),
    }
    return templates.TemplateResponse(f"/board/{board.bo_skin}/read_post.html", context)


@router.get("/delete/{bo_table}/{wr_id}", dependencies=[Depends(validate_token)])
async def delete_post(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    wr_id: int = Path(...),
):
    """
    게시글을 삭제한다.
    """
    delete_post_service = DeletePostService(
        request, db, bo_table, wr_id, request.state.login_member
    )
    delete_post_service.validate_level()
    delete_post_service.validate_exists_reply()
    delete_post_service.validate_exists_comment()
    delete_post_service.delete_write()
    query_params = remove_query_params(request, "token")
    return RedirectResponse(set_url_query_params(f"/board/{bo_table}", query_params), status_code=303)


@router.get("/{bo_table}/{wr_id}/download/{bf_no}", dependencies=[Depends(check_group_access)])
async def download_file(
    request: Request,
    db: db_session,
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
    download_file_service = DownloadFileService(
        request, db, bo_table, request.state.login_member, wr_id, bf_no
    )
    download_file_service.validate_download_level()
    board_file = download_file_service.get_board_file()
    download_file_service.validate_point_session(board_file)
    return FileResponse(board_file.bf_file, filename=board_file.bf_source)


@router.post(
        "/write_comment_update/{bo_table}",
        dependencies=[Depends(validate_token), Depends(check_group_access)])
async def write_comment_update(
    request: Request,
    db: db_session,
    write: Annotated[WriteBaseModel, Depends(get_write)],
    bo_table: str = Path(...),
    form: WriteCommentForm = Depends(),
    recaptcha_response: str = Form("", alias="g-recaptcha-response"),
):
    """
    댓글 등록/수정
    """
    member = request.state.login_member

    comment_service = CommentService(
        request, db, bo_table, member, form.comment_id
    )

    if form.w == "c":
        #댓글 생성
        if not member:
            # 비회원은 Captcha 유효성 검사
            await validate_captcha(request, recaptcha_response)
        comment_service.validate_write_delay()
        comment_service.validate_comment_level()
        comment_service.validate_point()
        comment_service.validate_post_content(form.wr_content)
        comment = comment_service.save_comment(form, write)
        comment_service.add_point(comment)
        comment_service.send_write_mail_(comment, write)
        insert_board_new(bo_table, comment)
        set_write_delay(request)
    elif form.w == "cu":
        # 댓글 수정
        write_model = comment_service.write_model
        comment = db.get(write_model, form.comment_id)
        if not comment:
            raise AlertException(f"{form.comment_id} : 존재하지 않는 댓글입니다.", 404)

        comment_service.validate_author(comment)
        comment_service.validate_post_content(form.wr_content)
        comment.wr_content = comment_service.get_cleaned_data(form.wr_content)
        comment.wr_option = form.wr_secret or "html1"
        comment.wr_last = comment_service.g5_instance.get_wr_last_now(write_model.__tablename__)
    db.commit()
    redirect_url = comment_service.get_redirect_url(write)
    return RedirectResponse(redirect_url, status_code=303)


@router.get("/delete_comment/{bo_table}/{wr_id}", dependencies=[Depends(validate_token)])
async def delete_comment(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    comment_id: int = Path(..., alias="wr_id"),
):
    """
    댓글 삭제
    """
    delete_comment_service = DeleteCommentService(
        request, db, bo_table, comment_id, request.state.login_member
    )
    comment = delete_comment_service.get_comment()
    delete_comment_service.check_authority()
    delete_comment_service.delete_comment()

    # request.query_params에서 token 제거
    query_params = remove_query_params(request, "token")
    url = f"/board/{bo_table}/{comment.wr_parent}"
    return RedirectResponse(
        set_url_query_params(url, query_params), status_code=303)


@router.get("/{bo_table}/{wr_id}/link/{no}")
async def link_url(
    request: Request,
    db: db_session,
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