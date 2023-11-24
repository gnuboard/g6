# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 그누보드5 버전에서 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.
import datetime
from fastapi import APIRouter, Depends, Request, File, Form, Path, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import aliased, Session
from lib.pbkdf2 import create_hash

from lib.board_lib import *
from lib.common import *
from common.database import get_db
from common.formclass import WriteForm, WriteCommentForm
from common.models import AutoSave, Board, BoardGood, Group, GroupMember, Scrap

router = APIRouter()
templates = MyTemplates(directory=[EDITOR_PATH, CAPTCHA_PATH, TEMPLATES_DIR])
templates.env.filters["datetime_format"] = datetime_format
templates.env.filters["set_image_width"] = set_image_width
templates.env.globals["editor_macro"] = editor_macro
templates.env.globals["get_admin_type"] = get_admin_type
templates.env.globals["get_unique_id"] = get_unique_id
templates.env.globals["board_config"] = BoardConfig
templates.env.globals["get_list_thumbnail"] = get_list_thumbnail
templates.env.globals["captcha_widget"] = captcha_widget

FILE_DIRECTORY = "data/file/"


@router.get("/group/{gr_id}")
def group_board_list(
    request: Request,
    db: Session = Depends(get_db),
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
    if not admin_type and request.state.device == 'mobile':
        raise AlertException(f"{group.gr_subject} 그룹은 모바일에서만 접근할 수 있습니다.", 400, url="/")
    
    # 그룹별 게시판 목록 조회
    query_boards = db.query(Board).filter(
        Board.gr_id == gr_id,
        Board.bo_list_level <= member_level,
        Board.bo_device != 'mobile'
    )

    # 인증게시판 제외
    if not admin_type:
        query_boards = query_boards.filter_by(bo_use_cert='')

    boards = query_boards.order_by(Board.bo_order).all()
    return templates.TemplateResponse(
        f"{request.state.device}/board/group.html",
        {"request": request, "group": group, "boards": boards, "latest": latest}
    )


@router.get("/{bo_table}")
def list_post(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(..., title="게시판 아이디"),
    search_params: dict = Depends(common_search_query_params)
):
    """
    지정된 게시판의 글 목록을 보여준다.
    """
    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

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
    model_write = dynamic_create_write_table(bo_table)

    # 공지 게시글 목록 조회
    notice_writes = []
    if current_page == 1:
        notice_ids = board_config.get_notice_list()
        notice_query = db.query(model_write).filter(model_write.wr_id.in_(notice_ids))
        if sca:
            notice_query = notice_query.filter(model_write.ca_name == sca)
        notice_writes = [get_list(request, write, board_config) for write in notice_query.all()]

    # 게시글 목록 조회
    query = write_search_filter(request, model_write, sca, sfl, stx)
    query = query.filter_by(wr_is_comment=0)
    # 정렬
    if sst and hasattr(model_write, sst):
        if sod == "desc":
            query = query.order_by(desc(sst))
        else:
            query = query.order_by(asc(sst))
    else:
        query = board_config.get_list_sort_query(model_write, query)

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * page_rows
    # 최종 쿼리 결과를 가져옵니다.
    writes = query.offset(offset).limit(page_rows).all()
    total_count = query.count()

    # 게시글 정보 수정
    for write in writes:
        write.num = total_count - offset - (writes.index(write))
        write = get_list(request, write, board_config)

    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/list_post.html",
        {
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
        }
    )


@router.post("/list_delete/{bo_table}")
def list_delete(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    token: str = Form(...),
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글을 일괄 삭제한다.
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시판 관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, group=board.group, board=board)
    if not admin_type:
        raise AlertException("게시판 관리자 이상 접근이 가능합니다.", 403)

    # 게시글 조회
    model_write = dynamic_create_write_table(bo_table)
    writes = db.query(model_write).filter(model_write.wr_id.in_(wr_ids)).all()
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
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    # TODO: 게시글 삭제시 같이 삭제해야할 것들 추가

    return RedirectResponse(f"/board/{bo_table}?{request.query_params}", status_code=303)


