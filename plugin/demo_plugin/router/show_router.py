import logging

from fastapi import APIRouter
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from lib.common import TEMPLATES_DIR
from ..__init__ import module_name

logging.info('load show_router.py')
show_router = APIRouter()

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])


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
