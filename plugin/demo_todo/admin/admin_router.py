from typing import Optional

from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from admin.admin_config import get_admin_plugin_menus
from common.database import get_db
from lib.common import ADMIN_TEMPLATES_DIR, get_member_id_select, get_skin_select, get_editor_select, get_selected, \
    get_member_level_select, option_array_checked, get_admin_menus, generate_token, get_client_ip, check_token, \
    AlertException
from lib.plugin.service import get_all_plugin_module_names, PLUGIN_DIR
from ..models import Todo
from ..plugin_config import module_name, admin_router_prefix

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[PLUGIN_DIR, PLUGIN_TEMPLATES_DIR, ADMIN_TEMPLATES_DIR])
templates.env.globals["getattr"] = getattr
templates.env.globals["get_member_id_select"] = get_member_id_select
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_editor_select"] = get_editor_select
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals["option_array_checked"] = option_array_checked
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["generate_token"] = generate_token
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
def show_todo(request: Request, id: int, db: Session = Depends(get_db)):
    request.session["menu_key"] = module_name

    todo = db.query(Todo).filter(Todo.id == id).scalar()
    return templates.TemplateResponse(
        "admin/show.html", {
            "request": request,
            "todo": todo,
        })


@admin_router.get("/todos")
def show_todo_list(request: Request,
                   db: Session = Depends(get_db)):
    request.session["menu_key"] = module_name

    todos = db.query(Todo).all()

    return templates.TemplateResponse(
        "admin/todos.html", {
            "request": request,
            "todos": todos,
        })


@admin_router.get("/create")
def create_form(request: Request):
    request.session["menu_key"] = module_name

    todo = Todo(
        title='',
        content=''
    )
    return templates.TemplateResponse(
        "admin/create.html", {
            "request": request,
            "action_url": "/admin/todo/create",
            "todo": todo,
            "content": f"Hello {module_name}",
        })


@admin_router.post("/create")
def create(request: Request,
           title: str = Form(...),
           content: str = Form(...),
           token: str = Form(...),
           db: Session = Depends(get_db)):
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    todo = Todo(
        title=title,
        content=content
    )
    db.add(todo)
    db.commit()
    return RedirectResponse("/admin/todo/todos", status_code=302)


@admin_router.get("/update/{id}")
def update(request: Request,
           db: Session = Depends(get_db)):
    id = request.path_params.get('id')
    todo = db.query(Todo).filter(Todo.id == id).scalar()

    return templates.TemplateResponse("admin/create.html", {
        "request": request,
        "todo": todo,
        "action_url": f"/admin/todo/update/{id}",
    })


@admin_router.post("/update/{id}")
def update(request: Request,
           title: str = Form(...),
           content: str = Form(...),
           is_done: Optional[int] = Form(default=False),
           db: Session = Depends(get_db)):
    id = request.path_params.get('id')
    db.query(Todo).filter(Todo.id == id).update({
        "title": title,
        "content": content,
        "is_done": is_done
    })

    # DB 반영
    db.commit()

    return RedirectResponse("/admin/todo/todos", status_code=200)


@admin_router.post("/delete")
def update(request: Request,
           token: str = Form(...),
           ids: list = Form(..., alias='chk[]'),
           db: Session = Depends(get_db)):
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)
    db.query(Todo).filter(Todo.id.in_(ids)).delete()
    db.commit()
    return RedirectResponse(f"/admin/todo/todos", status_code=302)
