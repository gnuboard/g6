# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.
from typing_extensions import Annotated, List

from fastapi import APIRouter, Depends, Request, Form, Path, Query, File, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from core.database import db_session
from core.exception import AlertException
from core.formclass import WriteForm, WriteCommentForm
from core.models import WriteBaseModel
from core.template import UserTemplates
from lib.member import get_admin_type
from lib.board_lib import (
    set_image_width, url_auto_link, BoardConfig, get_list_thumbnail,
    render_latest_posts, generate_reply_character, is_secret_write,
    is_owner, insert_board_new, set_write_delay
)
from lib.captcha import captcha_widget
from lib.common import set_url_query_params, get_unique_id, remove_query_params
from lib.dependency.board import get_write
from lib.dependency.dependencies import (
    check_group_access, common_search_query_params, validate_captcha, validate_token
)
from lib.template_functions import get_paging
from service.board import (
    ListPostService, CreatePostService, ReadPostService,
    UpdatePostService, DeletePostService, GroupBoardListService,
    CommentService, DeleteCommentService, ListDeleteService,
    MoveUpdateService, DownloadFileService
)
from service.board_file_service import BoardFileService
from service.popular_service import PopularService


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
    service: Annotated[GroupBoardListService, Depends(GroupBoardListService.async_init)],
):
    """
    게시판그룹의 모든 게시판 목록을 보여준다.
    """
    # 게시판 그룹 정보 조회
    group = service.group
    service.check_mobile_only()
    boards = service.get_boards_in_group()

    context = {
        "request": request,
        "group": group,
        "boards": boards,
        "render_latest_posts": render_latest_posts
    }
    return templates.TemplateResponse("/board/group.html", context)


