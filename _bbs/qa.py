from fastapi import APIRouter, Depends, File, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

from common import *
from database import get_db
from dataclassform import QaContentForm
from models import QaConfig, QaContent

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals['get_selected'] = get_selected
templates.env.globals["generate_token"] = generate_token
templates.env.globals["generate_query_string"] = generate_query_string

FILE_DIRECTORY = "data/qa/"


@router.get("/list")
def qa_list(request: Request,
            db: Session = Depends(get_db),
            current_page: int = Query(default=1, alias="page"), # 페이지
            ):
    '''
    Q&A 목록 보기
    '''
    sca = request.state.sca if request.state.sca is not None else ""
    stx = request.state.stx if request.state.stx is not None else ""
    sfl = request.state.sfl if request.state.sfl is not None else ""

    # Q&A 설정 조회
    qa_config = db.query(QaConfig).order_by(QaConfig.id.asc()).first()
    if not qa_config:
        raise AlertException(status_code=404, detail=f"Q&A 설정이 존재하지 않습니다.")
    
    # Q&A 목록 조회
    query = db.query(QaContent).filter(QaContent.qa_type == 0).order_by(QaContent.qa_id.desc())
    # 카테고리
    if sca:
        query = query.filter(QaContent.qa_category == sca)
    # 검색어
    if stx:
        if sfl == "qa_subject":
            query = query.filter(QaContent.qa_subject.like(f"%{stx}%"))
        elif sfl == "qa_content":
            query = query.filter(QaContent.qa_content.like(f"%{stx}%"))
        elif sfl == "qa_name":
            query = query.filter(QaContent.qa_name.like(f"%{stx}%"))
        elif sfl == "mb_id":
            query = query.filter(QaContent.mb_id.like(f"%{stx}%"))

    # 페이징 변수
    records_per_page = request.state.config.cf_page_rows
    total_records = query.count()
    offset = (current_page - 1) * records_per_page

    # Q&A 목록 조회 & 페이징
    qa_list = query.offset(offset).limit(records_per_page).all()

    context = {
        "request": request,
        "qa_config": qa_config,
        "qa_list": qa_list,
        "categories": qa_config.qa_category.split("|"),
        "total_records": total_records,
        "current_page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }

    return templates.TemplateResponse(f"qa/pc/qa_list.html", context)


@router.get("/write")
def qa_write(request: Request,
             db: Session = Depends(get_db),
             qa_related: int = None):
    '''
    Q&A 작성하기
    '''
    # Q&A 설정 조회
    qa_config = db.query(QaConfig).order_by(QaConfig.id.asc()).first()
    if not qa_config:
        raise AlertException(status_code=404, detail=f"Q&A 설정이 존재하지 않습니다.")
    
    # 추가질문 작성 시, 원본질문 조회
    related = None
    if qa_related:
        related = db.query(QaContent).filter(QaContent.qa_id == qa_related).first()
        if not related:
            raise AlertException(status_code=404, detail=f"{qa_related} : 연관된 Q&A아이디가 존재하지 않습니다.")

    context = {
        "request": request,
        "qa_config": qa_config,
        "categories": qa_config.qa_category.split("|"),
        "qa": None,
        "related": related,
    }

    return templates.TemplateResponse(f"qa/pc/qa_form.html", context)


# Q&A 수정하기
@router.get("/write/{qa_id:int}")
def qa_edit(qa_id: int,
            request: Request,
            db: Session = Depends(get_db)):
    '''
    Q&A 수정하기
    '''
    # Q&A 설정 조회
    qa_config = db.query(QaConfig).order_by(QaConfig.id.asc()).first()
    if not qa_config:
        raise AlertException(status_code=404, detail=f"Q&A 설정이 존재하지 않습니다.")

    # Q&A 상세 조회
    qa = db.query(QaContent).filter(QaContent.qa_id == qa_id).first()
    if not qa:
        raise AlertException(status_code=404, detail=f"{qa_id} : Q&A 아이디가 존재하지 않습니다.")

    context = {
        "request": request,
        "qa_config": qa_config,
        "categories": qa_config.qa_category.split("|"),
        "qa": qa,
    }

    return templates.TemplateResponse(f"qa/pc/qa_form.html", context)


@router.post("/update")
def qa_update(request: Request,
                token: str = Form(...),
                db: Session = Depends(get_db),
                form_data: QaContentForm = Depends(),
                qa_id: int = Form(None),
                qa_parent: str = Form(None),
                qa_related: int = Form(None),
                file1: UploadFile = File(None),
                file2: UploadFile = File(None),
                qa_file_del1: int = Form(None),
                qa_file_del2: int = Form(None),
                ):
    """1:1문의 설정 등록/수정 처리

    Args:
        token (str): 입력/수정/삭제 변조 방지 토큰.
        form_data (QaConfigDataclass): 입력/수정 Form Data.

    Raises:
        AlertException: 토큰 유효성 검사

    Returns:
        RedirectResponse: 1:1문의 설정 등록/수정 후 폼으로 이동
    """
    # 회원정보

    if compare_token(request, token, 'insert'): # 토큰에 등록돤 action이 insert라면 신규 등록
        form_data.qa_related = qa_related
        form_data.qa_type = 1 if qa_parent else 0
        form_data.qa_parent = qa_parent if qa_parent else 0
        form_data.mb_id = ''
        form_data.qa_name = ''
        form_data.qa_datetime = datetime.now()
        form_data.qa_ip = ''

        qa = QaContent(**form_data.__dict__)
        db.add(qa)

        # 답변글이면 원본글의 답변여부를 1로 변경
        if qa_parent:
            parent = db.query(QaContent).filter(QaContent.qa_id == qa_parent).first()
            parent.qa_status = 1

        db.commit()

    elif compare_token(request, token, 'update'):  # 토큰에 등록된 action이 update라면 수정
        # 데이터 수정 후 commit
        qa = db.query(QaContent).filter(QaContent.qa_id == qa_id).first()
        for field, value in form_data.__dict__.items():
            setattr(qa, field, value)
        db.commit()
    
    else: # 토큰 검사 실패
        raise AlertException(status_code=403, detail=f"{token} : 토큰이 존재하지 않습니다.")
    

    # 파일 경로체크 및 생성
    make_directory(FILE_DIRECTORY)
    # 파일 삭제
    delete_image(FILE_DIRECTORY, f"{qa.qa_source1}", qa_file_del1)
    delete_image(FILE_DIRECTORY, f"{qa.qa_source2}", qa_file_del2)
    # 파일 및 데이터 저장
    if file1.size > 0:
        filename1 = os.urandom(16).hex() + "." + file1.filename.split(".")[-1]
        qa.qa_file1 = FILE_DIRECTORY + filename1
        qa.qa_source1 = file1.filename
        save_image(FILE_DIRECTORY, f"{filename1}", file1)
    elif not qa.qa_source1:
        qa.qa_file1 = None
    if file2.size > 0:
        filename2 = os.urandom(16).hex() + "." + file2.filename.split(".")[-1]
        qa.qa_file2 = FILE_DIRECTORY + filename2
        qa.qa_source2 = file2.filename
        save_image(FILE_DIRECTORY, f"{filename2}", file2)
    elif not qa.qa_source2: 
        qa.qa_file2 = None
    db.commit()

    if qa.qa_type == 1:
        return RedirectResponse(url=f"/qa/{qa.qa_parent}", status_code=302)
    else:
        return RedirectResponse(url=f"/qa/{qa.qa_id}", status_code=302)


@router.get("/delete/{qa_id}")
def qa_delete(request: Request,
                qa_id: int,
                token: str = Query(...),
                db: Session = Depends(get_db)):
    '''
    Q&A 삭제하기
    '''
    if not compare_token(request, token, 'delete'):
        raise AlertException(status_code=403, detail=f"{token} : 토큰이 존재하지 않습니다.")

    # Q&A 삭제
    db.query(QaContent).filter(QaContent.qa_id == qa_id).delete()
    db.commit()

    return RedirectResponse(url=f"/qa/list", status_code=302)


@router.post("/list/delete")
async def qa_list_delete(request: Request, db: Session = Depends(get_db),
                      token: Optional[str] = Form(...),
                      checks: List[int] = Form(..., alias="chk_qa_id[]")
                      ):
    """Q&A 목록 삭제

    Args:
        token (str): 입력/수정/삭제 변조 방지 토큰.
        checks (List[int]): Q&A ID list. Defaults to Form(None, alias="chk_qa_id[]").
    """
    if not compare_token(request, token, 'delete'):
        raise AlertException(status_code=403, detail=f"{token} : 토큰이 존재하지 않습니다.")
    
    for i in checks:
        qa = db.query(QaContent).filter(QaContent.qa_id == i).first()
        if qa:
            # Q&A 삭제
            db.delete(qa)
            db.commit()

    return RedirectResponse(f"/qa/list?{generate_query_string(request)}", status_code=303)


@router.get("/{qa_id}")
def qa_view(qa_id: int,
            request: Request,
            db: Session = Depends(get_db)):
    '''
    Q&A 상세보기
    '''
    model = QaContent

    # Q&A 설정 조회
    qa_config = db.query(QaConfig).order_by(QaConfig.id.asc()).first()
    if not qa_config:
        raise AlertException(status_code=404, detail=f"Q&A 설정이 존재하지 않습니다.")
    
    # Q&A 조회
    qa = db.query(model).filter(model.qa_id == qa_id).first()
    # Q&A 파일목록 설정
    qa = set_file_list(request, qa)

    # Q&A 답변글 조회
    answer = db.query(model).filter(model.qa_type == 1, model.qa_parent == qa_id).first()
    # Q&A 답변글 파일목록 설정
    answer = set_file_list(request, answer)

    # 연관질문 목록 조회
    related_list = db.query(model).filter(model.qa_type == 0, model.qa_related == qa_id).all()

    # 이전글, 다음글
    sca = request.state.sca if request.state.sca is not None else ""
    stx = request.state.stx if request.state.stx is not None else ""
    sfl = request.state.sfl if request.state.sfl is not None else ""
    query = db.query(model)
    # 카테고리
    if sca:
        query = query.filter(QaContent.qa_category == sca)
    # 검색어
    if stx:
        if sfl == "qa_subject":
            query = query.filter(QaContent.qa_subject.like(f"%{stx}%"))
        elif sfl == "qa_content":
            query = query.filter(QaContent.qa_content.like(f"%{stx}%"))
        elif sfl == "qa_name":
            query = query.filter(QaContent.qa_name.like(f"%{stx}%"))
        elif sfl == "mb_id":
            query = query.filter(QaContent.mb_id.like(f"%{stx}%"))

    prev = query.filter(model.qa_type == 0, model.qa_id < qa_id).order_by(model.qa_id.desc()).first()
    next = query.filter(model.qa_type == 0, model.qa_id > qa_id).order_by(model.qa_id.asc()).first()

    context = {
        "request": request,
        "qa_config": qa_config,
        "qa": qa,
        "answer": answer,
        "related_list": related_list,
        "prev": prev,
        "next": next
    }

    return templates.TemplateResponse(f"qa/pc/qa_view.html", context)


def set_file_list(request: Request, qa: QaContent = None):
    """이미지 파일과 첨부파일 목록을 설정

    Args:
        request (Request): Request 객체
        qa (QaContent, optional): Q&A 객체. Defaults to None.

    Returns:
        QaContent: 이미지/첨부파일 목록이 설정된 Q&A 객체
    """
    config = request.state.config
    if qa:
        qa.image = []
        qa.file = []

        if qa.qa_source1:
            ext1 = qa.qa_source1.split('.')[-1]
            if ext1 in config.cf_image_extension:
                qa.image.append(qa.qa_file1)
            else:
                qa.file.append({"name": qa.qa_source1, "path": qa.qa_file1})
        if qa.qa_source2:
            ext2 = qa.qa_source2.split('.')[-1]
            if ext2 in config.cf_image_extension:
                qa.image.append(qa.qa_file2)
            else:
                qa.file.append({"name": qa.qa_source2, "path": qa.qa_file2})

    return qa
