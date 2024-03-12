from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from core.database import db_session
from core.models import Member
from lib.common import dynamic_create_write_table

from api.v1.models import responses
from api.v1.dependencies.member import get_current_member
from api.v1.models.scrap import ResponseScrapModel

router = APIRouter()


@router.get("/scraps",
            summary="회원 스크랩 목록 조회",
            response_model=List[ResponseScrapModel],
            responses={**responses})
async def read_member_scraps(
    db: db_session,
    current_member: Annotated[Member, Depends(get_current_member)],
):
    """회원 스크랩 목록을 조회합니다."""
    scraps = current_member.scraps.all()
    for scrap in scraps:
        write_model = dynamic_create_write_table(table_name=scrap.bo_table)
        write = db.get(write_model, scrap.wr_id)

        scrap.wr_subject = write.wr_subject
        scrap.bo_subject = scrap.board.bo_subject

    return scraps


@router.delete("/scraps/{ms_id}",
                summary="회원 스크랩 삭제",
                responses={**responses})
async def delete_member_scrap(
    db: db_session,
    ms_id: Annotated[int, Path(title="스크랩 아이디")],
    current_member: Annotated[Member, Depends(get_current_member)],
):
    """회원 스크랩을 삭제합니다."""
    scrap = current_member.scraps.filter_by(ms_id=ms_id).first()
    if scrap is None:
        raise HTTPException(status_code=404, detail="스크랩을 찾을 수 없습니다.")
    if scrap.mb_id != current_member.mb_id:
        raise HTTPException(status_code=403, detail="본인의 스크랩만 삭제할 수 있습니다.")

    db.delete(scrap)
    db.commit()
    db.refresh(current_member)

    return {"detail": "스크랩을 삭제하였습니다."}