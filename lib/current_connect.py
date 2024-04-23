"""현재 접속자 관련 기능을 제공하는 모듈입니다."""
import re

from fastapi import Request

from core.database import DBConnect
from service.current_connect_service import CurrentConnectService


def get_current_login_count(request: Request,
                            only_member: bool = False) -> int:
    """현재 접속자수를 반환하는 함수"""
    with DBConnect().sessionLocal() as db:
        service = CurrentConnectService(request, db)
        return service.fetch_total_records(only_member)


def hide_ip_address(ip: str) -> str:
    """IP 주소를 가려주는 함수"""
    return re.sub(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)",
                  "\\1.#.#.\\4", ip)
