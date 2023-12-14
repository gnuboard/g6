from fastapi import APIRouter
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from lib.common import TEMPLATES_DIR, theme_asset
from ..plugin_config import module_name

router = APIRouter()

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])
templates.env.globals["theme_asset"] = theme_asset

@router.get("/show")
def show(request: Request):
    return {"message": "Hello Plugin!"}


@router.get("/show_template")
def show(request: Request):
    return templates.TemplateResponse(
        "user_demo.html",
        {
            "request": request,
            "title": f"Hello plugin!",
            "content": f"Hello {module_name}!",
        })
