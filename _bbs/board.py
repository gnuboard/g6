# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 그누보드5 버전에서 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.
import bleach
import datetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import aliased, Session

from common import *
from database import get_db
from dataclassform import WriteForm
import models

router = APIRouter()
templates = Jinja2Templates(directory=[EDITOR_PATH, TEMPLATES_DIR])
templates.env.filters["datetime_format"] = datetime_format
templates.env.globals["bleach"] = bleach
templates.env.globals["nl2br"] = nl2br
templates.env.globals["editor_macro"] = editor_macro
templates.env.globals["generate_token"] = generate_token
templates.env.globals["getattr"] = getattr
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_unique_id"] = get_unique_id


@router.get("/group/{gr_id}")
def group_board_list(request: Request, gr_id: str, db: Session = Depends(get_db)):
    """
    게시판그룹의 모든 게시판 목록을 보여준다.
    """
    member_level = get_member_level(request)
    is_super_admin = request.state.is_super_admin
    
    group = db.query(models.Group).get(gr_id)
    if not is_super_admin and request.state.device == 'mobile':
        raise AlertException(status_code=400, detail=f"{group.gr_subject} 그룹은 모바일에서만 접근할 수 있습니다.", url="/")
    
    # 그룹별 게시판 목록 조회
    query_boards = db.query(models.Board).filter(
        models.Board.gr_id == gr_id,
        models.Board.bo_list_level <= member_level,
        models.Board.bo_device != 'mobile'
    )
    if not is_super_admin:
        query_boards = query_boards.filter(models.Board.bo_use_cert == '')

    boards = query_boards.order_by(models.Board.bo_order).all()
    return templates.TemplateResponse(
        f"{request.state.device}/board/group.html", {"request": request, "group": group, "boards": boards, "latest": latest}
    )


