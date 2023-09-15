from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates/user_sample")

router = APIRouter()

@router.get("/")
def read_users():
    return [{"username": "gnu"}, {"username": "board"}]

@router.get("/html")
def read_users_html(request: Request):
    return templates.TemplateResponse("sample.html", {"request": request, "username1": "gnu", "username2": "board"})