@router.post("/move/{bo_table}")
async def move_post(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    sw: str = Form(...),
    wr_ids: list = Form(..., alias="chk_wr_id[]"),
):
    """
    게시글 복사/이동
    """
    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시판 관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, group=board.group, board=board)
    if not admin_type:
        raise AlertException("게시판 관리자 이상 접근이 가능합니다.", 403)

    # 게시판 목록 조회
    br = aliased(Board)
    gr = aliased(Group)
    query = db.query(br.bo_table, br.bo_subject, gr.gr_subject).outerjoin(gr, gr.gr_id == br.gr_id)
    # 관리자가 속한 게시판 목록만 조회
    if admin_type == "group":
        query = query.filter(gr.gr_admin == mb_id)
    elif admin_type == "board":
        query = query.filter(br.bo_admin == mb_id)
    results = query.order_by(br.gr_id, br.bo_order, br.bo_table).all()

    return templates.TemplateResponse(
        f"{request.state.device}/board/move.html", {
            "request": request,
            "sw": sw,
            "act": "이동" if sw == "move" else "복사",
            "results": results,
            "current_board": board,
            "wr_ids": ','.join(wr_ids)
        }
    )


@router.post("/move_update/")
def move_update(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    sw: str = Form(...),
    bo_table: str = Form(...),
    wr_ids: str = Form(..., alias="wr_id_list"),
    target_bo_tables: list = Form(..., alias="chk_bo_table[]"),
):
    """
    게시글 복사/이동
    """
    config = request.state.config
    act = "이동" if sw == "move" else "복사"

    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    # 게시판 검증
    origin_board = db.get(Board, bo_table)
    if not origin_board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시판관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, group=origin_board.group, board=origin_board)
    if not admin_type:
        raise AlertException("게시판 관리자 이상 접근이 가능합니다.", 403)

    # 입력받은 정보를 토대로 게시글을 복사한다.
    model_write = dynamic_create_write_table(bo_table)
    origin_writes = db.query(model_write).filter(model_write.wr_id.in_(wr_ids.split(','))).all()

    # 게시글 복사/이동 작업 반복
    for target_bo_table in target_bo_tables:
        for origin_write in origin_writes:
            TargetWrite = dynamic_create_write_table(target_bo_table)
            target_write = TargetWrite()

            # 복사/이동 로그 기록
            if not origin_write.wr_is_comment and config.cf_use_copy_log:
                log_msg = f"[이 게시물은 {member.mb_nick}님에 의해 {datetime_format(datetime.now()) } {origin_board.bo_subject}에서 {act} 됨]"
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
                db.query(BoardNew).filter_by(
                    bo_table=origin_board.bo_table, wr_id=origin_write.wr_id
                ).update({"bo_table": target_bo_table, "wr_id": target_write.wr_id, "wr_parent": target_write.wr_id})

                # 게시글
                if not origin_write.wr_is_comment:
                    # 추천데이터 이동
                    db.query(BoardGood).filter_by(
                        bo_table=origin_board.bo_table, wr_id=origin_write.wr_id
                    ).update({"bo_table": target_bo_table, "wr_id": target_write.wr_id})

                    # 스크랩 이동
                    db.query(Scrap).filter_by(
                        bo_table=bo_table, wr_id=origin_write.wr_id
                    ).update({"bo_table": target_bo_table, "wr_id": target_write.wr_id})

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
        G6FileCache().delete_prefix(f'latest-{target_bo_table}')

    # 원본 게시판 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return templates.TemplateResponse(
        "alert_close.html", {"request": request, "errors": f"해당 게시물을 선택한 게시판으로 {act} 하였습니다."}, status_code=200
    )


@router.get("/write/{bo_table}")
def write_form_add(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    parent_id: int = Query(None)
):
    """
    게시글을 작성하는 form을 보여준다.
    """
    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    parent_write = None
    if parent_id:
        # 답글 작성권한 검증
        if not board_config.is_reply_level():
            raise AlertException("답변글을 작성할 권한이 없습니다.", 403)

        # 답글 생성가능여부 검증
        model_write = dynamic_create_write_table(bo_table)
        parent_write = db.get(model_write, parent_id)
        generate_reply_character(board, parent_write)
    else:
        if not board_config.is_write_level():
            raise AlertException("글을 작성할 권한이 없습니다.", 403)

    # 게시판 제목 설정
    board.subject = board_config.subject
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board_config.select_editor

    # 게시판 관리자 확인
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, group=board.group, board=board)

    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/write_form.html",
        {
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
    )


