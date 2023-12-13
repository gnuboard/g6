from fastapi import APIRouter
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from lib.common import TEMPLATES_DIR
from ...plugin_info import module_name

router = APIRouter()

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])


@router.get("/show")
async def show(request: Request):
    return {"message": "Hello Plugin!"}


@router.get("/show_template")
async def show(request: Request):
    return templates.TemplateResponse(
        "user_demo.html",
        {
            "request": request,
            "title": "Hello user demo plugin!",
            "content": f"Hello demo plugin!",
        })
