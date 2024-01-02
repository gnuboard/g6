import logging
import os
import re

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from PIL import Image

from common.database import db_session
from common.models import Config
from lib.common import *

router = APIRouter()
templates = AdminTemplates()

THEME_DIR = TEMPLATES  # Replace with actual theme directory
THEME_MENU_KEY = "100280"  # Replace with actual menu key


def get_theme_dir():
    result_array = []

    dirname = os.path.join(THEME_DIR)
    for file in os.listdir(dirname):
        if file in ['.', '..']:
            continue

        theme_path = os.path.join(dirname, file)
        if os.path.isdir(theme_path) and all(os.path.isfile(os.path.join(theme_path, fname)) for fname in ['readme.txt', 'screenshot.png', 'index.html']):
            result_array.append(file)

    result_array.sort()  # Using Python's default sort which is similar to natsort for strings

    return result_array


@router.get("/screenshot")
async def screenshot():
    '''
    스크린샷
    '''
    return {"screenshot": "screenshot"}


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.get("/screenshot/{dir}")
async def serve_screenshot(dir: str):
    try:
        file_path = Path(f"{TEMPLATES}/{dir}/screenshot.png")

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(file_path)
    except Exception as e:
        logger.error(f"An error occurred while serving the file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_theme_info(dir):
    info = {}
    path = os.path.join(THEME_DIR, dir)

    if os.path.isdir(path):
        screenshot = os.path.join(path, 'screenshot.png')
        screenshot_url = ''
        if os.path.isfile(screenshot):
            try:
                img = Image.open(screenshot)
                if img.format == "PNG":
                    # screenshot_url = screenshot.replace("/")  # Replace with actual URL replacement
                    # screenshot_url = f"/{TEMPLATES}/{dir}/screenshot.png"
                    screenshot_url = f"/admin/screenshot/{dir}"
            except:
                pass

        info['screenshot'] = screenshot_url

        text = os.path.join(path, 'readme.txt')
        if os.path.isfile(text):
            with open(text, 'r', encoding="UTF-8") as f:
                content = [line.strip() for line in f.readlines()]

            patterns = [
                ("^Theme Name:(.+)$", "theme_name"),
                ("^Theme URI:(.+)$", "theme_uri"),
                ("^Maker:(.+)$", "maker"),
                ("^Maker URI:(.+)$", "maker_uri"),
                ("^Version:(.+)$", "version"),
                ("^Detail:(.+)$", "detail"),
                ("^License:(.+)$", "license"),
                ("^License URI:(.+)$", "license_uri")
            ]

            for line in content:
                for pattern, key in patterns:
                    match = re.search(pattern, line, re.I)
                    if match:
                        info[key] = match.group(1).strip()

        if not info.get('theme_name'):
            info['theme_name'] = dir

        info['theme_dir'] = dir

    return info


# # 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals['get_theme_info'] = get_theme_info
templates.env.globals['serve_screenshot'] = serve_screenshot


@router.get("/theme")
async def theme(request: Request, db: db_session):
    """
    테마관리
    """
    request.session["menu_key"] = THEME_MENU_KEY

    if not request.state.is_super_admin:
        raise AlertException("최고관리자만 접근 가능합니다.", 403)

    config = db.scalars(select(Config)).one()
    themes = get_theme_dir()
    current_theme = getattr(config, "cf_theme", None)

    # 테마가 없거나 테마가 설치되어 있지 않으면 기본 테마로 변경
    if current_theme not in themes:
        config.cf_theme = current_theme = "basic"
        db.commit()

    # 테마가 있으면 테마를 목록 맨 앞으로 이동
    if current_theme and current_theme in themes:
        themes.remove(current_theme)
        themes.insert(0, current_theme)

    context = {
        "request": request,
        "config": config,
        "themes": themes,
        "total_count": len(themes)
    }
    return templates.TemplateResponse("theme.html", context)


@router.post("/theme_detail")
async def theme_detail(
    request: Request,
    theme: str = Form(...)
):
    if not request.state.is_super_admin:
        raise AlertException("최고관리자만 접근 가능합니다.", 403)

    theme = theme.strip()
    theme_dir = get_theme_dir()

    if theme not in theme_dir:
        raise AlertException("선택하신 테마가 설치되어 있지 않습니다.", 400)

    info = get_theme_info(theme)

    context = {
        "request": request,
        "name": info['theme_name'],
        "info": info
    }
    return templates.TemplateResponse("theme_detail.html", context)


# 테마 미리보기 미완성 (프로그램 실행시 테마를 미리 지정하므로 중간에 다른 테마의 미리보기를 하기가 어려움)
@router.get("/theme_preview")
async def theme_preview(
    request: Request,
    theme: str
):
    if not request.state.is_super_admin:
        raise AlertException("최고관리자만 접근 가능합니다.", 403)

    theme = theme.strip()
    theme_dir = get_theme_dir()

    if theme not in theme_dir:
        raise AlertException("선택하신 테마가 설치되어 있지 않습니다.", 400)

    info = get_theme_info(theme)

    context = {
        "request": request,
        "name": info['theme_name'],
        "info": info
    }
    return templates.TemplateResponse("theme_preview.html", context)


@router.post("/theme_update")
async def theme_update(
    request: Request,
    db: db_session,
    theme: str = Form(...)
):
    if not request.state.is_super_admin:
        raise AlertException("최고관리자만 접근 가능합니다.", 403)

    theme = theme.strip()
    theme_dir = get_theme_dir()

    info = get_theme_info(theme)

    if theme not in theme_dir:
        return {"error": f"선택하신 {info['theme_name']} 테마가 설치되어 있지 않습니다."}

    config = db.scalars(select(Config)).one()
    config.cf_theme = theme
    db.commit()

    from main import app  # 순환참조 방지

    # todo 미들웨어로 옮기기
    register_theme_statics(app)
    user_template = UserTemplates()
    current_theme_path = user_template.env.loader.searchpath
    if current_theme_path[0] in user_template.env.loader.searchpath:
        user_template.env.loader.searchpath = [f"{TEMPLATES}/{theme}"]
        user_template.env.cache.clear()

    return {"success": f"{info['theme_name']} 테마로 변경하였습니다."}
