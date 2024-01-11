from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy import select, update

from core.database import db_session
from core.exception import AlertException
from core.template import (
    AdminTemplates, get_template_list, get_template_info,
    register_template_statics, TEMPLATES, UserTemplates
)
from lib.common import *
from lib.dependencies import validate_super_admin, validate_template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(validate_super_admin)])
templates = AdminTemplates()
templates.env.globals['get_template_info'] = get_template_info

TEMPLATE_MENU_KEY = "100280"


@router.get("/template")
async def template(request: Request, db: db_session):
    """
    템플릿 목록 조회
    """
    request.session["menu_key"] = TEMPLATE_MENU_KEY

    config = db.scalar(select(Config))
    current_template = getattr(config, "cf_theme", None)
    template_list = get_template_list()

    # 템플릿이 없거나 설치되어 있지 않으면 기본 템플릿으로 변경
    if current_template not in template_list:
        config.cf_theme = current_template = "basic"
        db.commit()

    # 현재 사용 중인 템플릿을 목록 맨 앞으로 이동
    if current_template and current_template in template_list:
        template_list.remove(current_template)
        template_list.insert(0, current_template)

    context = {
        "request": request,
        "config": config,
        "templates": template_list,
        "total_count": len(template_list)
    }
    return templates.TemplateResponse("template.html", context)


@router.post("/template_detail")
async def template_detail(
    request: Request,
    template: Annotated[str, Depends(validate_template)]
):
    """
    템플릿 상세정보 조회
    """
    context = {
        "request": request,
        "info": get_template_info(template)
    }
    return templates.TemplateResponse("template_detail.html", context)


@router.get("/template_preview/{template}")
async def template_preview(
    request: Request,
    template: Annotated[str, Depends(validate_template)]
):
    """템플릿 미리보기 (미완성)
    - 프로그램 실행시 템플릿을 미리 지정하므로 중간에 다른 템플릿의 미리보기를 하기가 어려움
    """
    context = {
        "request": request,
        "info": get_template_info(template)
    }
    return templates.TemplateResponse("template_preview.html", context)


@router.post("/template_update")
async def template_update(
    request: Request,
    db: db_session,
    template: Annotated[str, Depends(validate_template)]
):
    """ 템플릿 적용 """
    info = get_template_info(template)

    db.execute(update(Config).values(cf_theme=template))
    db.commit()

    from main import app  # 순환참조 방지

    # todo 미들웨어로 옮기기
    register_template_statics(app)
    user_template = UserTemplates()
    current_template_path = user_template.env.loader.searchpath
    if current_template_path[0] in user_template.env.loader.searchpath:
        user_template.env.loader.searchpath = [f"{TEMPLATES}/{template}"]
        user_template.env.cache.clear()

    return {"success": f"{info['template_name']} 템플릿으로 변경하였습니다."}


@router.get("/screenshot/{template}")
async def screenshot(template: str = Path(...)):
    try:
        file_path = f"{TEMPLATES}/{template}/screenshot.png"

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(file_path)
    except Exception as e:
        logger.error(f"An error occurred while serving the file: {e}")
        raise HTTPException(status_code=500, detail=str(e))