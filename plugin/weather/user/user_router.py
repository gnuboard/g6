from fastapi import APIRouter
from starlette.requests import Request

from core.template import UserTemplates
from .. import plugin_config
from ..plugin_config import module_name

import httpx
from fastapi.responses import HTMLResponse, Response, JSONResponse 
# GOOGLE_MAPS_API_KEY, OPENWEATHERMAP_API_KEY 을 가지고 오기
from ..config.keys import GOOGLE_MAPS_API_KEY, OPENWEATHERMAP_API_KEY, ncpClientId

router = APIRouter()
templates = UserTemplates()


@router.get("/google-map", response_class=HTMLResponse)
async def show_google_map(request: Request):
    return templates.TemplateResponse(f"{plugin_config.TEMPLATE_PATH}/google-map.html", {"request": request})
    

# GOOGLE_MAPS_API_KEY 를 노출하지 않도록 API 서버를 통해 호출합니다.
@router.get("/google-maps-api")
async def google_map_proxy():
    url = f"https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return Response(content=response.text, media_type="application/javascript")


# OPENWEATHERMAP_API_KEY 를 노출하지 않도록 API 서버를 통해 호출합니다.
@router.get("/get-info/{lat}/{lon}")
async def get_weather(lat: float, lon: float):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()
    except Exception as e:
        print(e)  # 에러 로깅
        return JSONResponse(content={"error": "An error occurred"}, status_code=500)


@router.get("/naver-map", response_class=HTMLResponse)
async def show_naver_map(request: Request):
    context = {
        "request": request,
        "ncpClientId": ncpClientId
    }
    return templates.TemplateResponse(f"{plugin_config.TEMPLATE_PATH}/naver-map.html", context)
