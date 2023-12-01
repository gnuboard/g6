import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import phpserialize
from fastapi import APIRouter
from fastapi.params import Depends, Form
from popbill import PopbillException
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.requests import Request

from common.database import get_db, SessionLocal
from common.models import Member
from plugin.popbill.models import SmsBook, SmsWrite, SmsHistory, SmsConfig
from plugin.popbill.router import messageService

admin_router = APIRouter(prefix="/sms_admin")


@admin_router.post("/ajax/sms_send")
async def send_sms(request: Request, wr_reply: str = Form(),
                   wr_message: str = Form(default=""),
                   message_subject: str = Form(default=""),
                   wr_target: Optional[str] = Form(default=None),
                   send_list: str = Form(default=""),  # gnuboard serialize  g, l, h, p
                   wr_by: Optional[str] = Form(default=None),  # year 년
                   wr_bm: Optional[str] = Form(default=None),  # month 월
                   wr_bd: Optional[str] = Form(default=None),  # day 일
                   wr_bh: Optional[str] = Form(default=None),  # hour 시
                   wr_bi: Optional[str] = Form(default=None),  # minute 분
                   adsYN: Optional[str] = Form(default="N"),
                   db: Session = Depends(get_db)):
    """문자 발송
    Args:
        wr_message (str): 문자 메시지
        send_list (str): 문자 메시지를 받을 휴대폰번호 - 자체규격 직렬화데이터
        wr_no (int): wr_no
        wr_by (int): year 년
        wr_bm (int): month 월
        wr_bd (int): day 일
        wr_bh (int): hour 시
        wr_bi (int): minute 분
        db (Session, optional)

        send_list: 규격
          g : group -  g,group_no
          l : level - l,member_level
          h : hp - {name: hp}
          p : personal - p,bk_no
          를 / 로 구분하여 직렬화
    """

    config = request.state.config
    if config.cf_sms_use != "popbill":
        return {"result": "fail", "msg": "popbill 사용이 비활성화 되어있습니다."}

    # 팝빌 설정 체크
    if not check_valid_callback(wr_reply):
        return {"result": "fail", "msg": "발신번호를 올바르게 입력해 주세요"}

    if not wr_message:
        return {"result": "fail", "msg": "메시지를 입력해 주세요"}

    if not send_list:
        return {"result": "fail", "msg": "문자 메시지를 받을 휴대폰번호를 입력해 주세요"}

    sms_config = db.query(SmsConfig).first()
    if not sms_config:
        return {"result": "fail", "msg": "문자 설정이 필요합니다."}

    # 예약일시
    if wr_by and wr_bm and wr_bd and wr_bh and wr_bi:
        wr_booking = f"{wr_by}-{wr_bm}-{wr_bd} {wr_bh}:{wr_bi}:00"
        booking_date = datetime.strptime(wr_booking, '%Y-%m-%d %H:%M:%S')
    else:
        booking_date = None  # 미지정시 바로전송    

    data_list = []
    hps = []

    is_check_duplicate = True
    duplicate_number_count = 0
    duplicate_data = {}
    duplicate_data['hp'] = []
    str_serialize = ""
    # bk is book

    send_list = send_list.split('/')
    for send_item in send_list:
        send_target_data = send_item.split(',')
        group_type = send_target_data[0]

        # 그룹전송
        if group_type == 'g':
            send_group_number = send_target_data[1]
            group_result = db.query(SmsBook).filter(
                SmsBook.bg_no == send_group_number,
                SmsBook.bk_receipt == 1).all()
            for row in group_result:
                row.bk_hp = get_hp(row.bk_hp)
                if not row.bk_hp:
                    continue
                if is_check_duplicate and check_duplicate_item(hps, row.bk_hp):
                    duplicate_number_count += 1
                    duplicate_data['hp'].append(row.bk_hp)
                    continue

                data_list.append({
                    'sms_book_hp': row.bk_hp,
                    'sms_book_name': row.bk_name,
                    'mb_id': row.mb_id,
                    'bg_no': row.bg_no,
                    'bk_no': row.bk_no
                })
                hps.append(row.bk_hp)


        # 권한 레벨
        elif group_type == 'l':
            mb_level = send_target_data[1]

            member_result = db.query(Member.mb_id, Member.mb_name, Member.mb_nick, Member.mb_hp).filter(
                Member.mb_level == mb_level,
                Member.mb_sms == 1,
                Member.hp != '').all()

            for member in member_result:
                hp = get_hp(member.mb_hp)
                if not hp:
                    continue
                if is_check_duplicate and check_duplicate_item(hps, hp):
                    duplicate_number_count += 1
                    duplicate_data['hp'].append(hp)
                    continue

                book_result = db.query(SmsBook).filter(SmsBook.mb_id == member.mb_id).scalar()
                bk_no = None
                bg_no = None
                if book_result:
                    bg_no = book_result.bg_no
                    bk_no = book_result.bk_no

                data_list.append({
                    'sms_book_hp': hp,
                    'sms_book_name': member.mb_name,
                    "mb_id": member.mb_id,
                    "bg_no": bg_no,
                    "bk_no": bk_no
                })
                hps.append(member.mb_hp)

        # 휴대폰
        elif group_type == 'h':
            values = send_target_data[1]
            values = values.split(':')
            name = values[0]
            hp = values[1]
            hp = get_hp(hp, '-')

            if not hp:
                continue

            if is_check_duplicate and check_duplicate_item(hps, {hp}):
                duplicate_number_count += 1
                duplicate_data['hp'].append(hp)
                continue
            data_list.append({
                'sms_book_hp': hp,
                'sms_book_name': name,
                "mb_id": None,
                "bg_no": None,
                "bk_no": None,
            })
            hps.append(hp)

        if group_type == 'p':  # 개인 선택
            target_bk_no = send_target_data[1]

            result_contract: SmsBook = db.query(SmsBook).filter(SmsBook.bk_no == target_bk_no).scalar()
            result_contract.bk_hp = get_hp(result_contract.bk_hp)

            if not result_contract.bk_hp:
                continue
            if is_check_duplicate and check_duplicate_item(hps, result_contract.bk_hp):
                duplicate_number_count += 1
                duplicate_data['hp'].append(result_contract.bk_hp)
                continue

            data_list.append({
                "sms_book_hp": result_contract.bk_hp,
                "sms_book_name": result_contract.bk_name,
                "mb_id": result_contract.mb_id,
                "bg_no": result_contract.bg_no,
                "bk_no": result_contract.bk_no
            })
            hps.append(result_contract.bk_hp)

    total_count = len(data_list)
    if total_count > 1000:
        return {"result": "fail", "msg": "최대 1000건까지만 동시발송 가능합니다."}

    if len(duplicate_data.get('hp', [])) > 0:
        duplicate_data['total'] = duplicate_number_count
        # 기존 DB의 wr_memo 컬럼 데이터가 php serialize 포멧으로 저장.
        str_serialize = phpserialize.dumps(duplicate_data)

    if total_count > 1:
        # 대량 전송
        messages = []
        for data in data_list:
            messages.append(MultiMessage(
                snd=None,
                sndnm="발신자명",
                rcv=data.get('sms_book_hp'),
                rcvnm=data.get('sms_book_name'),
                msg=None,
                sjt=message_subject,
                interOPRefKey=None
            ))

        send_result = send_sms_multi(
            data_list,
            message_subject,
            message_content=wr_message,
            messages=messages,
            sender_number=wr_reply,
            sender_name="발신자명",
            booking_date=booking_date,
            total_count=total_count,
            str_serialize=str_serialize,
            adsYN=adsYN
        )


    elif total_count == 1:
        send_result = send_sms_one(
            data_list=data_list,
            message_subject=message_subject,
            message=wr_message,
            sender_number=wr_reply,
            booking_date=booking_date,
            total_count=total_count,
            str_serialize=str_serialize,
            adsYN=adsYN
        )


    else:
        return {"result": "fail", "msg": "발송할 번호가 없습니다."}

    # sms_result_save(send_result, wr_reply, wr_message, wr_target, wr_no, wr_total, wr_booking, str_serialize, db)
    # try:
    # 
    #     request_number = messageService.sendSMS('corpNum', wr_reply, "수신번호", "수신자명", "내용", booking_date, "adsYN",
    #                                             "USERid",
    #                                             "발신자명", RequestNum="")
    #     
    # 
    # 
    # except PopbillException as e:
    #     logging.critical(f"fail send message popbill code:{e.code} message: {e.message}", exc_info=True)
    #     return {"result": "fail", "msg": f"문자 발송에 실패했습니다. \n{e.message}"}


