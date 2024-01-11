# 플러그인을 관리하는 메뉴
# 플러그인을 활성/비활성하고 플러그인의 신규 플러그인을 등록한다.
import logging

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.params import Form
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse

from admin.admin import templates
from core.plugin import (
    get_plugin_info, get_all_plugin_info, PLUGIN_DIR,
    PluginState, read_plugin_state, write_plugin_state
)
from lib.dependencies import validate_super_admin

logging.basicConfig(level=logging.INFO)
router = APIRouter()


@router.post("/plugin_detail", dependencies=[Depends(validate_super_admin)])
async def plugin_detail(request: Request, module_name: str = Form(...)):
    module = module_name.strip()
    info = get_plugin_info(module, PLUGIN_DIR)
    if not info:
        raise HTTPException(status_code=400, detail="The selected plugin is not installed.")

    if not info.get('plugin_name', None):
        # 플러그인의 readme.txt 파일의 양식 체크. 
        raise HTTPException(status_code=400, detail="플러그인의 상세 정보가 없습니다.")

    context = {
        "request": request,
        "name": info['plugin_name'],
        "info": info,
    }
    return templates.TemplateResponse("plugin_detail.html", context)


@router.get("/plugin_list", dependencies=[Depends(validate_super_admin)])
async def show_plugins(request: Request):
    """
    플러그인 목록
    """
    request.session["menu_key"] = "100420"
    info = get_all_plugin_info(PLUGIN_DIR)
    context = {
        "request": request,
        "plugin_list": info,
        "total_count": len(info),
    }

    return templates.TemplateResponse("plugin_list.html", context)


@router.post("/plugin_update")
async def update_plugin_state(
        request: Request,
        type: str = Form(...),
        plugin_name: str = Form(...),
        module_name: str = Form(...),
):
    """
    플러그인 활성/비활성화
    한번에 한가지씩만 상태변경이 가능하다.
    """
    if not request.state.is_super_admin:
        return JSONResponse(status_code=400, content={"message": "관리자만 접근 가능합니다."})

    if type == "enable":  # import를 하고 state_list 를 만든다.
        plugin_state = PluginState(
            plugin_name=plugin_name,
            module_name=module_name,
            is_enable=True,
        )
        message = "플러그인이 활성화 되었습니다."

    elif type == "disable":  # 패키지의 __init__.py 파일을 참조해서 state_list 를 만든다.
        plugin_state = PluginState(
            plugin_name=plugin_name,
            module_name=module_name,
            is_enable=False,
        )
        message = "플러그인 비활성화 되었습니다."
    else:
        return JSONResponse(status_code=400, content={"message": "잘못된 요청입니다."})

    plugin_state = [plugin_state]

    # update plugin state
    exist_plugins = read_plugin_state()
    if exist_plugins:
        for exist_plugin in exist_plugins:
            if exist_plugin.module_name == module_name:
                exist_plugin.is_enable = plugin_state[0].is_enable
                break
        else:
            exist_plugins.append(plugin_state[0])
        plugin_state = exist_plugins

    try:
        write_plugin_state(plugin_state)
    except Exception as e:

        logging.error(e)
        return JSONResponse(status_code=400, content={"message": "플러그인 상태를 변경할 수 없습니다."})

    return {"message": message}


@router.get("/plugin/screenshot/{module_name}")
async def show_screenshot(module_name: str):
    try:
        file_path = f"{PLUGIN_DIR}/{module_name}/screenshot.png"

        return FileResponse(file_path)
    except Exception as e:
        logging.error(f"An error occurred while serving the file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