@router.get("/write/{bo_table}/{wr_id}")
def write_form_edit(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    wr_id: int = Path(...)
):
    """
    게시글을 작성하는 form을 보여준다.
    """
    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시글 조회
    model_write = dynamic_create_write_table(bo_table)
    write = db.get(model_write, wr_id)
    if not write:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

    # 게시판 관리자 확인
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, group=board.group, board=board)

    # 게시판 수정 권한
    if not board_config.is_write_level():
        raise AlertException("글을 수정할 권한이 없습니다.", 403)
    if not board_config.is_modify_by_comment(wr_id):
        raise AlertException(f"이 글과 관련된 댓글이 {board.bo_count_modify}건 이상 존재하므로 수정 할 수 없습니다.", 403)

    if not admin_type:
        # 익명 글
        if not write.mb_id:
            if not request.session.get(f"ss_edit_{bo_table}_{wr_id}"):
                return RedirectResponse(f"/bbs/password/update/{bo_table}/{write.wr_id}?{request.query_params}", status_code=303)
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

    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/write_form.html",
        {
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
    )


@router.post("/write_update")
async def write_update(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    recaptcha_response: Optional[str] = Form(alias="g-recaptcha-response", default=""),
    bo_table: str = Form(...),
    wr_id: int = Form(None),
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
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)
    
    config = request.state.config
    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시판 관리자 확인
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, group=board.group, board=board)

    # 비밀글 사용여부 체크
    if not admin_type:
        if not board.bo_use_secret and "secret" in secret and "secret" in html and "secret" in mail:
            raise AlertException("비밀글 미사용 게시판 이므로 비밀글로 등록할 수 없습니다.", 403)
        # 비밀글 옵션에 따라 비밀글 설정
        if board.bo_use_secret == 2:
            secret = "secret"

    # 게시글 테이블 정보 조회
    model_write = dynamic_create_write_table(bo_table)
    # 옵션 설정
    options = [opt for opt in [html, secret, mail] if opt]
    form_data.wr_option = ",".join(map(str, options))

    # 링크 설정
    if not board_config.is_link_level():
        form_data.wr_link1 = ""
        form_data.wr_link2 = ""
        
    exists_write = db.query(model_write).filter_by(wr_id=wr_id).one_or_none()

    # 글 등록
    if not exists_write:
        
        # Captcha 검증
        if board_config.use_captcha:
            captcha_cls = get_current_captcha_cls(config.cf_captcha)
            if captcha_cls and (not await captcha_cls.verify(config.cf_recaptcha_secret_key, recaptcha_response)):
                raise AlertException("캡차가 올바르지 않습니다.", 400)
        if parent_id:
            if not board_config.is_reply_level():
                raise AlertException("답변글을 작성할 권한이 없습니다.", 403)
            parent_write = db.get(model_write, parent_id) if parent_id else None
        else:
            if not board_config.is_write_level():
                raise AlertException("글을 작성할 권한이 없습니다.", 403)
            parent_write = None

        form_data.wr_password = create_hash(form_data.wr_password) if form_data.wr_password else ""
        form_data.wr_name = board_config.set_wr_name(member, form_data.wr_name)
        form_data.wr_email = getattr(member, "mb_email", form_data.wr_email)
        form_data.wr_homepage = getattr(member, "mb_homepage", form_data.wr_homepage)

        write = model_write(
            wr_num = parent_write.wr_num if parent_write else get_next_num(bo_table),
            wr_reply = generate_reply_character(board, parent_write) if parent_write else "",
            wr_datetime = datetime.now(),
            mb_id = request.state.login_member.mb_id if member else '',
            wr_ip = request.client.host,
            **form_data.__dict__
        )
        db.add(write)
        db.commit()

        write.wr_parent = write.wr_id  # 부모아이디 설정
        board.bo_count_write = board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        db.commit()

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
    
        # 게시글 정보 조회 및 수정
        write = db.get(model_write, wr_id)
        if not write:
            raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

        form_data.wr_password = create_hash(form_data.wr_password) if form_data.wr_password else ""

        for field, value in form_data.__dict__.items():
            if value:
                setattr(write, field, value)

        # 분류 수정 시 댓글/답글도 같이 수정
        if form_data.ca_name:
            db.query(model_write).filter(model_write.wr_parent == wr_id).update({"ca_name": form_data.ca_name})
            db.commit()

    # 공지글 설정
    board.bo_notice = board_config.set_board_notice(write.wr_id, notice)
    # 자동저장 글 삭제
    if uid:
        db.query(AutoSave).filter(AutoSave.as_uid == uid).delete()
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
        for file in files:
            index = files.index(file)
            # 관리자가 아니면서 설정한 업로드 사이즈보다 크다면 건너뜀
            if file.filename and (admin_type or file_manager.is_upload_size(file)):
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
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return RedirectResponse(f"/board/{bo_table}/{write.wr_id}?{request.query_params}", status_code=303)


