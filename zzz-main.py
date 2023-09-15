from fastapi import FastAPI
from app.users import router as users_router
from app.posts import router as posts_router

app = FastAPI()

app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(posts_router, prefix="/posts", tags=["posts"])

@app.get("/")
async def root():
    return {"message": "Hello root"}