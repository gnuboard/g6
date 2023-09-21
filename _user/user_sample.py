from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from common import *

router = APIRouter()

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.get("/")
def read_users():
    return [{"username": "gnu"}, {"username": "board"}]

@router.get("/html")
def read_users_html(request: Request):
    return templates.TemplateResponse("user_sample/sample.html", {"request": request, "username1": "gnu", "username2": "board"})