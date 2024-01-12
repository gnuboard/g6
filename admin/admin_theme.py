from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy import select, update

from core.database import db_session
from core.template import (
    AdminTemplates, TEMPLATES, UserTemplates,
    get_theme_list, get_theme_info, register_theme_statics,
)
from lib.common import *
from lib.dependencies import validate_super_admin, validate_theme

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(validate_super_admin)])
templates = AdminTemplates()
templates.env.globals['get_theme_info'] = get_theme_info

TEMPLATE_MENU_KEY = "100280"


@router.get("/theme")
async def theme(request: Request, db: db_session):
    """
    테마 목록 조회
    """
    request.session["menu_key"] = TEMPLATE_MENU_KEY

    config = db.scalar(select(Config))
    current_theme = getattr(config, "cf_theme", None)
    theme_list = get_theme_list()

    # 테마가 없거나 설치되어 있지 않으면 기본 테마로 변경
    if current_theme not in theme_list:
        config.cf_theme = current_theme = "basic"
        db.commit()

    # 현재 사용 중인 테마를 목록 맨 앞으로 이동
    if current_theme and current_theme in theme_list:
        theme_list.remove(current_theme)
        theme_list.insert(0, current_theme)

    context = {
        "request": request,
        "config": config,
        "theme_list": theme_list,
        "total_count": len(theme_list)
    }
    return templates.TemplateResponse("theme.html", context)


@router.post("/theme_detail")
async def theme_detail(
    request: Request,
    theme: Annotated[str, Depends(validate_theme)]
):
    """
    테마 상세정보 조회
    """
    context = {
        "request": request,
        "info": get_theme_info(theme)
    }
    return templates.TemplateResponse("theme_detail.html", context)


@router.get("/theme_preview/{theme}")
async def theme_preview(
    request: Request,
    theme: Annotated[str, Depends(validate_theme)]
):
    """테마 미리보기 (미완성)
    - 프로그램 실행시 테마를 미리 지정하므로 중간에 다른 테마의 미리보기를 하기가 어려움
    """
    context = {
        "request": request,
        "info": get_theme_info(theme)
    }
    return templates.TemplateResponse("theme_preview.html", context)


@router.post("/theme_update")
async def theme_update(
    request: Request,
    db: db_session,
    theme: Annotated[str, Depends(validate_theme)]
):
    """ 테마 적용 """
    info = get_theme_info(theme)

    db.execute(update(Config).values(cf_theme=theme))
    db.commit()

    from main import app  # 순환참조 방지

    # todo 미들웨어로 옮기기
    register_theme_statics(app)
    user_template = UserTemplates()
    current_theme_path = user_template.env.loader.searchpath
    
    if current_theme_path[0] in user_template.env.loader.searchpath:
        user_template.env.loader.searchpath.remove(current_theme_path[0])
        user_template.env.loader.searchpath.insert(0, f"{TEMPLATES}/{theme}")
        user_template.env.cache.clear()

    return {"success": f"{info['theme_name']} 테마로 변경되었습니다."}


@router.get("/screenshot/{theme}")
async def screenshot(theme: str = Path(...)):
    try:
        file_path = f"{TEMPLATES}/{theme}/screenshot.png"

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(file_path)
    except Exception as e:
        logger.error(f"An error occurred while serving the file: {e}")
        raise HTTPException(status_code=500, detail=str(e))