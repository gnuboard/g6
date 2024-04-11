"""메뉴 API Router."""
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from lib.menu import get_menus
from api.v1.models.response import responses

router = APIRouter()


@router.get("/menus",
            summary="메뉴 목록 조회",
            # response_model=ResponseScrapListModel,
            responses={**responses})
async def read_menus():
    """회원 스크랩 목록을 조회합니다."""
    try:
        return get_menus()
    except SQLAlchemyError as e:
        return HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