@router.get("/{bo_table}/{wr_id}")
def read_post(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    wr_id: int = Path(...)
):
    """
    게시글을 1개 읽는다.
    """
    config = request.state.config

    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시판 설정
    group = board.group
    board.subject = board_config.subject

    # 게시판 관리자 확인
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    member_level = get_member_level(request)
    admin_type = get_admin_type(request, mb_id, group=group, board=board)

    # 게시글 정보 조회
    model_write = dynamic_create_write_table(bo_table)
    write = db.get(model_write, wr_id)
    if not write:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

    # 그룹 접근 사용
    if group.gr_use_access:
        if not member:
            raise AlertException(f"비회원은 이 게시판에 접근할 권한이 없습니다.\\n\\n회원이시라면 로그인 후 이용해 보십시오.", 403)
        if not (admin_type == "super" or admin_type == "group"):
            group_member = db.query(GroupMember).filter(
                GroupMember.gr_id == group.gr_id,
                GroupMember.mb_id == mb_id
            ).one_or_none()
            print(group.gr_id, mb_id, group_member)
            if not group_member:
                raise AlertException("접근 권한이 없으므로 글읽기가 불가합니다.\\n\\n궁금하신 사항은 관리자에게 문의 바랍니다.", 403, "/")

    # 읽기 권한 검증
    if not board_config.is_read_level():
        raise AlertException("글을 읽을 권한이 없습니다.", 403)

    # 비밀글 검증
    session_secret_name = f"ss_secret_{bo_table}_{wr_id}"
    if ("secret" in write.wr_option
            and not admin_type
            and not is_owner(write, mb_id)
            and not request.session.get(session_secret_name)
            ):
        # 부모글이 본인글이라면 열람 가능
        owner = False
        if write.wr_reply and mb_id:
            parent_write = db.query(model_write).filter_by(
                wr_num=write.wr_num,
                wr_reply="",
                wr_is_comment=False
            ).first()
            if parent_write.mb_id == mb_id:
                owner = True
        if not owner:
            return RedirectResponse(f"/bbs/password/view/{bo_table}/{write.wr_id}?{request.query_params}", status_code=303)
        request.session[session_secret_name] = True

    # 게시글 정보 설정
    write.ip = board_config.get_display_ip(write.wr_ip)
    write.name = write.wr_name[:config.cf_cut_name] if config.cf_cut_name else write.wr_name

    # 세션 체크
    # 한번 읽은 게시글은 세션만료까지 조회수, 포인트 처리를 하지 않는다.
    session_name = f"ss_view_{bo_table}_{wr_id}"
    if not request.session.get(session_name):
        # 조회수 증가
        write.wr_hit = write.wr_hit + 1
        db.commit()

        # 포인트 검사 및 소진
        read_point = board.bo_read_point
        if config.cf_use_point and read_point != 0:
            # 관리자이거나 자신의 글이면 통과
            if not (admin_type
                    or is_owner(write, mb_id)
                    or (not member and board.bo_read_level == 1 and write.wr_ip == request.client.host)
                    ):
                # 포인트 검사 및 소진
                mb_point = getattr(member, "mb_point", 0)
                if mb_point + read_point < 0:
                    raise AlertException(f"게시글을 읽기 위해 {abs(read_point)} 포인트가 필요합니다.", 403)
                else:
                    # 포인트 소진 처리
                    insert_point(request, member.mb_id, read_point, f"{board.bo_subject} {write.wr_id} 글읽기", board.bo_table, write.wr_id, "읽기")
        request.session[session_name] = True

    if member:
        # 스크랩 여부 확인
        scrap_data = db.query(Scrap).filter_by(
            bo_table=bo_table, wr_id=wr_id, mb_id=member.mb_id
        ).first()
        if scrap_data:
            write.is_scrap = True

        # 추천/비추천 여부 확인
        good_data = db.query(BoardGood).filter_by(
            bo_table=bo_table, wr_id=wr_id, mb_id=member.mb_id
        ).first()
        if good_data:
            setattr(write, f"is_{good_data.bg_flag}", True)

    # 이전글 다음글 조회
    prev = None
    next = None
    sca = request.query_params.get("sca")
    sfl = request.query_params.get("sfl")
    stx = request.query_params.get("stx")
    if not board.bo_use_list_view:
        query = db.query(model_write).filter(model_write.wr_is_comment == 0).order_by(model_write.wr_num)
        if sca:
            query = query.filter(model_write.ca_name == sca)
        if sfl and stx and hasattr(model_write, sfl):
            query = query.filter(getattr(model_write, sfl).like(f"%{stx}%"))
         # 같은 wr_num 내에서 이전글 조회
        prev = query.filter(
            model_write.wr_num == write.wr_num,
            model_write.wr_reply < write.wr_reply,
        ).order_by(model_write.wr_reply.desc()).first()
        if not prev:
            prev = query.filter(model_write.wr_num < write.wr_num).first()

        # 같은 wr_num 내에서 다음글 조회
        next = query.filter(
            model_write.wr_num == write.wr_num,
            model_write.wr_reply > write.wr_reply,
        ).order_by(model_write.wr_reply).first()
        if not next:
            next = query.filter(model_write.wr_num > write.wr_num).first()

    # 파일정보 조회
    images, files = BoardFileManager(board, wr_id).get_board_files_by_type(request)

    # 링크정보 조회
    links = []
    for i in range(1, 3):
        url = getattr(write, f"wr_link{i}")
        hit = getattr(write, f"wr_link{i}_hit")
        if url:
            links.append({"no": i, "url": url, "hit": hit})

    # 댓글 목록 조회
    comments = db.query(model_write).filter_by(
        wr_parent=wr_id,
        wr_is_comment=True
    ).order_by(model_write.wr_comment, model_write.wr_comment_reply).all()

    for comment in comments:
        comment.name = comment.wr_name[:config.cf_cut_name] if config.cf_cut_name else comment.wr_name
        comment.ip = board_config.get_display_ip(comment.wr_ip)
        comment.is_reply = len(comment.wr_comment_reply) < 5 and board.bo_comment_level <= member_level
        comment.is_edit = admin_type or (member and comment.mb_id == member.mb_id)
        comment.is_del = admin_type or (member and comment.mb_id == member.mb_id) or not comment.mb_id 
        comment.is_secret = "secret" in comment.wr_option

        # 비밀댓글 처리
        session_secret_comment_name = f"ss_secret_comment_{bo_table}_{comment.wr_id}"
        if (comment.is_secret
                and not admin_type
                and not is_owner(comment, mb_id)
                and not request.session.get(session_secret_comment_name)
            ):
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
        "files": files,
        "links": links,
        "is_write": board_config.is_write_level(),
        "is_reply": board_config.is_reply_level(),
        "is_comment_write": board_config.is_comment_level(),
    }
    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/read_post.html", context
    )


