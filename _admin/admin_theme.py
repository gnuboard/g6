
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from common import *
import os
from PIL import Image
from database import get_db
from models import Config
from sqlalchemy import update
import re
from pathlib import Path

THEME_DIR = TEMPLATES  # Replace with actual theme directory

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def get_theme_dir():
    result_array = []

    dirname = os.path.join(THEME_DIR)
    for file in os.listdir(dirname):
        if file in ['.', '..']:
            continue

        theme_path = os.path.join(dirname, file)
        if os.path.isdir(theme_path) and all(os.path.isfile(os.path.join(theme_path, fname)) for fname in ['readme.txt', 'screenshot.png', 'index.pc.html']):
            result_array.append(file)

    result_array.sort()  # Using Python's default sort which is similar to natsort for strings

    return result_array

# app = FastAPI()
# app.mount("/templates", StaticFiles(directory="templates"), name="templates")


@router.get("/screenshot")
def screenshot():
    '''
    스크린샷
    '''
    return {"screenshot": "screenshot"}


import logging

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
                    screenshot_url = f"/{TEMPLATES}/{dir}/screenshot.png"
            except:
                pass

        info['screenshot'] = screenshot_url

        text = os.path.join(path, 'readme.txt')
        if os.path.isfile(text):
            with open(text, 'r') as f:
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
# templates.env.globals['getattr'] = getattr
# templates.env.globals['today'] = SERVER_TIME.strftime("%Y%m%d")
# templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals['get_theme_info'] = get_theme_info
templates.env.globals['serve_screenshot'] = serve_screenshot


@router.get("/theme")
async def theme(request: Request, db: Session = Depends(get_db)):
    '''
    테마관리
    '''
    config = db.query(Config).first()
    
    themes = get_theme_dir()
    if config.cf_theme and config.cf_theme in themes:
        themes.insert(0, config.cf_theme)
    themes = list(dict.fromkeys(themes))  # Remove duplicates
    total_count = len(themes)    
    
    # 설정된 테마가 존재하지 않는다면 cf_theme 초기화
    if config and config.cf_theme and config.cf_theme not in theme:
        config.cf_theme = ""
        db.commit()
    
    context = {
        "request": request,
        "config": config,
        "themes": themes,
        "total_count": total_count
    }    
    return templates.TemplateResponse("admin/theme.html", context)


@router.post("/theme_detail")
async def theme_detail(request: Request, theme: str = Form(...)):
    # Check if the user is an admin
    # if not is_admin():  # Define your own is_admin() function
    #     raise HTTPException(status_code=403, detail="Only the super admin can access this page.")
    
    print(theme)

    theme = theme.strip()
    theme_dir = get_theme_dir()

    if theme not in theme_dir:
        raise HTTPException(status_code=400, detail="The selected theme is not installed.")

    info = get_theme_info(theme)
    name = info['theme_name']

    return templates.TemplateResponse("admin/theme_detail.html", {"request": request, "name": name, "info": info})
