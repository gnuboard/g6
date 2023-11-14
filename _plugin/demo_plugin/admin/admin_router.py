from fastapi import APIRouter

admin_router = APIRouter(tags=['demo_admin'])


@admin_router.get("/test_admin")
def show():
    return {"message": "Hello ADMIN demo Plugin!"}
