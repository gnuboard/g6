from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, Text, Index, PrimaryKeyConstraint, Boolean

from common.database import DB_TABLE_PREFIX
from common.models import Base


class SmsConfig(Base):
    """
    sms 환경설정 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "sms5_config"
    __table_args__ = (
        PrimaryKeyConstraint('cf_phone'),  # tuple 이라 , 를 붙여줘야함.
    )

    cf_phone = Column('cf_phone', String(255), nullable=False, default='')
    cf_datetime = Column('cf_datetime', DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))


class SmsForm(Base):
    """
    sms form 테이블
    """
    __tablename__ = DB_TABLE_PREFIX + 'sms5_form'

    fo_no = Column(Integer, primary_key=True, autoincrement=True)
    fg_no = Column(Integer, nullable=False, default=0)
    fg_member = Column(String(1), nullable=False, default='0', comment='폼 그룹 회원 여부')  # todo
    fo_name = Column(String(255), nullable=False, default='', comment='폼 이름')
    fo_content = Column(Text, nullable=False, comment='폼 내용')
    fo_datetime = Column(DateTime, nullable=False,
                         default=datetime(1, 1, 1, 0, 0, 0), comment='폼 생성일')

    Index('idx_fg_no_fo_no', 'fg_no', 'fo_no', unique=False)


class SmsFormGroup(Base):
    __tablename__ = DB_TABLE_PREFIX + 'sms5_form_group'
    # 폼 그룹 테이블

    fg_no = Column(Integer, primary_key=True, autoincrement=True)
    fg_name = Column(String(255), nullable=False, default='')
    fg_count = Column(Integer, nullable=False, default=0)
    fg_member = Column(Boolean, nullable=False, comment='폼 그룹 회원 여부')

    Index('idx_fg_name', 'fg_name', unique=False)


class SmsHistory(Base):
    __tablename__ = DB_TABLE_PREFIX + 'sms5_history'
    """sms 발송내역 로그
    """

    hs_no = Column(Integer, primary_key=True, autoincrement=True)
    wr_no = Column(Integer, nullable=False, default=0)
    wr_renum = Column(Integer, nullable=False, default=0)
    bg_no = Column(Integer, nullable=False, default=0)
    mb_no = Column(Integer, nullable=False, default=0)
    mb_id = Column(String(20), nullable=False, default='')
    bk_no = Column(Integer, nullable=False, default=0)
    hs_name = Column(String(30), nullable=False, default='')
    hs_hp = Column(String(255), nullable=False, default='')
    hs_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    hs_flag = Column(Integer, nullable=False, default=0)  # tinyint
    hs_code = Column(String(255), nullable=False, default='')
    hs_memo = Column(String(255), nullable=False, default='')
    hs_log = Column(String(255), nullable=False, default='')

    Index('idx_wr_no', 'wr_no', unique=False)
    Index('idx_mb_no', 'mb_no', unique=False)
    Index('idx_bk_no', 'bk_no', unique=False)
    Index('idx_hs_hp', 'hs_hp', unique=False)
    Index('idx_hs_code', 'hs_code', unique=False)
    Index('idx_bg_no', 'bg_no', unique=False)
    Index('idx_mb_id', 'mb_id', unique=False)


class SmsWrite(Base):
    __tablename__ = DB_TABLE_PREFIX + 'sms5_write'
    # sms 발송내역

    wr_no = Column(Integer, primary_key=True, nullable=False, default=1)
    wr_renum = Column(Integer, primary_key=True, nullable=False, default=0)  # todo 재발송이랑 연관있음.
    wr_reply = Column(String(255), nullable=False, default='')
    wr_message = Column(Text, nullable=False)
    wr_booking = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    wr_total = Column(Integer, nullable=False, default=0)
    wr_re_total = Column(Integer, nullable=False, default=0)
    wr_success = Column(Integer, nullable=False, default=0)
    wr_failure = Column(Integer, nullable=False, default=0)
    wr_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    wr_memo = Column(Text, nullable=False, comment='memo, php serialize data')


class SmsBook(Base):
    __tablename__ = DB_TABLE_PREFIX + 'sms5_book'

    bk_no = Column(Integer, primary_key=True, autoincrement=True)
    bg_no = Column(Integer, nullable=False, default=0)
    mb_no = Column(Integer, nullable=False, default=0)
    mb_id = Column(String(20), nullable=False, default='')
    bk_name = Column(String(255), nullable=False, default='')
    bk_hp = Column(String(255), nullable=False, default='')
    bk_receipt = Column(Integer, nullable=False, default=0)
    bk_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    bk_memo = Column(Text, nullable=False)

    # Index definitions
    Index('idx_bk_name', 'bk_name')
    Index('idx_bk_hp', 'bk_hp')
    Index('idx_mb_no', 'mb_no')
    Index('idx_bg_no_bk_no', 'bg_no', 'bk_no')
    Index('idx_mb_id', 'mb_id')


class SmsBookGroup(Base):
    __tablename__ = DB_TABLE_PREFIX + 'sms5_book_group'

    bg_no = Column(Integer, primary_key=True, autoincrement=True)
    bg_name = Column(String(255), nullable=False, default='')
    bg_count = Column(Integer, nullable=False, default=0)
    bg_member = Column(Integer, nullable=False, default=0)
    bg_nomember = Column(Integer, nullable=False, default=0)
    bg_receipt = Column(Integer, nullable=False, default=0)
    bg_reject = Column(Integer, nullable=False, default=0)

    # Index definitions
    Index('idx_bg_name', 'bg_name')