@router.get("/{bo_table}")
def list_post(bo_table: str, 
              request: Request, 
              db: Session = Depends(get_db),
              search_params: dict = Depends(common_search_query_params)
              ):
    """
    지정된 게시판의 글 목록을 보여준다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")

    models.Write = dynamic_create_write_table(bo_table)
    config = request.state.config
    sca = request.query_params.get("sca")
    sfl = search_params['sfl']
    stx = search_params['stx']
    sst = search_params['sst']
    sod = search_params['sod']
    current_page = search_params['current_page']
    page_rows = config.cf_mobile_page_rows if request.state.is_mobile and config.cf_mobile_page_rows else config.cf_page_rows

    # 게시판 카테고리 설정
    categories = board.bo_category_list.split("|") if board.bo_use_category else []

    notice_writes = []
    # 공지 게시글 목록 조회
    if current_page == 1:
        notice_ids = board.bo_notice.split(",")
        notice_query = db.query(models.Write).filter(models.Write.wr_id.in_(notice_ids))
        if sca:
            notice_query = notice_query.filter(models.Write.ca_name == sca)
        notice_writes = notice_query.all()

    # 게시글 목록 조회
    # TODO: sfl 검색필드가 wr_name,1 형식으로 구성되었을 경우
    query = db.query(models.Write).filter_by(wr_is_comment = 0)
    # 분류
    if sca:
        query = query.filter(models.Write.ca_name == sca)
    # 검색
    if sfl and stx and hasattr(models.Write, sfl):
        query = query.filter(getattr(models.Write, sfl).like(f"%{stx}%"))
    # 정렬
    if sst and hasattr(models.Write, sst):
        if sod == "desc":
            query = query.order_by(desc(sst))
        else:
            query = query.order_by(asc(sst))
    else:
        query = query.order_by(models.Write.wr_num, models.Write.wr_reply)

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * page_rows
    # 최종 쿼리 결과를 가져옵니다.
    writes = query.offset(offset).limit(page_rows).all()

    total_count = query.count()

    # 게시글 정보 수정
    for write in writes:
        write.num = total_count - offset - (writes.index(write))
        write.icon_hot = write.wr_hit >= board.bo_hot
        write.icon_new = write.wr_datetime > (datetime.now() - timedelta(hours=int(board.bo_new)))
        write.icon_file = write.wr_file
        write.icon_link = write.wr_link1 or write.wr_link2

    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/list_post.html",
        {
            "request": request,
            "categories": categories,
            "board": board,
            "notice_writes": notice_writes,
            "writes": writes,
            "total_count": total_count,
            "current_page": search_params['current_page'],
            "paging": get_paging(request, search_params['current_page'], total_count)
        }
    )


@router.post("/list_delete/{bo_table}")
def list_delete(
        request: Request,
        bo_table: str,
        token: str = Form(...),
        db: Session = Depends(get_db),
        wr_ids: list = Form(..., alias="chk_wr_id[]"),
    ):
    """
    게시글을 삭제한다.
    """
    # 토큰 검증    
    if not compare_token(request, token, 'board_list'):
        raise AlertException(status_code=403, detail="잘못된 접근입니다.")
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")
    
    # 게시글 조회
    models.Write = dynamic_create_write_table(bo_table)
    writes = db.query(models.Write).filter(models.Write.wr_id.in_(wr_ids)).all()
    for write in writes:
        db.delete(write)
    db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    # TODO: 게시글 삭제시 같이 삭제해야할 것들 추가

    return RedirectResponse(f"/board/{bo_table}", status_code=303)


@router.post("/move/{bo_table}")
async def move_post(
        request: Request,
        bo_table: str,
        sw: str = Form(...),
        db: Session = Depends(get_db),
        wr_ids: list = Form(..., alias="chk_wr_id[]"),
    ):
    """
    게시글 복사/이동
    """
    member = request.state.login_member
    act = "이동" if sw == "move" else "복사"

    # 게시판 관리자 검증
    # TODO: 게시판관리자/그룹관리자 허용 추가
    if not request.state.is_super_admin:
        raise AlertException(status_code=403, detail="게시판 관리자 이상 접근이 가능합니다.")

    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")
    # 게시판 목록 조회
    br = aliased(models.Board)
    gr = aliased(models.Group)
    query = db.query(br, gr).join(gr, gr.gr_id == br.gr_id)
    # TODO: 게시판관리자/그룹관리자 필터링 추가
    # if request.state.is_group_admin:
    #     query_boards = query_boards.filter(models.Group.gr_admin == member.mb_id)
    # if request.state.is_board_admin:
    #     query_boards = query_boards.filter(models.Board.bo_admin == member.mb_id)
    results = query.order_by(br.gr_id, br.bo_order, br.bo_table).all()

    return templates.TemplateResponse(
        f"{request.state.device}/board/move.html", {
            "request": request,
            "sw": sw,
            "act": act,
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
    member = request.state.login_member
    act = "이동" if sw == "move" else "복사"

    # 토큰 검증
    if not compare_token(request, token, 'board_move'):
        raise AlertException(status_code=403, detail="잘못된 접근입니다.")
    # 게시판관리자 검증

    # 입력받은 정보를 토대로 게시글을 복사한다.
    models.Write = dynamic_create_write_table(bo_table)
    origin_board = db.query(models.Board).get(bo_table)
    target_writes = db.query(models.Write).filter(models.Write.wr_id.in_(wr_ids.split(','))).all()

    # 게시글 복사/이동 작업 반복
    for target_bo_table in target_bo_tables:
        for write in target_writes:
            models.TargetWrite = dynamic_create_write_table(target_bo_table)
            
            # 복사/이동 로그 기록
            if not write.wr_is_comment and config.cf_use_copy_log:
                log_msg = f"[이 게시물은 {member.mb_nick}님에 의해 {datetime.now()} {origin_board.bo_subject}에서 {act} 됨]"
                if "html" in write.wr_option:
                    log_msg = f'<div class="content_{sw}>' + log_msg + '</div>'
                else:
                    log_msg = '\n' + log_msg

            # 게시글 복사
            initial_field = ["wr_id", "wr_parent"]
            target_write = models.TargetWrite()

            for field in write.__table__.columns.keys():
                if field in initial_field:
                    continue
                elif field == 'wr_content':
                    target_write.wr_content = write.wr_content + log_msg
                elif field == 'wr_num':
                    target_write.wr_num = get_next_num(target_bo_table)
                else:
                    setattr(target_write, field, getattr(write, field))

            if sw == "copy":
                target_write.wr_good = 0
                target_write.wr_nogood = 0
                target_write.wr_hit = 0
                target_write.wr_datetime = datetime.now()

            # 게시글 추가
            db.add(target_write)
            db.commit()

            # TODO: 파일 복사
            # files = db.query(models.BoardFile).filter(
            #     models.BoardFile.bo_table==origin_board.bo_table,
            #     models.BoardFile.wr_id==write.wr_id
            # ).all()
            # if files:
            #     pass

            if sw == "move":
                # TODO: 최신글 이동(주석해제)
                pass
                # write_new = db.query(models.boardNew).filter(bo_table == bo_table, wr_id=write.wr_id).first()
                # write_new.bo_table = target_write.bo_table
                # write_new.wr_id = write_new.parent_id = target_write.wr_id
                # db.commit()
                
                # 게시글
                if not write.wr_is_comment:
                    pass
                    # TODO: 추천데이터 이동
                    # TODO: 스크랩 이동

                # 기존 데이터(게시글, 파일, 최신글) 삭제
                db.delete(write)
                db.commit()
        # 최신글 캐시 삭제
        G6FileCache().delete_prefix(f'latest-{target_bo_table}')
    
    # 원본 게시판 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return templates.TemplateResponse(
        "alert_close.html", {"request": request, "errors": f"해당 게시물을 선택한 게시판으로 {act} 하였습니다."}, status_code=200
    )


@router.get("/write/{bo_table}")
def write_form_add(bo_table: str, request: Request, db: Session = Depends(get_db), parent_id: int = Query(None)):
    """
    게시글을 작성하는 form을 보여준다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")
    # 답글 생성가능여부 체크
    if parent_id:
        models.Write = dynamic_create_write_table(bo_table)
        write = db.query(models.Write).get(parent_id)
        wr_reply = generate_reply_character(board, write)

    # 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board.bo_select_editor or request.state.editor

    member_level = get_member_level(request)
    # 분류
    categories = [] if not board.bo_use_category else board.bo_category_list.split("|")
    # 공지사항
    is_notice = True if request.state.is_super_admin and not parent_id else False
    # HTML
    is_html = member_level >= board.bo_html_level
    # 비밀글
    is_secret = board.bo_use_secret
    # 메일
    is_mail = True if request.state.config.cf_email_use and board.bo_use_email else False
    recv_email_checked = "checked"
    # 링크
    is_link = member_level >= board.bo_link_level
    # 파일
    file_count = int(board.bo_upload_count) or 0
    is_file = member_level >= board.bo_upload_level
    is_file_content = board.bo_use_file_content

    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/write_form.html",
        {
            "request": request,
            "categories": categories,
            "board": board,
            "write": None,
            "is_notice": is_notice,
            "is_html": is_html,
            "is_secret": is_secret,
            "is_mail": is_mail,
            "recv_email_checked": recv_email_checked,
            "is_link": is_link,
            "file_count": file_count,
            "is_file": is_file,
            "is_file_content": is_file_content,
        }
    )


