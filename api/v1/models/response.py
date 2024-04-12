"""API 응답 모델 정의"""
from fastapi import status
from pydantic import BaseModel


class MessageResponse(BaseModel):
    """메시지 응답 모델 (API Docs)"""
    message: str


response_401 = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": MessageResponse,
        "description": "인증되지 않은 요청"
    }
}


response_403 = {
    status.HTTP_403_FORBIDDEN: {
        "model": MessageResponse,
        "description": "권한 없음"
    }
}

response_404 = {
    status.HTTP_404_NOT_FOUND: {
        "model": MessageResponse,
        "description": "데이터 없음"
    }
}

response_409 = {
    status.HTTP_409_CONFLICT: {
        "model": MessageResponse,
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

response_500 = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "서버 오류"
    }
}

responses = {
    status.HTTP_403_FORBIDDEN: {"model": MessageResponse},
    status.HTTP_409_CONFLICT: {"model": MessageResponse},
}
