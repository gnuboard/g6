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
import models

router = APIRouter()
templates = Jinja2Templates(directory=[EDITOR_PATH, TEMPLATES_DIR])
templates.env.filters["datetime_format"] = datetime_format
templates.env.globals["bleach"] = bleach
templates.env.globals["nl2br"] = nl2br
templates.env.globals["editor_path"] = editor_path
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
        f"board/{request.state.device}/group.html", {"request": request, "group": group, "boards": boards, "latest": latest}
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

    # 게시판 카테고리 설정
    categories = []
    if board.bo_use_category:
        categories = board.bo_category_list.split("|")

    models.Write = dynamic_create_write_table(bo_table)

    writes = []
    # 공지 게시글 목록 조회
    if search_params["current_page"] == 1:
        notice_ids = board.bo_notice.split(",")
        notice_writes = db.query(models.Write).filter(models.Write.wr_id.in_(notice_ids)).all()
        # 게시글 정보 수정
        for write in notice_writes:
            write.is_notice = True

        writes.extend(notice_writes)

    # 게시글 목록 조회
    # TODO: sca 검색조건 추가
    # TODO: sfl 검색필드가 wr_name,1 형식으로 구성되었을 경우
    result = select_query(
            request,
            models.Write, 
            search_params, 
            default_sst = ["wr_num", "wr_reply"],
            default_sod = "",
        )
    writes.extend(result['rows'])
    total_count = result['total_count']

    # 게시글 정보 수정
    for write in writes:
        write.icon_hot = write.wr_hit >= board.bo_hot
        write.icon_new = write.wr_datetime > (datetime.now() - timedelta(hours=int(board.bo_new)))
        write.icon_file = write.wr_file
        write.icon_link = write.wr_link1 or write.wr_link2

    return templates.TemplateResponse(
        f"board/{request.state.device}/{board.bo_skin}/list_post.html",
        {
            "request": request,
            "categories": categories,
            "board": board,
            "notice_writes" : notice_writes,
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
def move_post(
        request: Request,
        bo_table: str,
        sw: str = Form(...),
        token: str = Form(...),
        db: Session = Depends(get_db),
        wr_ids: list = Form(..., alias="chk_wr_id[]"),
    ):
    """
    게시글 복사/이동
    """
    member = request.state.login_member
    act = "이동" if sw == "move" else "복사"

    # 토큰 검증    
    if not compare_token(request, token, 'board_list'):
        raise AlertException(status_code=403, detail="잘못된 접근입니다.")
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
        f"board/pc/move.html", {
            "request": request,
            "act": act,
            "results": results,
            "current_board": board,
            "wr_ids": ','.join(wr_ids)
        }
    )


# 작업 진행중....
@router.post("/move_update/")
def move_update(
        request: Request,
        token: str = Form(...),
        sw: str = Form(...),
        target_bo_table: str = Form(...),
        wr_ids: list = Form(..., alias="chk_wr_id[]"),
        db: Session = Depends(get_db),
    ):
    """
    게시글 복사/이동
    """
    member = request.state.login_member
    act = "이동" if sw == "move" else "복사"

    # 토큰 검증    
    if not compare_token(request, token, 'board_list'):
        raise AlertException(status_code=403, detail="잘못된 접근입니다.")
    


@router.get("/write/{bo_table}")
def write_form_add(bo_table: str, request: Request, db: Session = Depends(get_db), wr_id: int = Query(None)):
    """
    게시글을 작성하는 form을 보여준다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")
    
    # 게시판 카테고리 설정
    categories = []
    if board.bo_use_category:
        categories = board.bo_category_list.split("|")
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board.bo_select_editor or request.state.editor
    # 공지사항 설정
    is_notice = False
    if request.state.is_super_admin and not wr_id:
        is_notice = True
    # HTML 설정
    is_html = True if get_member_level(request) >= board.bo_html_level else False
    # 비밀글 설정
    is_secret = board.bo_use_secret
    # 메일 설정
    is_mail = True if request.state.config.cf_email_use and board.bo_use_email else False;
    recv_email_checked = "checked"
    # 링크 설정
    is_link = True if get_member_level(request) >= board.bo_link_level else False
    # 파일 설정
    file_count = int(board.bo_upload_count) or 0
    is_file = True if get_member_level(request) >= board.bo_upload_level else False
    is_file_content = True if board.bo_use_file_content else False

    return templates.TemplateResponse(
        f"board/{request.state.device}/{board.bo_skin}/write_form.html",
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

    # 게시판 카테고리 설정
    categories = []
    if board.bo_use_category:
        categories = board.bo_category_list.split("|")
    # 게시판 에디터 설정
    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board.bo_select_editor or request.state.editor

    # 게시글 조회
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).get(wr_id)
    # 공지사항 설정
    is_notice = True if not write.wr_reply and request.state.is_super_admin else False
    notice_checked = ""
    notice_ids = board.bo_notice.split(",")
    if str(wr_id) in notice_ids:
        notice_checked = "checked"
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
        f"board/{request.state.device}/{board.bo_skin}/write_form.html",
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

from dataclasses import dataclass

@dataclass
class writeForm:
    ca_name: str = Form(None)
    wr_name: str = Form(None)
    wr_email: str = Form(None)
    wr_homepage: str = Form(None)
    wr_subject: str = Form(...)
    wr_content: str = Form(...)
    wr_is_comment:bool = False

@router.post("/write_update/")
def write_update(
    request: Request,
    token: str = Form(...),
    bo_table: str = Form(...),
    wr_id: int = Form(None),
    parent_id: int = Form(None),
    db: Session = Depends(get_db),
    form_data: writeForm = Depends(),
):
    """
    게시글을 Table 추가한다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")
    
    models.Write = dynamic_create_write_table(bo_table)
    
    if compare_token(request, token, 'insert'): # 토큰에 등록돤 action이 insert라면 신규 등록
        tmp_write = db.query(models.Write).order_by(models.Write.wr_num.asc()).first()
        form_data.wr_name = request.state.login_member.mb_name if request.state.login_member else form_data.wr_name
        write = models.Write(
            wr_num= tmp_write.wr_num - 1 if tmp_write else -1,
            wr_datetime=datetime.now(),
            mb_id = request.state.login_member.mb_id if request.state.login_member else '',
            wr_ip = request.client.host,
            **form_data.__dict__
        )
        db.add(write)
        db.commit()
    elif compare_token(request, token, 'update'):  # 토큰에 등록된 action이 update라면 수정
        write = db.query(models.Write).get(wr_id)
        for field, value in form_data.__dict__.items():
            setattr(write, field, value)
        db.commit()
    else:
        raise AlertException(status_code=403, detail="잘못된 접근입니다.")

    db.commit()

    # 부모 글의 wr_reply 필드를 수정한다.
    write.wr_parent = parent_id or write.wr_id
    db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return RedirectResponse(f"/board/{bo_table}/{write.wr_id}", status_code=303)


@router.get("/{bo_table}/{wr_id}")
def read_post(bo_table: str, wr_id: int, request: Request, db: Session = Depends(get_db)):
    """
    게시글을 1개 읽는다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")

    # 게시글 정보 조회
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).get(wr_id)
    if not write:
        raise AlertException(status_code=404, detail="{wr_id} of {bo_table} is not found.")

    # 이전글 다음글 조회
    prev = None
    next = None

    # 댓글 목록 조회
    comments = db.query(models.Write).filter(
        models.Write.wr_parent == wr_id,
        models.Write.wr_is_comment == True
    ).order_by(models.Write.wr_id.desc()).all()
    

    # 조회수 증가
    write.wr_hit = write.wr_hit + 1
    db.commit()

    context = {
        "request": request,
        "board": board,
        "write": write,
        "comments": comments,
        "prev": prev,
        "next": next,
    }
    return templates.TemplateResponse(
        f"board/{request.state.device}/{board.bo_skin}/read_post.html", context
    )


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