@router.get("/write/{bo_table}/{wr_id}")
def write_form_edit(bo_table: str, wr_id: int, request: Request, db: Session = Depends(get_db)):
    """
    게시글을 작성하는 form을 보여준다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")

    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board.bo_select_editor or request.state.editor

    # 분류
    categories = [] if not board.bo_use_category else board.bo_category_list.split("|")

    # 게시글 조회
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).get(wr_id)
    # 공지사항 설정
    is_notice = True if not write.wr_reply and request.state.is_super_admin else False
    notice_checked = "checked" if is_board_notice(board, wr_id) else ""
    # HTML 설정
    is_html = False
    html_checked = ""
    html_value = ""
    if get_member_level(request) >= board.bo_html_level:
        is_html = True
    if "html1" in write.wr_option:
        html_checked = "checked"
        html_value = "html1"
    elif "html2" in write.wr_option:
        html_checked = "checked"
        html_value = "html2"
    # 비밀글
    is_secret = board.bo_use_secret if "secret" in write.wr_option else True
    # 메일 설정
    is_mail = True if request.state.config.cf_email_use and board.bo_use_email else False;
    recv_email_checked = "checked" if "mail" in write.wr_option else ""
    # 링크 설정
    is_link = False
    if get_member_level(request) >= board.bo_link_level:
        is_link = True
    # 파일 설정
    # TODO: 업로드한 파일이 file_count보다 클 경우, file_count를 증가시킨다.
    file_count = int(board.bo_upload_count)
    is_file = True if get_member_level(request) >= board.bo_upload_level else False
    is_file_content = True if board.bo_use_file_content else False

    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/write_form.html",
        {
            "request": request,
            "categories": categories,
            "board": board,
            "write": write,
            "is_notice": is_notice,
            "notice_checked": notice_checked,
            "is_html": is_html,
            "html_checked": html_checked,
            "html_value": html_value,
            "is_secret": is_secret,
            "is_mail": is_mail,
            "recv_email_checked": recv_email_checked,
            "is_link": is_link,
            "file_count": file_count,
            "is_file": is_file,
            "is_file_content": is_file_content,
        }
    )


@router.post("/write_update/")
def write_update(
    request: Request,
    token: str = Form(...),
    bo_table: str = Form(...),
    wr_id: int = Form(None),
    parent_id: int = Form(None),
    db: Session = Depends(get_db),
    uid: str = Form(None),
    notice: bool = Form(False),
    html: str = Form(None),
    mail: str = Form(None),
    secret: str = Form(None),
    form_data: WriteForm = Depends(),
):
    """
    게시글을 Table 추가한다.
    """
    member = request.state.login_member

    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)
    
    # 비밀글 사용여부 체크
    if not request.state.is_super_admin and not board.bo_use_secret and "secret" in secret and "secret" in html and "secret" in mail:
        raise AlertException("비밀글 미사용 게시판 이므로 비밀글로 등록할 수 없습니다.", 403)
    # 비밀글 옵션에 따라 비밀글 설정
    if not request.state.is_super_admin and board.bo_use_secret == 2:
        secret = "secret"
    
    # 게시글 테이블 정보 조회
    models.Write = dynamic_create_write_table(bo_table)
    # 옵션 설정
    options = [opt for opt in [html, secret, mail] if opt]
    form_data.wr_option = ",".join(map(str, options))

    # 글 등록
    if compare_token(request, token, 'insert'):
        form_data.wr_name = getattr(member, "mb_name", form_data.wr_name)
        parent_write = db.query(models.Write).get(parent_id) if parent_id else None
        write = models.Write(
            wr_num = parent_write.wr_num if parent_write else get_next_num(bo_table),
            wr_reply = generate_reply_character(board, parent_write) if parent_write else "",
            wr_datetime = datetime.now(),
            mb_id = request.state.login_member.mb_id if request.state.login_member else '',
            wr_ip = request.client.host,
            **form_data.__dict__
        )
        db.add(write)
        db.commit()
        
        write.wr_parent = write.wr_id  # 부모아이디 설정
        board.bo_count_write = board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        db.commit()

        # 새글 추가
        insert_board_new(bo_table, write)

        # TODO: 글작성 포인트 부여(답변글은 댓글 포인트로 부여)
    # 글 수정
    elif compare_token(request, token, 'update'):
        # 게시글 정보 조회 및 수정
        write = db.query(models.Write).get(wr_id)
        if not write:
            raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

        for field, value in form_data.__dict__.items():
            setattr(write, field, value)

        # 분류 수정 시 댓글/답글도 같이 수정
        db.query(models.Write).filter(models.Write.wr_parent == wr_id).update({"ca_name": form_data.ca_name})
        db.commit()
    # 토큰 오류
    else:
        raise AlertException("잘못된 접근입니다.", 403)
    
    # 공지글 설정
    board.bo_notice = set_board_notice(board, write.wr_id, notice)
    # 자동저장 글 삭제
    if uid:
        db.query(models.AutoSave).filter(models.AutoSave.as_uid == uid).delete()
    db.commit()
    # TODO: 비밀글은 세션에 비밀글 저장 (자신의 글 확인)
    # TODO: 파일처리
    # TODO: 메일발송
    
    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return RedirectResponse(f"/board/{bo_table}/{write.wr_id}", status_code=303)


@router.get("/{bo_table}/{wr_id}")
def read_post(bo_table: str, wr_id: int, request: Request, db: Session = Depends(get_db)):
    """
    게시글을 1개 읽는다.
    """
    config = request.state.config
    member = request.state.login_member
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    # 게시글 정보 조회
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).get(wr_id)
    if not write:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)
    
    # 세션 체크
    # 한번 읽은 게시글은 세션만료까지 조회수, 포인트 처리를 하지 않는다.
    session_name = f"ss_view_{bo_table}_{wr_id}"
    if not request.session.get(session_name):
        # 조회수 증가
        write.wr_hit = write.wr_hit + 1

        # 관리자이거나 자신의 글이면 통과하는 함수
        if not (request.state.is_super_admin 
                or is_owner(write, member)
                or (not member and board.bo_read_level == 1 and write.wr_ip == request.client.host)
                ):
            # 포인트 검사 및 소진
            read_point = board.bo_read_point
            if config.cf_use_point and read_point:
                if member.mb_point + read_point < 0:
                    raise AlertException(f"게시글을 읽기 위해 {read_point} 포인트가 필요합니다.", 403)
                else:
                    # TODO: 포인트 소진 처리
                    pass
        request.session[session_name] = True
        db.commit()
    
    if member:
        # 스크랩 여부 확인
        scrap_data = db.query(models.Scrap).filter_by(
            bo_table = bo_table, wr_id = wr_id, mb_id = member.mb_id
        ).first()
        if scrap_data:
            write.is_scrap = True

        # 추천/비추천 여부 확인
        good_data = db.query(models.BoardGood).filter_by(
            bo_table = bo_table, wr_id = wr_id, mb_id = member.mb_id
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
        query = db.query(models.Write).filter(models.Write.wr_is_comment == 0).order_by(models.Write.wr_num)
        if sca:
            query = query.filter(models.Write.ca_name == sca)
        if sfl and stx and hasattr(models.Write, sfl):
            query = query.filter(getattr(models.Write, sfl).like(f"%{stx}%"))
         # 같은 wr_num 내에서 이전글 조회
        prev = query.filter(
            models.Write.wr_num == write.wr_num,
            models.Write.wr_reply < write.wr_reply,
        ).order_by(models.Write.wr_reply.desc()).first()
        if not prev:
            prev = query.filter(models.Write.wr_num < write.wr_num).first()

        # 같은 wr_num 내에서 다음글 조회
        next = query.filter(
            models.Write.wr_num == write.wr_num,
            models.Write.wr_reply > write.wr_reply,
        ).order_by(models.Write.wr_reply).first()
        if not next:
            next = query.filter(models.Write.wr_num > write.wr_num).first()

    # 댓글 목록 조회
    comments = db.query(models.Write).filter(
        models.Write.wr_parent == wr_id,
        models.Write.wr_is_comment == True
    ).order_by(models.Write.wr_id).all()
    
    context = {
        "request": request,
        "board": board,
        "write": write,
        "comments": comments,
        "prev": prev,
        "next": next,
    }
    return templates.TemplateResponse(
        f"{request.state.device}/board/{board.bo_skin}/read_post.html", context
    )


# 게시글 삭제
@router.get("/delete/{bo_table}/{wr_id}")
def delete_post(
    request: Request,
    bo_table: str,
    wr_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    """
    게시글을 삭제한다.
    """
    # 토큰 검증
    if not compare_token(request, token, 'delete'):
        raise AlertException(status_code=403, detail="잘못된 접근입니다.")
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")
    # 게시글 조회
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).get(wr_id)
    if not write:
        raise AlertException(status_code=404, detail="{wr_id} in {bo_table} is not found.")
    
    # 게시글 삭제
    db.delete(write)
    db.commit()

    # TODO: 게시글 삭제에 따른 추가정보 삭제

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return RedirectResponse(f"/board/{bo_table}", status_code=303)


@router.post("/write_comment_update/")
def write_comment_update(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Form(...),
    wr_id: int = Form(...),
    wr_content: str = Form(...),
):
    """
    댓글을 추가한다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")

    # 원글을 찾는다
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).filter(models.Write.wr_id == wr_id).first()
    if not write:
        raise HTTPException(
            status_code=404, detail="{wr_id} in {bo_table} is not found."
        )

    write.wr_comment = write.wr_comment + 1
    db.commit()

    # 댓글 추가
    comment = models.Write()
    comment.wr_is_comment = True
    comment.wr_parent = wr_id
    comment.wr_content = wr_content
    comment.wr_datetime = datetime.now()
    comment.wr_ip = request.client.host
    comment.wr_last = datetime.now()
    db.add(comment)
    db.commit()

    return RedirectResponse(f"/board/{bo_table}/{wr_id}", status_code=303)


