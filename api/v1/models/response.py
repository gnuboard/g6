"""API 응답 모델 정의"""
from fastapi import status
from pydantic import BaseModel


class Message(BaseModel):
    """메시지 응답 모델 (API Docs)"""
    detail: str


response_403 = {
    status.HTTP_403_FORBIDDEN: {
        "model": Message,
        "description": "권한 없음"
    }
}

response_404 = {
    status.HTTP_404_NOT_FOUND: {
        "model": Message,
        "description": "데이터 없음"
    }
}

response_409 = {
    status.HTTP_409_CONFLICT: {
        "model": Message,
        "description": "중복된 데이터"
    }
}

response_422 = {
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": "입력값 오류",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/HTTPValidationError"
                }
            }
        }
    }
}

responses = {
    status.HTTP_403_FORBIDDEN: {"model": Message},
    status.HTTP_409_CONFLICT: {"model": Message},
}