def send_sms_one(data_list, message_subject, message, sender_number, booking_date, total_count, str_serialize,
                 adsYN="N"):
    send_result_number = 0
    error_code = None
    error_message = None
    # 에러
    # print(data_list[0].sms_book_hp)
    # print('data_list[0].sms_book_hp')
    COMPANY_REGISTER_NUM = os.getenv("POPBILL_COMPANY_REGISTER_NUM")
    POPBILL_LINK_ID = os.getenv("POPBILL_LINK_ID")
    with SessionLocal() as db:
        sms_config = db.query(SmsConfig).first()
        sender_number = sms_config.cf_phone
    if not sms_config:
        raise PopbillException(-99999999, "문자 설정이 필요합니다.")

    try:
        send_result_number = messageService.sendSMS(
            COMPANY_REGISTER_NUM, sender_number, data_list[0].get('sms_book_hp'),
            ReceiverName=None,
            Contents=message,
            reserveDT=booking_date,
            adsYN=adsYN,
            UserID=POPBILL_LINK_ID,
            SenderName="발신자명",
            RequestNum=None
        )
        print('send_result_number')
        print(send_result_number)

    except PopbillException as e:
        logging.critical(f"fail send message popbill error code:{e.code} message: {e.message}", exc_info=True)
        error_message = e.message
        error_code = e.code
        print('-----------------------')
        print('error_message')
        print(error_message)
        print('error_code')
        print(error_code)

    except Exception as e:
        logging.critical(f"fail send message error", exc_info=True)
        error_message = '문자 발송에 실패했습니다.'
        error_code = 5  # 팝빌이외의 에러

    success_count = 0
    fail_count = 0

    # success
    if send_result_number and error_message is None:
        success_count += 1
        hs_code = "0000"
        hs_memo = f"{data_list[0].get('sms_book_hp')} 로 전송했습니다. 팝빌전송번호: {send_result_number}"
        hs_log = {"send_result_number": send_result_number}
        hs_flag = 1  # success constant

    # fail
    else:
        fail_count += 1
        hs_code = error_code
        hs_memo = error_message
        hs_log = error_message
        hs_flag = 0  # fail constant

    """
    sql_query("insert into {$g5['sms5_history_table']} set wr_no='$wr_no', 
                wr_renum=0,
                 bg_no='{$row['bg_no']}', 
                 mb_id='{$row['mb_id']}', 
                 bk_no='{$row['bk_no']}', 
                 hs_name='".addslashes($row['bk_name'])."', 
                 hs_hp='{$row['bk_hp']}', hs_datetime='".G5_TIME_YMDHIS."', 
                 hs_flag='$hs_flag', 
                 hs_code='$hs_code',
                 hs_memo='".addslashes($hs_memo)."',
                 hs_log='".addslashes($log)."'", 
                 false);
    """
    # sms_write 테이블이 auto_increment 지정안되어 있어서 wr_no 를 계산해야함.
    with SessionLocal() as db:
        latest_id = db.query(func.max(SmsWrite.wr_no)).scalar()

        if latest_id:
            latest_id += 1
        else:
            latest_id = 1

        new_history = SmsHistory(
            wr_no=latest_id,
            bg_no=data_list[0].get('bg_no'),
            mb_id=data_list[0].get('mb_id'),
            bk_no=data_list[0].get('bk_no'),
            hs_name=data_list[0].get('sms_book_name'),
            hs_hp=data_list[0].get('sms_book_hp'),
            hs_datetime=datetime.now(),
            hs_flag=hs_flag,
            hs_code=hs_code,
            hs_memo=hs_memo,
            hs_log=hs_log
        )

        db.add(new_history)

        sms_write = SmsWrite(
            wr_no=latest_id,
            wr_renum=0,
            wr_reply=sender_number,
            wr_success=success_count,
            wr_failure=fail_count,
            wr_message=message,
            wr_booking=booking_date,
            wr_total=total_count,
            wr_datetime=datetime.now(),
            wr_memo=str_serialize
        )
        db.add(sms_write)
        db.commit()


