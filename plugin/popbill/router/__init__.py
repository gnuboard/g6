from fastapi import APIRouter
from popbill import MessageService, PopbillException
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from lib.common import TEMPLATES_DIR, default_if_none, generate_token, is_admin
from lib.plugin.service import get_all_plugin_module_names
from plugin.popbill import POPBILL_IS_TEST, POPBILL_IP_RESTRICT_ON_OFF, POPBILL_USE_STATIC_IP, POPBILL_USE_LOCALTIME_YN, \
    POPBILL_LINK_ID, POPBILL_SECRET_KEY, PLUGIN_TEMPLATES_DIR

templates = Jinja2Templates(directory=[TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])

templates.env.globals["is_admin"] = is_admin
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals['getattr'] = getattr
templates.env.globals["generate_token"] = generate_token
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names

router = APIRouter(prefix="/popbill")
messageService = MessageService(POPBILL_LINK_ID, POPBILL_SECRET_KEY)
# 연동환경 설정값, 개발용(True), 상업용(False)
messageService.IsTest = POPBILL_IS_TEST

# 인증토큰 IP제한기능 사용여부, 권장(True)
messageService.IPRestrictOnOff = POPBILL_IP_RESTRICT_ON_OFF

# 팝빌 API 서비스 고정 IP 사용여부, true-사용, false-미사용, 기본값(false)
messageService.UseStaticIP = POPBILL_USE_STATIC_IP

# 로컬시스템 시간 사용여부, 권장(True)
messageService.UseLocalTimeYN = POPBILL_USE_LOCALTIME_YN
@router.get("/send_sms")
def send_sms(request: Request):
    try:
        # 팝빌회원 사업자번호
        CorpNum = "1234567890"

        # 팝빌회원 아이디
        UserID = "testkorea"

        # 발신번호
        Sender = "07043042991"

        # 발신자명
        SenderName = "발신자명"

        # 수신번호
        ReceiverNum = "010111222"

        # 수신자명
        ReceiverName = "수신자명"

        # 단문메시지 내용, 90Byte 초과시 길이가 조정되 전송됨
        Contents = "문자 API 단건전송 테스트"

        # 예약전송시간, 작성형식:yyyyMMddHHmmss, 공백 기재시 즉시전송
        reserveDT = ""

        # 광고문자 전송여부
        adsYN = False

        # 접수번호
        receiptNum = messageService.sendSMS(CorpNum, Sender, ReceiverNum, ReceiverName,
                                            Contents, reserveDT, adsYN, UserID, SenderName, RequestNum=None)
        context = {
            'request': request,
            'receiptNum': receiptNum
        }
        return templates.TemplateResponse('response.html',
                                          context)  # render(request, 'response.html', {'receiptNum': receiptNum})
    except PopbillException as PE:
        return templates.TemplateResponse('response.html', {request: request, 'code': PE.code, 'message': PE.message})
        # render(request, 'exception.html', {'code': PE.code, 'message': PE.message})
