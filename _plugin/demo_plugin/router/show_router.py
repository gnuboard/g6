from fastapi import APIRouter

print('load show_router.py')
show_router = APIRouter()


@show_router.get("/show")
def show():
    return {"message": "Hello Plugin!"}
