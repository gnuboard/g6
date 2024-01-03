from typing import Optional

from fastapi import APIRouter, Depends, Form, Path
from sqlalchemy import select, insert, update, delete
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from core.database import db_session
from core.plugin import get_admin_plugin_menus, get_all_plugin_module_names
from core.template import ADMIN_TEMPLATES_DIR
from lib.common import get_member_id_select, get_skin_select, get_editor_select, get_selected, \
    get_member_level_select, option_array_checked, get_admin_menus, get_client_ip
from lib.dependencies import validate_token
from ..models import Todo
from ..plugin_config import module_name, admin_router_prefix

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[PLUGIN_TEMPLATES_DIR, ADMIN_TEMPLATES_DIR])
templates.env.globals["admin_menus"] = get_admin_menus()
templates.env.globals["getattr"] = getattr
templates.env.globals["get_member_id_select"] = get_member_id_select
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_editor_select"] = get_editor_select
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals["option_array_checked"] = option_array_checked
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_client_ip"] = get_client_ip
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names

admin_router = APIRouter(prefix=f'/{admin_router_prefix}', tags=['demo_admin'])


@admin_router.get("/test_demo_admin")
def show(request: Request):
    request.session["menu_key"] = module_name
    request.session["plugin_submenu_key"] = module_name + "1"

    return {"message": "Hello Admin Demo Plugin!",
            "pacakge": __package__,
            "__file__": __file__,
            "__name__": __name__,
            }


@admin_router.get("/todo/{id}")
def show_todo(
    request: Request,
    db: db_session,
    id: int = Path(...)
):
    request.session["menu_key"] = module_name

    todo = db.get(Todo, id)

    context = {
        "request": request,
        "todo": todo,
    }
    return templates.TemplateResponse("admin/show.html", context)


@admin_router.get("/todos")
def show_todo_list(
    request: Request,
    db: db_session,
):
    request.session["menu_key"] = module_name

    todos = db.scalars(select(Todo)).all()

    context = {
        "request": request,
        "todos": todos,
    }
    return templates.TemplateResponse("admin/todos.html", context)


@admin_router.get("/create")
def create_form(request: Request):
    request.session["menu_key"] = module_name

    todo = Todo(title='', content='')

    context = {
        "request": request,
        "action_url": "/admin/todo/create",
        "todo": todo,
        "content": f"Hello {module_name}",
    }
    return templates.TemplateResponse("admin/create.html", context)


@admin_router.post("/create", dependencies=[Depends(validate_token)])
def create(
    request: Request,
    db: db_session,
    title: str = Form(...),
    content: str = Form(...),
):
    db.execute(
        insert(Todo).values(
            title=title,
            content=content
        )
    )
    db.commit()

    return RedirectResponse("/admin/todo/todos", status_code=302)


@admin_router.get("/update/{id}")
def update_form(
    request: Request,
    db: db_session,
    id: int = Path(...)
):
    todo = db.get(Todo, id)

    context = {
        "request": request,
        "todo": todo,
        "action_url": f"/admin/todo/update/{id}",
    }
    return templates.TemplateResponse("admin/create.html", context)


@admin_router.post("/update/{id}")
def update_todo(
    request: Request,
    db: db_session,
    id: int = Path(...),
    title: str = Form(...),
    content: str = Form(...),
    is_done: Optional[int] = Form(default=False),
):
    db.execute(
        update(Todo).values(
            title=title,
            content=content,
            is_done=is_done
        ).where(Todo.id == id)
    )
    db.commit()

    return RedirectResponse("/admin/todo/todos", status_code=302)


@admin_router.post("/delete", dependencies=[Depends(validate_token)])
def delete_todo(
    request: Request,
    db: db_session,
    ids: list = Form(..., alias='chk[]'),
):
    db.execute(
        delete(Todo).where(Todo.id.in_(ids))
    )
    db.commit()

    return RedirectResponse(f"/admin/todo/todos", status_code=302)
