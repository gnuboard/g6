"""회원 관련 의존성을 정의합니다."""
# TODO: 회원 관련 함수, 클래스를 공통으로 사용할 수 있도록 처리가 필요
from typing_extensions import Annotated

from fastapi import Request

from core.database import db_session
from api.v1.models.memo import CreateMemoModel


def validate_create_memo(
    request: Request,
    db: db_session,
    data: CreateMemoModel
):
    return data