# TODO: 아래 함수들을 다른 경로로 옮겨야 한다.

def is_board_notice(board: Board, wr_id: int) -> bool:
    """
    게시글이 공지글인지 확인한다.
    """
    return str(wr_id) in board.bo_notice.split(",")

def set_board_notice(board: Board, wr_id: int, insert: bool = False) -> str:
    """
    게시판의 공지글 목록을 설정한다.
    """
    notice_ids = list(board.bo_notice.split(","))
    exist = is_board_notice(board, wr_id)

    if insert and not exist:
        notice_ids.append(str(wr_id))
    elif not insert and exist:
        notice_ids.remove(str(wr_id))

    return ",".join(map(str, notice_ids))


def get_next_num(bo_table: str):
    """
    게시판의 다음글 번호를 얻는다.
    """
    db = SessionLocal()
    Write = dynamic_create_write_table(bo_table)
    row = db.query(func.min(Write.wr_num).label("min_wr_num")).first()

    return (int(row.min_wr_num) if row.min_wr_num else 0) - 1


# FIXME: 대댓글이 있는 상태에서 bo_reply_order를 바꾸면 입력하지 못하는 오류
# ex) 처음에는 정방향 A B C가 입력되고 역방향으로 바꾸면 last_reply_char이 A가 된다(Min).
# 역방향의 char_end는 A이고 A - 1은 예외처리하고 있음으로 대댓글이 입력되지 않는다
def generate_reply_character(board: Board, write):
    """ 대댓글 단계 문자열 생성 

    Args:
        board (Board): 게시판 object
        write (Write): 댓글/답글을 달 게시글 object

    Raises:
        AlertException: Z를 넘어가는 문자열 예외처리

    Returns:
        str: A~Z의 연속된 문자열(Ex: A, B, AA, AB, ABA ..)
    """
    db = SessionLocal()
    write_model = dynamic_create_write_table(board.bo_table)
    # 마지막 문자열 1개 자르기
    query = db.query(func.right(write_model.wr_reply, 1).label("reply")).filter(
        write_model.wr_reply != "",
        write_model.wr_parent == write.wr_id
    )
    # 정방향이면 최대값, 역방향이면 최소값
    if board.bo_reply_order:
        result = query.order_by(desc("reply")).first()
        char_begin = "A"
        char_end = "Z"
        char_increase = 1
    else:
        result = query.order_by(asc("reply")).first()
        char_begin = "Z"
        char_end = "A"
        char_increase = -1

    last_reply_char = result.reply if result else None
    if last_reply_char == char_end:  # A~Z은 26 입니다.
        raise AlertException("더 이상 답변하실 수 없습니다. 답변은 26개 까지만 가능합니다.")

    if not last_reply_char:
        reply_char = char_begin
    else:
        reply_char = chr(ord(last_reply_char) + char_increase)

    return write.wr_reply + reply_char


def is_owner(object, member = None):
    object_mb_id = getattr(object, "mb_id", None)
    member_mb_id = getattr(member, "mb_id", None)
    if object_mb_id:
        return object_mb_id == member_mb_id
    else:
        return False