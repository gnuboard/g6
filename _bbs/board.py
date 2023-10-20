# 여기에서 write 와 post 는 글 한개라는 개념으로 사용합니다.
# 그누보드5 버전에서 게시판 테이블을 write 로 사용하여 테이블명을 바꾸지 못하는 관계로
# 테이블명은 write 로, 글 한개에 대한 의미는 write 와 post 를 혼용하여 사용합니다.

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import datetime
from common import *

from database import get_db
import models

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["get_popular_list"] = get_popular_list


# all board list
@router.get("/")
def list_board(request: Request, db: Session = Depends(get_db)):
    '''
    모든 게시판 목록을 보여준다.
    '''
    boards = db.query(models.Board).all()
    return templates.TemplateResponse("board/list_board.html", {"request": request, "boards": boards})


@router.get("/{bo_table}")
def list_post(bo_table: str, request: Request, db: Session = Depends(get_db)):
    '''
    지정된 게시판의 글 목록을 보여준다.
    '''
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")
    
    # models_write = lambda: None
    models.Write = dynamic_create_write_table(bo_table)
    writes = db.query(models.Write).filter(models.Write.wr_is_comment == False).order_by(models.Write.wr_num).all()
    if writes:
        for write in writes:
            write.wr_num = abs(write.wr_num) # 양수로 변경  
            write.wr_datetime = write.wr_datetime.strftime("%Y-%m-%d %H:%M:%S")
    else:
        writes = []
        
    request.state.context["board"] = board
    request.state.context["writes"] = writes

    # return templates.TemplateResponse("board/list_post.html", {"request": request, "board": board, "writes": writes})
    return templates.TemplateResponse(f"board/{request.state.device}/{board.bo_skin}/list_post.html", request.state.context)


@router.get("/write/{bo_table}")
def write_form(bo_table: str, request: Request, db: Session = Depends(get_db)):
    '''
    게시글을 작성하는 form을 보여준다.
    '''
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")
    
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).order_by(models.Write.wr_num).all()
        
    return templates.TemplateResponse(f"board/{request.state.device}/{board.bo_skin}/write_form.html", {"request": request, "board": board, "write": write})


@router.post("/write_update/")
def write_update(request: Request, db: Session = Depends(get_db), 
                 bo_table: str = Form(...),
                 wr_subject: str = Form(...), 
                 wr_content: str = Form(...), 
                #  wr_name: str = Form(...), 
                #  wr_password: str = Form(...),
                 ):
    '''
    게시글을 Table 추가한다.
    '''
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
    write = models.Write(wr_num=wr_num, wr_is_comment=False, wr_subject=wr_subject, wr_content=wr_content, wr_datetime=wr_datetime, wr_ip=wr_ip)
    db.add(write)
    db.commit()
    
    wr_id = write.wr_id
    write.wr_parent = wr_id
    db.commit()
    
    return RedirectResponse(f"/board/{bo_table}/{wr_id}", status_code=303)


@router.get("/{bo_table}/{wr_id}")
def read_post(bo_table: str, wr_id: int, request: Request, db: Session = Depends(get_db)):
    '''
    게시글을 1개 읽는다.
    '''
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")
    
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).filter(models.Write.wr_id == wr_id).first()
    if not write:
        raise HTTPException(status_code=404, detail="{wr_id} of {bo_table} is not found.")
    write.wr_hit = write.wr_hit + 1
    db.commit()
    # print(write.__dict__)
    
    comments = db.query(models.Write).filter(models.Write.wr_parent == wr_id and models.Write.wr_is_comment == True).order_by(models.Write.wr_id.desc()).all()
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
    return templates.TemplateResponse(f"board/{request.state.device}/{board.bo_skin}/read_post.html", context)


@router.post("/write_comment_update/")
def write_comment_update(request: Request, db: Session = Depends(get_db), 
                 bo_table: str = Form(...),
                 wr_id: int = Form(...),
                 wr_content: str = Form(...), 
                #  wr_name: str = Form(...), 
                #  wr_password: str = Form(...),
                 ):
    '''
    댓글을 추가한다.
    '''
    # 게시판이 존재하는지 확인
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="{bo_table} is not found.")
    
    # 원글을 찾는다
    models.Write = dynamic_create_write_table(bo_table)
    write = db.query(models.Write).filter(models.Write.wr_id == wr_id).first()
    if not write:
        raise HTTPException(status_code=404, detail="{wr_id} in {bo_table} is not found.")  
    
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
