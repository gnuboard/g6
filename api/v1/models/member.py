"""회원 모델"""
# TODO: 공통으로 사용하는 속성, 메서드는 상위 클래스로 분리
from datetime import datetime
from typing_extensions import Annotated

from fastapi import Body
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from lib.pbkdf2 import create_hash


class CreateMemberModel(BaseModel):
    """회원 가입 정보 모델"""
    # 추가 필드 허용
    model_config = ConfigDict(extra='allow')

    mb_id: Annotated[str, Body(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$",
                               title="아이디", description="3~20자의 영문, 숫자, _만 사용 가능합니다.")]
    mb_password: Annotated[str, Body(..., title="비밀번호")]
    mb_password_re: Annotated[str, Body(..., title="비밀번호 확인")]
    mb_nick: Annotated[str, Body(..., title="닉네임")]
    mb_name: Annotated[str, Body(..., title="이름")]
    mb_sex: Annotated[str, Body("", pattern=r"^[mf]?$", title="성별")]
    mb_email: Annotated[str, Body(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                                  title="이메일", description="이메일 형식에 맞게 입력해주세요.")]
    mb_homepage: Annotated[str, Body("", title="홈페이지")]
    mb_zip: Annotated[str, Body("", title="우편번호")]
    mb_addr_jibeon: Annotated[str, Body("", title="지번 주소")]
    mb_addr1: Annotated[str, Body("", title="기본 주소")]
    mb_addr2: Annotated[str, Body("", title="나머지 주소")]
    mb_addr3: Annotated[str, Body("", title="기타 주소")]
    mb_tel: Annotated[str, Body("", title="전화번호")]
    mb_hp: Annotated[str, Body("", title="휴대전화번호")]
    mb_signature: Annotated[str, Body("", title="서명")]
    mb_profile: Annotated[str, Body("", title="자기소개")]
    mb_recommend: Annotated[str, Body("", title="추천인 아이디")]

    mb_mailling: Annotated[int, Body(0, title="메일 수신 여부")]
    mb_sms: Annotated[int, Body(0, title="SMS 수신 여부")]
    mb_open: Annotated[int, Body(0, title="	회원정보 공개 여부")]

    @field_validator('mb_zip', mode='after')
    @classmethod
    def divide_zip(cls, v: str) -> str:
        """우편번호를 앞자리와 뒷자리 각각 3자리로 분리"""
        cls.mb_zip1 = v[:3]
        cls.mb_zip2 = v[3:6]
        return v

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'CreateMemberModel':
        """비밀번호와 비밀번호 확인이 일치하는지 검사"""
        pw1 = self.mb_password
        pw2 = self.mb_password_re
        if pw1 is not None and pw2 is not None and pw1 != pw2:
            raise ValueError('비밀번호가 일치하지 않습니다.')

        # convert to hash password
        self.mb_password = create_hash(pw1)

        return self

    @model_validator(mode='after')
    def init_fields(self) -> 'CreateMemberModel':
        """CreateMemberModel에서 선언되지 않은 필드를 초기화"""
        self.mb_level: int = 1
        self.mb_login_ip: str = ""
        # 회원가입에 필요 없는 필드 삭제
        del self.mb_password_re
        del self.mb_zip

        return self


class UpdateMemberModel(BaseModel):
    """회원 정보 수정 모델"""
    # 추가 필드 허용
    model_config = ConfigDict(extra='allow')

    mb_password: Annotated[str, Body(title="비밀번호")] = None
    mb_password_re: Annotated[str, Body(title="비밀번호 확인")] = None
    mb_nick: Annotated[str, Body(..., title="닉네임")]
    mb_name: Annotated[str, Body(..., title="이름")]
    mb_sex: Annotated[str, Body(pattern=r"^[mf]?$", title="성별")] = None
    mb_email: Annotated[str, Body(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                                  title="이메일", description="이메일 형식에 맞게 입력해주세요.")]
    mb_homepage: Annotated[str, Body(title="홈페이지")] = None
    mb_zip: Annotated[str, Body(title="우편번호")] = None
    mb_addr_jibeon: Annotated[str, Body(title="지번 주소")] = None
    mb_addr1: Annotated[str, Body(title="기본 주소")] = None
    mb_addr2: Annotated[str, Body(title="나머지 주소")] = None
    mb_addr3: Annotated[str, Body(title="기타 주소")] = None
    mb_tel: Annotated[str, Body(title="전화번호")] = None
    mb_hp: Annotated[str, Body(title="휴대전화번호")] = None
    mb_signature: Annotated[str, Body(title="서명")] = None
    mb_profile: Annotated[str, Body(title="자기소개")] = None

    mb_mailling: Annotated[int, Body(title="메일 수신 여부")] = None
    mb_sms: Annotated[int, Body(title="SMS 수신 여부")] = None
    mb_open: Annotated[int, Body(title="회원정보 공개 여부")] = None

    @field_validator('mb_zip', mode='after')
    @classmethod
    def divide_zip(cls, v: str) -> str:
        """우편번호를 앞자리와 뒷자리 각각 3자리로 분리"""
        cls.mb_zip1 = v[:3]
        cls.mb_zip2 = v[3:6]
        return v

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UpdateMemberModel':
        """비밀번호와 비밀번호 확인이 일치하는지 검사"""
        pw1 = self.mb_password
        pw2 = self.mb_password_re

        if pw1 is not None:
            if pw1 != pw2:
                raise ValueError('비밀번호가 일치하지 않습니다.')
            self.mb_password = create_hash(pw1)
        else:
            del self.mb_password

        return self

    @model_validator(mode='after')
    def init_update_fields(self) -> 'UpdateMemberModel':
        """UpdateMemberModel에서 선언되지 않은 필드를 초기화"""
        self.mb_nick_date = datetime.now()
        self.mb_open_date = datetime.now()
        # 회원가입에 필요 없는 필드 삭제
        del self.mb_password_re
        del self.mb_zip

        return self


class ResponseMemberModel(BaseModel):
    """회원 정보 응답 모델(임시)"""
    mb_id: str
    mb_name: str
    mb_nick: str