def send_sms_multi(data_list, message_subject, message_content, messages, sender_number, sender_name, booking_date,
                   total_count,
                   str_serialize,
                   adsYN="N"):
    send_result_number = 0
    error_code = None
    error_message = None
    """
    단일메시지를 다수의 번호에 전송 요청을합니다. (동보전송)
    """

    COMPANY_REGISTER_NUM = os.getenv("xxxPOPBILL_COMPANY_REGISTER_NUM")
    POPBILL_LINK_ID = os.getenv("xxxxxxPOPBILL_LINK_ID")
    with SessionLocal() as db:
        sms_config = db.query(SmsConfig).first()
        sender_number = sms_config.cf_phone
    if not sms_config:
        raise PopbillException(-99999999, "문자 설정이 필요합니다.")

    try:
        send_result_number = messageService.sendSMS_multi(
            COMPANY_REGISTER_NUM,
            sender=sender_number,
            senderName="발신자명",
            Messages=messages,
            reserveDT=booking_date,
            adsYN=adsYN,
            UserID=POPBILL_LINK_ID,
            SenderName="발신자명",
            RequestNum=None
        )
        print('send_result_number')
        print(send_result_number)

    except PopbillException as e:
        logging.critical(f"fail send message popbill error code:{e.code} message: {e.message}", exc_info=True)
        error_message = e.message
        error_code = e.code
        print('error_message')
        print(error_message)
        print('error_code')
        print(error_code)

    except Exception as e:
        logging.critical(f"fail send message error", exc_info=True)
        error_message = '문자 발송에 실패했습니다.'
        error_code = 5  # 팝빌이외의 에러

    success_count = 0
    fail_count = 0

    # success
    if send_result_number and error_message is None:
        success_count += 1
        hs_code = "0000"
        hs_memo = f"{data_list[0].get('sms_book_hp')} 로 전송했습니다. 팝빌전송번호: {send_result_number}"
        hs_log = {"send_result_number": send_result_number}
        hs_flag = 1  # success constant

    # fail
    else:
        fail_count += 1
        hs_code = error_code
        hs_memo = error_message
        hs_log = error_message
        hs_flag = 0  # fail constant

    """
    sql_query("insert into {$g5['sms5_history_table']} set wr_no='$wr_no', 
                wr_renum=0,
                 bg_no='{$row['bg_no']}', 
                 mb_id='{$row['mb_id']}', 
                 bk_no='{$row['bk_no']}', 
                 hs_name='".addslashes($row['bk_name'])."', 
                 hs_hp='{$row['bk_hp']}', hs_datetime='".G5_TIME_YMDHIS."', 
                 hs_flag='$hs_flag', 
                 hs_code='$hs_code',
                 hs_memo='".addslashes($hs_memo)."',
                 hs_log='".addslashes($log)."'", 
                 false);
    """

    # sms_write 테이블이 auto_increment 지정안되어 있어서 wr_no 를 계산해야함.
    with SessionLocal() as db:
        latest_id = db.query(func.max(SmsWrite.wr_no)).scalar()

        if latest_id:
            latest_id += 1
        else:
            latest_id = 1

        new_history = SmsHistory(
            wr_no=latest_id,
            bg_no=data_list[0].get('bg_no'),
            mb_id=data_list[0].get('mb_id'),
            bk_no=data_list[0].get('bk_no'),
            hs_name=data_list[0].get('sms_book_name'),
            hs_hp=data_list[0].get('sms_book_hp'),
            hs_datetime=datetime.now(),
            hs_flag=hs_flag,
            hs_code=hs_code,
            hs_memo=hs_memo,
            hs_log=hs_log
        )

        db.add(new_history)

        sms_write = SmsWrite(
            wr_no=latest_id,
            wr_renum=0,
            wr_reply=sender_number,
            wr_success=success_count,
            wr_failure=fail_count,
            wr_message=messages,
            wr_booking=booking_date,
            wr_total=total_count,
            wr_datetime=datetime.now(),
            wr_memo=str_serialize
        )
        db.add(sms_write)
        db.commit()


