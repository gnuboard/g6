from fastapi import APIRouter
from starlette.requests import Request

from core.template import theme_asset, UserTemplates
from .. import plugin_config
from ..plugin_config import module_name

router = APIRouter()

templates = UserTemplates()
templates.env.globals["theme_asset"] = theme_asset


@router.get("/show")
def show(request: Request):
    return {"message": "Hello Plugin JSON!"}


@router.get("/show_template")
def show(request: Request):
    return templates.TemplateResponse(
        f"{plugin_config.TEMPLATE_PATH}/user_demo.html",
        {
            "request": request,
            "title": f"Hello plugin Template!",
            "content": f"Hello {module_name}!",
        })
