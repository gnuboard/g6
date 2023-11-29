from fastapi import APIRouter
from starlette.requests import Request

from lib.common import TEMPLATES_DIR, UserTemplates
from ..__init__ import module_name

show_router = APIRouter()

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = UserTemplates(directory=[TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])


@show_router.get("/show")
def show(request: Request):
    return {"message": "Hello Plugin!"}


@show_router.get("/show_template")
def show(request: Request):
    return templates.TemplateResponse(
        "user_demo.html",
        {
            "request": request,
            "title": "Hello user demo plugin!",
            "content": f"Hello demo plugin!",
        })
