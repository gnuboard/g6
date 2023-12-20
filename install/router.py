from fastapi import APIRouter, Request

from common.database import db_session
from lib.common import *
from common.formclass import InstallFrom

INSTALL_TEMPLATES = "install/templates"

router = APIRouter()
templates = Jinja2Templates(directory=INSTALL_TEMPLATES)
templates.env.globals["version"] = read_version()


@router.get("/", name="install_main")
async def main(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})


@router.get("/license", name="install_license")
async def license(request: Request):
    context = {
        "request": request,
        "license": read_license(),
    }
    return templates.TemplateResponse("license.html", context)


@router.post("/form", name="install_form")
async def form(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("form.html", context)


@router.post("/", name="install")
async def install(
    request: Request,
    form: InstallFrom = Depends()
):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("result.html", context)