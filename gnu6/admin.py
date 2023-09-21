from fastapi import FastAPI, APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session
from database import SessionLocal, get_db, engine
# from models import create_dynamic_create_write_table
import models 
from common import *
from jinja2 import Environment, FileSystemLoader
import random
import os
from typing import List, Optional
import socket

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# # 파이썬 함수를 jinja2 에서 사용할 수 있도록 등록
# # templates.env.globals['getattr'] = getattr

from gnu6._admin.admin_config import router as admin_config_router
router.include_router(admin_config_router, prefix="", tags=["admin_config"])


@router.get("/")
def base(request: Request, db: Session = Depends(get_db)):
    # template = env.get_template("index.html")
    # render = template.render(request=request)
    # return templates.TemplateResponse(template, {"request": request})
    return templates.TemplateResponse("admin/index.html", {"request": request})

