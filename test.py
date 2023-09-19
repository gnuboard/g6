from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, Template
from typing import List, Optional


app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 템플릿 렌더링
# output = template.render(context)
# print(output)
@app.get("/test")
def test(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})

@app.post("/test")
def test(ttt: Optional[List[str]] = Form(None, alias="ttt[]")):
    print(ttt)
    return RedirectResponse("/test", status_code=303)

# async def test(request: Request):
#     form_data = await request.form()
#     ttt = form_data.getlist("ttt[]")
#     print(ttt)
#     return RedirectResponse("/test", status_code=303)