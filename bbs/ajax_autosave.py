from fastapi import APIRouter, Depends, Path
from starlette.responses import JSONResponse

from common.database import db_session
from common.formclass import AutoSaveForm
from common.models import AutoSave
from lib.common import *

router = APIRouter()


@router.get("/autosave_list")
async def autosave_list(request: Request, db: db_session):
    """
    자동저장 목록을 보여준다.
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
async def autosave_count(request: Request, db: db_session):
    """
    자동저장글 개수를 반환한다.
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
    """
    자동저장 내용을 불러온다.
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
    """
    글 임시저장
    """
    member = request.state.login_member
    if not member:
        raise HTTPException(status_code=403, detail="로그인 후 이용 가능합니다.")

    # 임시저장 데이턱 있는지 확인 후 수정 또는 추가
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
    """
    임시저장글 삭제
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
    """
    자동저장글 개수를 반환한다.
    """
    db = SessionLocal()
    count = db.scalar(
        select(func.count(AutoSave.as_id))
        .where(AutoSave.mb_id == mb_id)
    )
    db.close()

    return count