def sms_result_save():
    """sms 발송 결과 저장
    """


def sms_multi_send():
    corpNum = ""  # 팝빌회원 사업자번호, '-' 제외 10자리


def get_hp(hp, seperator='-'):
    hp = str(hp).replace(seperator, '')
    return hp


def check_duplicate_item(arr, val):
    for item in arr:
        if item == val:
            return True
    return False


def check_valid_callback(callback_number):
    if not callback_number:
        return False

    callback_number = re.sub(r'[^0-9]', '', callback_number)

    # 1588로 시작하면 총 8자리
    if callback_number.startswith('1588') and len(callback_number) != 8:
        return False

    # 지역번호 시작하면 총 9자리 또는 10자리
    if callback_number.startswith('02') and len(callback_number) not in (9, 10):
        return False

    # 1366은 그 자체가 원번호이기에 다른게 붙으면 차단
    if callback_number.startswith('1366'):
        return False

    # 030으로 시작하면 총 10자리 또는 11자리
    if callback_number.startswith('030') and len(callback_number) != 10:
        return False

    general_pattern = re.compile(r'^(02|0[3-6]\d|01[01356789]|070|080|007)-?\d{3,4}-?\d{4,5}$')
    special_pattern = re.compile(r'^(15|16|18)\d{2}-?\d{4,5}$')

    if not (general_pattern.match(callback_number) or special_pattern.match(callback_number)):
        return False

    if re.match(r'^(02|0[3-6]\d|01[01356789]|070|080)-?0{3,4}-?\d{4}$', callback_number):
        return False

    return True


@dataclass
class MultiMessage:
    """문자 발송용 데이터 클래스
     Attributes:
        snd: 발신번호
        sndnm: 발신자명
        rcv: 수신번호
        rcvnm: 수신자명
        msg: 메시지 내용
        sjt: 문자제목
        interOPRefKey: 파트너 지정키
    """
    snd: Optional[str]  # 발신번호
    sndnm: Optional[str]  # 발신자명
    rcv: str  # 수신번호
    rcvnm: str  # 수신자명
    msg: Optional[str]  # 메시지 내용
    sjt: str  # 문자제목
    interOPRefKey: Optional[str]  # 파트너 지정키
