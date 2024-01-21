from fastapi import APIRouter
from starlette.requests import Request

from core.template import UserTemplates
from .. import plugin_config
from ..plugin_config import module_name

router = APIRouter()

templates = UserTemplates()


@router.get("/show")
async def show(request: Request):
    """json 출력예시"""
    return {"message": "Hello Plugin JSON!"}


@router.get("/show_template")
async def show(request: Request):
    """템플릿 출력예시"""
    return templates.TemplateResponse(
        f"{plugin_config.TEMPLATE_PATH}/user_demo.html",
        {
            "request": request,
            "title": "Hello plugin Template!",
            "content": f"Hello {module_name}!",
        })
