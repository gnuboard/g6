# router
from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter()

templates = Jinja2Templates(directory="templates/user")


@router.post("/")
def create_user(username: str = Form(...), db: Session = Depends(get_db)):
    user = models.User(username=username)
    db.add(user)
    db.commit()
    return {"username": username, "id": user.id}

@router.post("/post/")
def create_post(title: str = Form(...), user_id: int = Form(...), db: Session = Depends(get_db)):
    post = models.Post(title=title, user_id=user_id)
    db.add(post)
    db.commit()
    return {"title": title, "user_id": user_id}

@router.get("/{user_id}")
def get_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    # return {"username": user.username, "posts": [{"title": post.title, "id": post.id} for post in user.posts]}
    return templates.TemplateResponse("user.html", {"request": request, "user": user})
