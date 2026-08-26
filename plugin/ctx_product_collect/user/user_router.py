import asyncio
import time

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from starlette.requests import Request

from core.template import UserTemplates
from ..plugin_config import module_name, TEMPLATE_PATH
from ..scraper import get_product_detail

router = APIRouter()
api_router = APIRouter()  # 의존성 없는 순수 API 라우터

templates = UserTemplates()

CTX_PROD_SEARCH_URL = "https://ctx.cretec.kr/CtxApp/ctx/selectPowerSearchJson.do"
CTX_EBOOK_SEARCH_URL = "https://ctx.cretec.kr/CtxApp/ebook/selectEbookUninumSearch.do"


@router.get("/")
async def index(request: Request):
    """CTX 상품수집 사용자 페이지 (준비 중)"""
    context = {
        "request": request,
        "title": "CTX 상품수집",
        "module_name": module_name,
    }
    return templates.TemplateResponse(
        f"{TEMPLATE_PATH}/index.html", context
    )


@api_router.get("/api/prod-search")
async def prod_search(
    prod_cd: str = Query(..., description="상품코드 (7자리 숫자)"),
    keyword: str = Query("", description="키워드"),
):
    """CTX 상품 정보 프록시 — selectPowerSearchJson"""
    params = {
        "prod_cd": prod_cd,
        "keyword": keyword,
        "_": int(time.time() * 1000),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CTX_PROD_SEARCH_URL, params=params)
            resp.raise_for_status()
            return JSONResponse(content=resp.json())
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="CTX API 응답 시간 초과")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"CTX API 오류: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CTX API 호출 실패: {str(e)}")


@api_router.get("/api/ebook-search")
async def ebook_search(
    prod_cd: str = Query(..., description="상품코드 (7자리 숫자)"),
    item_cd: str = Query("", description="아이템 코드"),
):
    """CTX eBook 정보 프록시 — selectEbookUninumSearch"""
    params = {
        "prodCd": prod_cd,
        "itemCd": item_cd,
        "_": int(time.time() * 1000),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CTX_EBOOK_SEARCH_URL, params=params)
            resp.raise_for_status()
            return JSONResponse(content=resp.json())
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="CTX eBook API 응답 시간 초과")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"CTX eBook API 오류: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CTX eBook API 호출 실패: {str(e)}")


@api_router.get("/api/item-detail")
async def item_detail(
    item_cd: str = Query(..., description="아이템 코드 (proino)"),
):
    """CTX 상품 상세 스크래핑 — Selenium headless Chrome"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_product_detail, item_cd)

    if not result.get("success", True):
        raise HTTPException(status_code=502, detail=result.get("error", "스크래핑 실패"))

    return JSONResponse(content=result)
