"""본인인증 서비스를 위한 추상 클래스와 유틸리티 함수를 제공합니다."""
import abc

import httpx
from fastapi.datastructures import FormData


class CertificateBase(metaclass=abc.ABCMeta):
    """본인인증 서비스를 위한 추상 클래스입니다."""
    @abc.abstractmethod
    async def get_request_data(self) -> dict:
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
