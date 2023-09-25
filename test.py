from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, Template
from typing import List, Optional


app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/test")
def test(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})

@app.post("/test")
def test(ttt: Optional[List[str]] = Form(None, alias="ttt[]")):
    print(ttt)
    return RedirectResponse("/test", status_code=303)
