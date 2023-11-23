import datetime
from dataclasses import dataclass

from fastapi import Form


@dataclass
class SmsConfig:
    cf_phone: str = Form(...)  # 발신번호
    cf_datetime: datetime = Form(...)  # 등록시간


@dataclass
class SmsForm:
    fo_no: int = Form(...)
    fg_no: int = Form(...)
    fg_member: str = Form(...)
    fo_name: str = Form(...)
    fo_content: str = Form(...)  # 문자내용
    fo_datetime: datetime = Form(...)


@dataclass
class SmsFormGroup:
    fg_no: int = Form(...)
    fg_name: str = Form(...)
    fg_count: int = Form(...)
    fg_member: int = Form(...)


@dataclass
class SmsHistory:
    hs_no: int = Form(...)
    wr_no: int = Form(...)
    wr_renum: int = Form(...)
    mb_no: int = Form(...)
    bg_no: int = Form(...)
    bk_no: str = Form(...)
    hs_name: str = Form(...)
    hs_hp: str = Form(...)
    hs_datetime: datetime = Form(...)
    hs_flag: int = Form(...)
    hs_code: str = Form(...)
    hs_memo: str = Form(...)
    hs_log: str = Form(...)


@dataclass
class SmsWrite:
    wr_no: int = Form(...)
    wr_renum: int = Form(...)
    wr_reply: str = Form(...)
    wr_message: str = Form(...)
    wr_booking: datetime = Form(...)
    wr_re_total: int = Form(...)
    wr_success: int = Form(...)
    wr_failure: int = Form(...)
    wr_datetime: datetime = Form(...)
    wr_memo: str = Form(...)