# 게시글 삭제
@router.get("/delete/{bo_table}/{wr_id}")
def delete_post(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    token: str = Query(...)
):
    """
    게시글을 삭제한다.
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.", 403)

    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    if not board_config.is_delete_by_comment(wr_id):
        raise AlertException(f"이 글과 관련된 댓글이 {board.bo_count_delete}건 이상 존재하므로 삭제 할 수 없습니다.", 403)

    # 게시글 조회
    model_write = dynamic_create_write_table(bo_table)
    write = db.get(model_write, wr_id)
    if not write:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

    # request.query_params에서 token 제거
    # POST 요청이면 없어도 될 듯..
    query_params = dict(request.query_params)
    query_params.pop("token", None)
    query_params = "&".join([f"{key}={value}" for key, value in query_params.items()])
    query_params = query_params.replace("&amp;", "&")

    # 게시글 삭제 처리
    delete_write(request, bo_table, write)

    return RedirectResponse(f"/board/{bo_table}?{query_params}", status_code=303)


@router.get("/{bo_table}/{wr_id}/download/{bf_no}")
def download_file(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    bf_no: int = Path(...),
):
    """첨부파일 다운로드

    Args:
        bo_table (str): 게시판 테이블명
        wr_id (int): 게시글 아이디
        bf_no (int): 파일 순번
        db (Session, optional): DB 세션. Defaults to Depends(get_db).

    Raises:
        AlertException: 파일이 존재하지 않을 경우

    Returns:
        FileResponse: 파일 다운로드
    """
    # 게시판/게시글 정보 조회
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    if not board_config.is_download_level():
        raise AlertException("다운로드 권한이 없습니다.", 403)

    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

    # 파일 정보 조회
    file_manager = BoardFileManager(board, wr_id)
    board_file = file_manager.get_board_file(bf_no)
    if not board_file:
        raise AlertException("파일이 존재하지 않습니다.", 404)

    # 회원 정보
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, group=board.group, board=board)

    # 게시물당 포인트가 한번만 차감되도록 세션 설정
    session_name = f"ss_down_{bo_table}_{wr_id}"
    if not request.session.get(session_name):
        # 관리자이거나 자신의 글이면 통과하는 함수
        if not (admin_type
                or is_owner(write, mb_id)
                or (not member and board.bo_download_level == 1 and write.wr_ip == request.client.host)
                ):
            # 포인트 검사 및 소진
            download_point = board.bo_download_point
            mb_point = member.mb_point if member else 0
            if mb_point + download_point < 0:
                raise AlertException(f"파일을 다운로드하기 위해 {abs(download_point)} 포인트가 필요합니다.", 403)
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


@router.post("/write_comment_update/")
async def write_comment_update(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    recaptcha_response: Optional[str] = Form(alias="g-recaptcha-response", default=""),
    form: WriteCommentForm = Depends(),
):
    """
    댓글 등록
    """
    config = request.state.config
    member = request.state.login_member

    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.", 403)

    # 게시판 정보 조회
    board = db.get(Board, form.bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertException(f"{form.bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시글 정보 조회
    write_model = dynamic_create_write_table(form.bo_table)
    write = db.get(write_model, form.wr_id)
    if not write:
        raise AlertException(f"{form.wr_id} : 존재하지 않는 게시글입니다.", 404)

    
    if form.w == "c":
        # Captcha 검증
        if not member:
            captcha_cls = get_current_captcha_cls(config.cf_captcha)
            if captcha_cls and (not await captcha_cls.verify(config.cf_recaptcha_secret_key, recaptcha_response)):
                raise AlertException("캡차가 올바르지 않습니다.", 400)

        if not board_config.is_comment_level():
            raise AlertException("댓글을 작성할 권한이 없습니다.", 403)

        # 댓글 객체 생성
        comment = write_model()

        if form.comment_id:
            parent_comment = db.get(write_model, form.comment_id)
            if not parent_comment:
                raise AlertException(f"{form.comment_id} : 존재하지 않는 댓글입니다.", 404)

            comment.wr_comment_reply = generate_reply_character(board, parent_comment)
            comment.wr_comment = parent_comment.wr_comment
        else:
            comment.wr_comment = (db.query(func.max(write_model.wr_comment).label("max_wr_comment")).filter(
                write_model.wr_parent == form.wr_id,
                write_model.wr_is_comment == True
            ).first().max_wr_comment or 0) + 1

        # 댓글 추가정보 등록
        comment.ca_name = write.ca_name
        comment.wr_option = form.wr_secret
        comment.wr_num = write.wr_num
        comment.wr_parent = form.wr_id
        comment.wr_is_comment = True
        comment.wr_content = form.wr_content
        comment.mb_id = getattr(member, "mb_id", "")
        comment.wr_password = create_hash(form.wr_password) if form.wr_password else ""
        comment.wr_name = board_config.set_wr_name(member, form.wr_name)
        comment.wr_email = getattr(member, "mb_email", "")
        comment.wr_homepage = getattr(member, "mb_homepage", "")
        comment.wr_datetime = comment.wr_last = datetime.now()
        comment.wr_ip = request.client.host
        db.add(comment)

        # 게시글에 댓글 수 증가
        write.wr_comment = write.wr_comment + 1
        db.commit()

        # 메일 발송
        if board_config.use_email:
            send_write_mail(request, board, comment, write)

    elif form.w == "cu":
        # 댓글 수정
        comment = db.get(write_model, form.comment_id)
        if not comment:
            raise AlertException(f"{form.comment_id} : 존재하지 않는 댓글입니다.", 404)

        comment.wr_content = form.wr_content
        comment.wr_option = form.wr_secret
        comment.wr_last = datetime.now()
        db.commit()

    return RedirectResponse(f"/board/{form.bo_table}/{form.wr_id}", status_code=303)


@router.get("/delete_comment/{bo_table}/{comment_id}")
def delete_comment(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    comment_id: int = Path(...),
    token: str = Query(...),
):
    """
    댓글 삭제
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.", 403)

    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    write_model = dynamic_create_write_table(bo_table)
    comment = db.get(write_model, comment_id)
    if not comment:
        raise AlertException(f"{comment_id} : 존재하지 않는 댓글입니다.", 404)

    # 게시판관리자 검증
    member = request.state.login_member
    mb_id = getattr(member, "mb_id", None)
    admin_type = get_admin_type(request, mb_id, board=board, group=board.group)

    # request.query_params에서 token 제거
    # POST 요청이면 없어도 될 듯..
    query_params = dict(request.query_params)
    query_params.pop("token", None)
    query_params = "&".join([f"{key}={value}" for key, value in query_params.items()])
    query_params = query_params.replace("&amp;", "&")

    # 게시글 삭제 권한 검증
    if not admin_type:
        # 익명 댓글
        if not comment.mb_id:
            if not request.session.get(f"ss_delete_comment_{bo_table}_{comment_id}"):
                raise AlertException("삭제할 권한이 없습니다.", 403, f"/bbs/password/comment-delete/{bo_table}/{comment_id}?{query_params}")
        # 회원 댓글
        elif comment.mb_id and not is_owner(write, mb_id):
            raise AlertException("본인 댓글만 삭제할 수 있습니다.", 403)

    # 댓글 삭제
    db.delete(comment)
    db.commit()
    # 게시글에 댓글 수 감소
    write = db.get(write_model, comment.wr_parent)
    write.wr_comment = write.wr_comment - 1
    db.commit()

    return RedirectResponse(f"/board/{bo_table}/{write.wr_id}?{query_params}", status_code=303)


@router.get("/{bo_table}/{wr_id}/link/{no}")
def link_url(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    no: int = Path(...)
):
    """
    게시글에 포함된 링크이동
    """
    # 게시판 정보 조회
    board = db.get(Board, bo_table)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시글 조회
    model_write = dynamic_create_write_table(bo_table)
    write = db.get(model_write, wr_id)
    if not write:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

    # 링크정보 조회
    url = getattr(write, f"wr_link{no}")
    if not url:
        raise AlertException("링크가 존재하지 않습니다.", 404)

    # 링크 세션 설정
    link_session_name = f"ss_link_{bo_table}_{wr_id}_{no}"
    if not request.session.get(link_session_name):
        # 링크 횟수 증가
        setattr(write, f"wr_link{no}_hit", getattr(write, f"wr_link{no}_hit") + 1)
        db.commit()
        request.session[link_session_name] = True

    # url에 http가 없으면 붙여줌
    if not url.startswith("http"):
        url = "http://" + url

    # 새 창의 외부 URL로 이동
    return RedirectResponse(url, status_code=303)
