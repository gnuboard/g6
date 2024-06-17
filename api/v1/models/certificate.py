"""본인인증 모델 클래스를 정의한 파일입니다."""
from enum import Enum
from fastapi import Path, Query
from pydantic import BaseModel, Field


class Provider(Enum):
    """본인인증 서비스 제공자"""
    KCP = "kcp"
    INICIS = "inicis"


class CertificateType(Enum):
    """본인인증 타입"""
    HP = "hp"
    SIMPLE = "simple"
    IPIN = "ipin"


class PageType(Enum):
    """인증요청 페이지 타입"""
    REGISTER = "register"
    FIND = "find"


class CertificatePageRequest(BaseModel):
    """본인인증 페이지 요청 파라미터"""
    provider: Provider = Field(Path(title="provider", description="본인인증 서비스 제공자"))
    cert_type: CertificateType = Field(Path(title="certType", description="본인인증 타입"))
    page_type: PageType = Field(Path(title="인증요청 페이지", description="인증요청 페이지"))
    direct_agency: str = Field(Query("", title="특정 제휴사 노출옵션(KG이니시스)",
                                     description="특정 제휴사 노출옵션(KG이니시스)"))
    web_siteid: str = Field(Query("", title="사이트 식별코드(KCP)", description="사이트 식별코드(KCP)"))


class CertificatePageResponse(BaseModel):
    """본인인증 페이지 요청 결과 데이터"""
    request_url: str  # 요청 URL
    request_form: dict  # 요청 데이터
