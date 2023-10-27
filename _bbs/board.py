# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 그누보드5 버전에서 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.
import bleach
import datetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from common import *
from database import get_db
import models

router = APIRouter()
templates = Jinja2Templates(directory=[EDITOR_PATH, TEMPLATES_DIR])
templates.env.globals["bleach"] = bleach
templates.env.globals["nl2br"] = nl2br
templates.env.globals["editor_path"] = editor_path
templates.env.globals["generate_token"] = generate_token
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
def list_post(bo_table: str, request: Request, db: Session = Depends(get_db), search_params: dict = Depends(common_search_query_params)):
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
        write.wr_num = abs(int(write.wr_num))  # 양수로 변경
        write.wr_datetime2 = write.wr_datetime.strftime("%Y-%m-%d %H:%M:%S")
        write.icon_hot = write.wr_hit >= board.bo_hot
        write.icon_new = write.wr_datetime > (datetime.now() - timedelta(hours=int(board.bo_new)))
        write.icon_file = write.wr_file
        write.icon_link = write.wr_link1 or write.wr_link2


        # 문자열을 datetime 객체로 변환
        

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


@router.get("/write")
def write_form_add(bo_table: str, request: Request, db: Session = Depends(get_db)):
    """
    게시글을 작성하는 form을 보여준다.
    """
    # 게시판 정보 조회
    board = db.query(models.Board).get(bo_table)
    if not board:
        raise AlertException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")

    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board.bo_select_editor

    return templates.TemplateResponse(
        f"board/{request.state.device}/{board.bo_skin}/write_form.html",
        {
            "request": request,
            "board": board,
            "write": None,
        }
    )


@router.get("/write/{bo_table}")
def write_form_edit(bo_table: str, request: Request, db: Session = Depends(get_db)):
    """
    게시글을 작성하는 form을 보여준다.
    """
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")

    write = dynamic_create_write_table(bo_table)
    write.wr_content = ""

    request.state.use_editor = board.bo_use_dhtml_editor
    request.state.editor = board.bo_select_editor

    return templates.TemplateResponse(f"board/{request.state.device}/{board.bo_skin}/write_form.html",
                                      {
                                          "request": request,
                                          "board": board,
                                          "write": write,
                                      })


@router.post("/write_update/")
def write_update(
    request: Request,
    db: Session = Depends(get_db),
    bo_table: str = Form(...),
    wr_subject: str = Form(...),
    wr_content: str = Form(...),
    #  wr_name: str = Form(...),
    #  wr_password: str = Form(...),
):
    """
    게시글을 Table 추가한다.
    """
    # print(bo_table, wr_subject, wr_content, wr_name, wr_password)
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")

    models.Write = dynamic_create_write_table(bo_table)
    tmp_write = db.query(models.Write).order_by(models.Write.wr_num.asc()).first()
    if tmp_write:
        wr_num = tmp_write.wr_num - 1
    else:
        wr_num = -1

    wr_datetime = datetime.now()
    wr_ip = request.client.host
    models.Write = dynamic_create_write_table(bo_table)
    write = models.Write(
        wr_num=wr_num,
        wr_is_comment=False,
        wr_subject=wr_subject,
        wr_content=wr_content,
        wr_datetime=wr_datetime,
        wr_ip=wr_ip,
    )
    db.add(write)
    db.commit()

    wr_id = write.wr_id
    write.wr_parent = wr_id
    db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{board.bo_table}')

    return RedirectResponse(f"/board/{bo_table}/{wr_id}", status_code=303)


@router.get("/{bo_table}/{wr_id}")
def read_post(
    bo_table: str, wr_id: int, request: Request, db: Session = Depends(get_db)
):
    """
    게시글을 1개 읽는다.
    """
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")

    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).filter(models.Write.wr_id == wr_id).first()
    if not write:
        raise HTTPException(
            status_code=404, detail="{wr_id} of {bo_table} is not found."
        )
    write.wr_hit = write.wr_hit + 1
    db.commit()
    # print(write.__dict__)

    comments = (
        db.query(models.Write)
        .filter(models.Write.wr_parent == wr_id and models.Write.wr_is_comment == True)
        .order_by(models.Write.wr_id.desc())
        .all()
    )
    if not comments:
        # raise HTTPException(status_code=404, detail="{write.wr_id} comment is not found.")
        comments = []
    # for comment in comments:
    #     print(vars(comment))

    # return templates.TemplateResponse("view.html", {"request": request, "board": board, "write": write, "comments": comments})

    # request.state.context["board"] = board
    # request.state.context["write"] = write
    # request.state.context["comments"] = comments

    context = {
        "request": request,
        "board": board,
        "write": write,
        "comments": comments,
    }
    # return templates.TemplateResponse(f"board/{request.state.device}/{board.bo_skin}/read_post.html", request.state.context)
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
    #  wr_name: str = Form(...),
    #  wr_password: str = Form(...),
):
    """
    댓글을 추가한다.
    """
    # 게시판이 존재하는지 확인
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")

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
