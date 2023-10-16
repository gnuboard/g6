from dataclasses import dataclass

from fastapi import Form
from typing_extensions import Optional

from common import *


@dataclass
class MemberForm:
    mb_name: Optional[str] = Form(default="")
    mb_nick: Optional[str] = Form(default="")
    mb_email: Optional[str] = Form(default="")
    mb_birth: Optional[datetime] = Form(None)
    mb_addr1: Optional[str] = Form(default="")
    mb_addr2: Optional[str] = Form(default="")
    mb_addr3: Optional[str] = Form(default="")
    mb_addr_jibeon: Optional[str] = Form(default="")
    mb_zip1: Optional[str] = Form(default="")
    mb_zip2: Optional[str] = Form(default="")
    mb_signature: Optional[str] = Form(default="")
    mb_profile: Optional[str] = Form(default="")
    mb_open: Optional[int] = 1
    mb_sms: Optional[bool] = Form(None)
    mb_mailling: Optional[bool] = Form(None)
    mb_memo: Optional[str] = Form(default="")
    mb_hp: Optional[str] = Form(None)
    mb_tel: Optional[str] = Form(None)
    mb_homepage: Optional[str] = Form(default="")
    mb_sex: Optional[str] = Form(default="")
    mb_recommend: str = Form(default="")
    mb_1: Optional[str] = Form(default="")
    mb_2: Optional[str] = Form(default="")
    mb_3: Optional[str] = Form(default="")
    mb_4: Optional[str] = Form(default="")
    mb_5: Optional[str] = Form(default="")
    mb_6: Optional[str] = Form(default="")
    mb_7: Optional[str] = Form(default="")
    mb_8: Optional[str] = Form(default="")
    mb_9: Optional[str] = Form(default="")
    mb_10: Optional[str] = Form(default="")
