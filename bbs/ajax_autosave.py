from fastapi import APIRouter, Depends, HTTPException, Path
from starlette.responses import JSONResponse

from core.database import db_session
from core.formclass import AutoSaveForm
from core.models import AutoSave
from lib.common import *

router = APIRouter()


@router.get("/autosave_list")
async def autosave_list(request: Request, db: db_session):
    """자동저장 목록을 반환한다.
    Args:
        request (Request): Request 객체
        db (db_session): 데이터베이스 세션
    Returns:
        AutoSave[list]: 자동저장 목록
    """
    member: Member = request.state.login_member
    if not member:
        raise HTTPException(status_code=403, detail="로그인 후 이용 가능합니다.")

    save_list = db.scalars(
        select(AutoSave)
        .where(AutoSave.mb_id == member.mb_id)
        .order_by(AutoSave.as_datetime.desc())
    ).all()
    return save_list


@router.get("/autosave_count")
async def autosave_count(request: Request):
    """자동저장글 개수를 반환한다.
    Args:
        request (Request): Request 객체
    Returns:
        dict: 자동저장글 개수
    """
    member: Member = request.state.login_member
    if not member:
        raise HTTPException(status_code=403, detail="로그인 후 이용 가능합니다.")

    return {"count": get_autosave_count(member.mb_id)}


@router.get("/autosave_load/{as_id}")
async def autosave_load(
        request: Request,
        db: db_session,
        as_id: int = Path(..., title="자동저장 ID")
):
    """자동저장 내용을 불러온다.
    Args:
        request (Request): Request 객체
        db (db_session): 데이터베이스 세션
        as_id (int, optional): 자동저장 ID.
    Returns:
        AutoSave: 자동저장 데이터
    Raises:
        HTTPException:  로그인이 필요합니다
        HTTPException: 저장된 글이 없을 경우
        HTTPException: 접근 권한이 없을 경우
    """
    member: Member = request.state.login_member
    if not member:
        raise HTTPException(status_code=403, detail="로그인 후 이용 가능합니다.")

    save_data = db.get(AutoSave, as_id)
    if not save_data:
        raise HTTPException(status_code=404, detail="저장된 글이 없습니다.")
    if save_data.mb_id != member.mb_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    return save_data


@router.post("/autosave")
async def autosave(
        request: Request,
        db: db_session,
        form_data: AutoSaveForm = Depends()
):
    """글 임시저장
    Args:
        request (Request): Request 객체
        db (db_session): 데이터베이스 세션
        form_data (AutoSaveForm, optional): 자동저장 데이터.
    Returns:
        JSONResponse: 임시저장글 개수
    Raises:
        HTTPException:  로그인이 필요합니다
    """
    member = request.state.login_member
    if not member:
        raise HTTPException(status_code=403, detail="로그인 후 이용 가능합니다.")

    # 임시저장 데이터가 있는지 확인 후 수정 또는 추가
    save_data = db.scalar(
        select(AutoSave)
        .where(AutoSave.mb_id == member.mb_id, AutoSave.as_uid == form_data.as_uid)
    )
    if save_data:
        save_data.as_subject = form_data.as_subject
        save_data.as_content = form_data.as_content
        save_data.as_datetime = datetime.now()
    else:
        db.add(AutoSave(mb_id=member.mb_id, **form_data.__dict__))
    db.commit()

    # 자동저장글 개수 반환
    count = get_autosave_count(member.mb_id)
    return JSONResponse(status_code=201, content={"count": count})


@router.delete("/autosave/{as_id}")
async def autosave(
        request: Request,
        db: db_session,
        as_id: int = Path(..., title="자동저장 ID")
):
    """임시저장글 삭제
    Args:
        request (Request): Request 객체
        db (db_session): 데이터베이스 세션
        as_id (int, optional): 자동저장 ID.
    Returns:
        JSONResponse: 삭제되었습니다.
    Raises:
    HTTPException:  로그인이 필요합니다, 저장된 글이 없을 경우, 접근 권한이 없을 경우
    HTTPException: 저장된 글이 없을 경우
    HTTPException: 접근 권한이 없을 경우
    """
    member = request.state.login_member
    if not member:
        raise HTTPException(status_code=403, detail="로그인 후 이용 가능합니다.")

    save_data = db.get(AutoSave, as_id)
    if not save_data:
        raise HTTPException(status_code=404, detail="저장된 글이 없습니다.")
    if save_data.mb_id != member.mb_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    db.delete(save_data)
    db.commit()

    return JSONResponse(status_code=200, content="삭제되었습니다.")


def get_autosave_count(mb_id: str):
    """임시저장된 글 개수를 반환한다.
    Args:
        mb_id (str): 회원 아이디
    Returns:
        int: 임시저장된 글 개수
    """
    db = DBConnect().sessionLocal()
    count = db.scalar(
        select(func.count(AutoSave.as_id))
        .where(AutoSave.mb_id == mb_id)
    )
    db.close()

    return count