@router.get("/{bo_table}/")
async def list_post(
    request: Request,
    list_post_service: Annotated[ListPostService, Depends(ListPostService.async_init)],
    popular_service: Annotated[PopularService, Depends(PopularService.async_init)],
    search_params: Annotated[dict, Depends(common_search_query_params)],
):
    """해당 게시판의 게시글 목록을 보여준다."""
    board = list_post_service.board
    paging = get_paging(
        list_post_service.request,
        list_post_service.search_params['current_page'],
        list_post_service.get_total_count(),
        list_post_service.page_rows
    )

    # 검색 단어를 인기검색어에 등록
    fields = search_params.get('sfl')
    word = search_params.get('stx')
    popular_service.create_popular(request, fields, word)

    context = {
        "request": list_post_service.request,
        "categories": list_post_service.categories,
        "board": board,
        "board_config": list_post_service,
        "notice_writes": list_post_service.get_notice_writes(),
        "writes": list_post_service.get_writes(),
        "total_count": list_post_service.get_total_count(),
        "current_page": list_post_service.search_params['current_page'],
        "paging": paging,
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
    service: Annotated[ListDeleteService, Depends(ListDeleteService.async_init)],
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글을 일괄 삭제한다.
    """
    service.validate_admin_authority()
    service.delete_writes(wr_ids)

    query_params = service.request.query_params
    url = f"/board/{service.bo_table}"
    return RedirectResponse(
        set_url_query_params(url, query_params), status_code=303)


@router.post("/move/{bo_table}")
async def move_post(
    service: Annotated[MoveUpdateService, Depends(MoveUpdateService.async_init)],
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글 복사/이동
    """
    service.validate_admin_authority()
    boards = service.get_admin_board_list()
    context = {
        "request": service.request,
        "sw": service.sw,
        "act": service.act,
        "boards": boards,
        "current_board": service.board,
        "wr_ids": ','.join(wr_ids)
    }
    return templates.TemplateResponse("/board/move.html", context)


@router.post("/move_update/", dependencies=[Depends(validate_token)])
async def move_update(
    service: Annotated[MoveUpdateService, Depends(MoveUpdateService.async_init)],
    wr_ids: str = Form(..., alias="wr_id_list"),
    target_bo_tables: list = Form(..., alias="chk_bo_table[]"),
):
    """
    게시글 복사/이동
    """
    service.validate_admin_authority()
    origin_writes = service.get_origin_writes(wr_ids)
    service.move_copy_post(target_bo_tables, origin_writes)
    context = {
        "request": service.request,
        "errors": f"해당 게시물을 선택한 게시판으로 {service.act} 하였습니다."
    }
    return templates.TemplateResponse("alert_close.html", context)


@router.get("/write/{bo_table}", dependencies=[Depends(check_group_access)])
async def write_form_add(
    service: Annotated[CreatePostService, Depends(CreatePostService.async_init)],
    file_service: Annotated[BoardFileService, Depends()],
    parent_id: int = Query(None)
):
    """
    게시글을 작성하는 form을 보여준다.(생성)
    """
    board = service.board
    parent_write = None
    if parent_id:
        parent_write = service.get_parent_post(parent_id)
        generate_reply_character(board, parent_write)
    else:
        service.validate_write_level()

    # TODO: 포인트 검증

    # 게시판 제목 설정
    board.subject = service.subject
    # 게시판 에디터 설정
    request = service.request
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = service.select_editor

    # 게시판 관리자 확인
    admin_type = service.member.admin_type

    context = {
        "request": request,
        "categories": service.get_category_list(),
        "board": board,
        "write": None,
        "is_notice": True if admin_type and not parent_id else False,
        "is_html": service.is_html_level(),
        "is_secret": 1 if is_secret_write(parent_write) else board.bo_use_secret,
        "secret_checked": "checked" if is_secret_write(parent_write) else "",
        "is_mail": service.use_email,
        "recv_email_checked": "checked",
        "is_link": service.is_link_level(),
        "is_file": service.is_upload_level(),
        "is_file_content": bool(board.bo_use_file_content),
        "files": file_service.get_board_files_by_form(board),
        "is_use_captcha": service.use_captcha,
        "write_min": service.write_min,
        "write_max": service.write_max,
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/write_form.html", context)


@router.get("/write/{bo_table}/{wr_id}", dependencies=[Depends(check_group_access)])
async def write_form_edit(
    service: Annotated[UpdatePostService, Depends(UpdatePostService.async_init)],
    file_service: Annotated[BoardFileService, Depends()],
):
    """
    게시글을 작성하는 form을 보여준다.(수정)
    """
    request = service.request
    bo_table = service.bo_table
    wr_id = service.wr_id
    board = service.board
    write = service.get_write(wr_id)

    # 게시판 수정 권한
    service.validate_write_level()
    service.validate_restrict_comment_count()

    # 게시판 관리자 확인
    admin_type = service.member.admin_type
    if not admin_type:
        # 익명 글
        if not write.mb_id:
            if not request.session.get(f"ss_edit_{bo_table}_{wr_id}"):
                query_params = request.query_params
                url = f"/bbs/password/update/{bo_table}/{write.wr_id}"
                return RedirectResponse(
                    set_url_query_params(url, query_params), status_code=303)
        # 회원 글
        elif write.mb_id and not is_owner(write, service.member.mb_id):
            raise AlertException("본인 글만 수정할 수 있습니다.", 403)

    # 게시판 제목 설정
    board.subject = service.subject
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = service.select_editor

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
        "categories": service.get_category_list(),
        "board": board,
        "write": write,
        "is_notice": True if not write.wr_reply and admin_type else False,
        "notice_checked": "checked" if service.is_board_notice(wr_id) else "",
        "is_html": service.is_html_level(),
        "html_checked": html_checked,
        "html_value": html_value,
        "is_secret": 1 if is_secret_write(write) else board.bo_use_secret,
        "secret_checked": "checked" if is_secret_write(write) else "",
        "is_mail": service.use_email,
        "recv_email_checked": "checked" if "mail" in write.wr_option else "",
        "is_link": service.is_link_level(),
        "is_file": service.is_upload_level(),
        "is_file_content": bool(board.bo_use_file_content),
        "files": file_service.get_board_files_by_form(board, wr_id),
        "is_use_captcha": False,
        "write_min": service.write_min,
        "write_max": service.write_max,
    }
    return templates.TemplateResponse(
        f"/board/{board.bo_skin}/write_form.html", context)


@router.post("/write_update/{bo_table}", dependencies=[Depends(validate_token), Depends(check_group_access)])
async def create_post(
    db: db_session,
    form_data: Annotated[WriteForm, Depends()],
    service: Annotated[CreatePostService, Depends(CreatePostService.async_init)],
    file_service: Annotated[BoardFileService, Depends()],
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
    await service.validate_captcha(recaptcha_response)
    service.validate_write_delay()
    service.validate_write_level()
    service.validate_secret_board(secret, html, mail)
    service.validate_post_content(form_data.wr_subject)
    service.validate_post_content(form_data.wr_content)
    service.is_write_level()
    service.arrange_data(form_data, secret, html, mail)
    write = service.save_write(parent_id, form_data)
    insert_board_new(service.bo_table, write)
    service.add_point(write)
    parent_write = service.get_parent_post(parent_id)
    service.send_write_mail_(write, parent_write)
    service.set_notice(write.wr_id, notice)
    set_write_delay(service.request)
    service.delete_auto_save(uid)
    service.save_secret_session(write.wr_id, secret)
    service.upload_files(file_service, write, files, file_content, file_dels)
    service.delete_cache()
    redirect_url = service.get_redirect_url(write)
    db.commit()
    return RedirectResponse(redirect_url, status_code=303)


@router.post("/write_update/{bo_table}/{wr_id}", dependencies=[Depends(validate_token), Depends(check_group_access)])
async def update_post(
    service: Annotated[UpdatePostService, Depends(UpdatePostService.async_init)],
    file_service: Annotated[BoardFileService, Depends()],
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
    wr_id = service.wr_id
    write = service.get_write(wr_id)
    service.validate_author(write, form_data.wr_password)
    service.validate_restrict_comment_count()
    service.validate_secret_board(secret, html, mail)
    service.validate_post_content(form_data.wr_subject)
    service.validate_post_content(form_data.wr_content)
    service.arrange_data(form_data, secret, html, mail)
    service.save_secret_session(wr_id, secret)
    service.save_write(write, form_data)
    service.set_notice(wr_id, notice)
    service.delete_auto_save(uid)
    service.upload_files(file_service, write, files, file_content, file_dels)
    service.update_children_category(form_data)
    service.delete_cache()
    redirect_url = service.get_redirect_url(write)
    service.db.commit()

    return RedirectResponse(redirect_url, status_code=303)


@router.get("/{bo_table}/{wr_id}", dependencies=[Depends(check_group_access)])
async def read_post(
    service: Annotated[ReadPostService, Depends(ReadPostService.async_init)],
):
    """게시글을 읽는다."""
    board = service.board
    service.request.state.editor = service.select_editor
    service.validate_secret_with_session()
    service.validate_repeat_with_session()
    service.block_read_comment()
    service.validate_read_level()
    service.check_scrap()
    service.check_is_good()
    prev, next = service.get_prev_next()
    service.db.commit()
    context = {
        "request": service.request,
        "board": board,
        "write": service.write,
        "write_list": service.write_list,
        "prev": prev,
        "next": next,
        "images": service.images,
        "files": service.images + service.normal_files,
        "links": service.get_links(),
        "comments": service.get_comments(),
        "is_write": service.is_write_level(),
        "is_reply": service.is_reply_level(),
        "is_comment_write": service.is_comment_level(),
    }
    return templates.TemplateResponse(f"/board/{board.bo_skin}/read_post.html", context)


@router.get("/delete/{bo_table}/{wr_id}", dependencies=[Depends(validate_token)])
async def delete_post(
    service: Annotated[DeletePostService, Depends(DeletePostService.async_init)],
):
    """
    게시글을 삭제한다.
    """
    service.validate_level()
    service.validate_exists_reply()
    service.validate_exists_comment()
    service.delete_write()
    query_params = remove_query_params(service.request, "token")
    return RedirectResponse(
        set_url_query_params(f"/board/{service.bo_table}", query_params), status_code=303
    )


@router.get("/{bo_table}/{wr_id}/download/{bf_no}", dependencies=[Depends(check_group_access)])
async def download_file(
    service: Annotated[DownloadFileService, Depends(DownloadFileService.async_init)],
):
    """첨부파일 다운로드

    Args:
        db (Session): DB 세션. Depends로 주입
        bo_table (str): 게시판 테이블명
        wr_id (int): 게시글 아이디
        bf_no (int): 파일 순번

    Raises:
        AlertException: 다운로드 권한 부재 / 파일 부재 / 포인트 부족

    Returns:
        FileResponse: 파일 다운로드
    """
    service.validate_download_level()
    board_file = service.get_board_file()
    service.validate_point_session(board_file)
    return FileResponse(board_file.bf_file, filename=board_file.bf_source)


@router.post(
        "/write_comment_update/{bo_table}",
        dependencies=[Depends(validate_token), Depends(check_group_access)])
async def write_comment_update(
    service: Annotated[CommentService, Depends(CommentService.async_init)],
    form: WriteCommentForm = Depends(),
    recaptcha_response: str = Form("", alias="g-recaptcha-response"),
):
    """
    댓글 등록/수정
    """
    write = service.get_write(service.wr_id)

    if form.w == "c":
        #댓글 생성
        if not service.member.mb_id:
            # 비회원은 Captcha 유효성 검사
            await validate_captcha(service.request, recaptcha_response)
        service.validate_write_delay()
        service.validate_comment_level()
        service.validate_point()
        service.validate_post_content(form.wr_content)
        comment = service.save_comment(form, write)
        service.add_point(comment)
        service.send_write_mail_(comment, write)
        insert_board_new(service.bo_table, comment)
        set_write_delay(service.request)
    elif form.w == "cu":
        # 댓글 수정
        write_model = service.write_model
        comment = service.db.get(write_model, form.comment_id)
        if not comment:
            raise AlertException(f"{form.comment_id} : 존재하지 않는 댓글입니다.", 404)

        service.validate_author(comment)
        service.validate_post_content(form.wr_content)
        comment.wr_content = service.get_cleaned_data(form.wr_content)
        comment.wr_option = form.wr_secret or "html1"
        comment.wr_last = service.g5_instance.get_wr_last_now(write_model.__tablename__)
    service.db.commit()
    redirect_url = service.get_redirect_url(write)
    return RedirectResponse(redirect_url, status_code=303)


@router.get("/delete_comment/{bo_table}/{comment_id}", dependencies=[Depends(validate_token)])
async def delete_comment(
    request: Request,
    service: Annotated[DeleteCommentService, Depends(DeleteCommentService.async_init)],
):
    """
    댓글 삭제
    """
    comment = service.get_comment()
    service.check_authority()
    service.delete_comment()

    # request.query_params에서 token 제거
    query_params = remove_query_params(request, "token")
    url = f"/board/{service.bo_table}/{comment.wr_parent}"
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
