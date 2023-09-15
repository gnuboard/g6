from main import app
# 아래와 같은 방식으로 사용자의 라우터를 추가할 수 있음
from user_sample import router as users_router
app.include_router(users_router, prefix="/user_sample", tags=["user_sample"])