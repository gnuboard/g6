from typing import Optional

from fastapi import APIRouter
from popbill import MessageService
from starlette.templating import Jinja2Templates

from lib.common import TEMPLATES_DIR, default_if_none, generate_token, is_admin
from plugin.popbill import POPBILL_IS_TEST, POPBILL_IP_RESTRICT_ON_OFF, POPBILL_UseStaticIP, POPBILL_UseLocalTimeYN

# def sendSMS(CorpNum: str, Sender: str, Receiver: str, ReceiverName: str, Contents: str, reserveDT: str,
#             adsYN: bool = False, UserID: Optional[str] = None, SenderName: Optional[str] = None,
#             RequestNum: Optional[str] = None):

templates = Jinja2Templates(directory=TEMPLATES_DIR, extensions=["jinja2.ext.i18n"])
templates.env.globals["is_admin"] = is_admin
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals['getattr'] = getattr
templates.env.globals["generate_token"] = generate_token

router = APIRouter(prefix="/popbill")
messageService = MessageService('link', 'secretkey')
# 연동환경 설정값, 개발용(True), 상업용(False)
messageService.IsTest = POPBILL_IS_TEST

# 인증토큰 IP제한기능 사용여부, 권장(True)
messageService.IPRestrictOnOff = POPBILL_IP_RESTRICT_ON_OFF

# 팝빌 API 서비스 고정 IP 사용여부, true-사용, false-미사용, 기본값(false)
messageService.UseStaticIP = POPBILL_UseStaticIP

# 로컬시스템 시간 사용여부, 권장(True)
messageService.UseLocalTimeYN = POPBILL_UseLocalTimeYN