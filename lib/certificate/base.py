"""본인인증 서비스를 위한 추상 클래스와 유틸리티 함수를 제공합니다."""
import abc
import random
from datetime import datetime

import httpx
from fastapi import Request
from fastapi.datastructures import FormData


class CertificateBase(metaclass=abc.ABCMeta):
    """본인인증 서비스를 위한 추상 클래스입니다."""
    @abc.abstractmethod
    def get_request_cert_page_url(self) -> str:
        """인증 페이지를 요청할 URL을 반환합니다."""

    @abc.abstractmethod
    async def get_request_data(self, **kwargs) -> dict:
        """인증 창을 띄우기 위한 데이터를 반환합니다."""

    @abc.abstractmethod
    async def get_result_data(self, response: FormData) -> dict:
        """인증 결과 데이터를 반환합니다."""


async def post_request(url: str, data: dict, headers: dict = None, timeout: float = 5.0) -> dict:
    """POST 요청"""
    base_headers = {
        'charset': 'UTF-8',
        'Content-Type': 'application/json'
    }
    if headers:
        base_headers.update(headers)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers, timeout=timeout)
    return response.json()


def create_cert_unique_id() -> str:
    """본인인증 고유값을 생성합니다."""
    timestamp = int(datetime.now().timestamp())
    random_num = random.randint(1000, 9999)

    return f"G6_{timestamp}{random_num}"


def create_result_url(request: Request, name: str, **kwargs) -> str:
    """본인인증 결과 URL을 생성합니다."""
    return str(request.url_for(
        name,
        provider=kwargs.get('provider'),
        cert_type=kwargs.get('cert_type'),
        page_type=kwargs.get('page_type')
    ))
