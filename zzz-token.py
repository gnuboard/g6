from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# 토큰 발급을 담당하는 엔드포인트 (실제로는 데이터베이스 등을 사용해야 함)
@app.post("/token", tags=["authentication"])
async def generate_token(username: str = Form(...), password: str = Form(...)):
    if username == "user" and password == "pass":
        return {"access_token": "my_valid_token", "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# 토큰이 필요한 엔드포인트
@app.get("/private/", tags=["private"])
async def read_private_data(token: str = Depends(oauth2_scheme)):
    if token != "my_valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"message": "This is a private endpoint."}
