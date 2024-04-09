from fastapi import APIRouter, Request

from core.template import AdminTemplates

router = APIRouter()
templates = AdminTemplates()

SERVICE_MENU_KEY = "100400"


@router.get("/service")
async def service_view(request: Request):
    """
    부가서비스
    """
    request.session["menu_key"] = SERVICE_MENU_KEY

    context = {
        "request": request,
    }
    return templates.TemplateResponse("service.html", context)
