from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, Index, text, DateTime, Date, Time, Boolean, BIGINT, UniqueConstraint
from typing import List

# TINYINT 대신 Integer 사용하기 바랍니다.
# from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DynamicMapped, Mapped, relationship, declarative_base
from datetime import datetime, date
from core.database import DBConnect

Base = declarative_base()

DB_TABLE_PREFIX = DBConnect().table_prefix or "g6_"


class Config(Base):
    """
    환경설정 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "config"

    cf_id = Column(Integer, primary_key=True)
    cf_title = Column(String(255), nullable=False, default="")
    cf_theme = Column(String(100), nullable=False, default="")
    cf_admin = Column(String(100), nullable=False, default="")
    cf_admin_email = Column(String(100), nullable=False, default="")
    cf_admin_email_name = Column(String(100), nullable=False, default="")
    cf_add_script = Column(Text, nullable=False, default="")
    cf_use_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_point_term = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_copy_log = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_email_certify = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_login_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_cut_name = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_nick_modify = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_new_skin = Column(String(50), nullable=False, default="")
    cf_new_rows = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_search_skin = Column(String(50), nullable=False, default="")
    cf_connect_skin = Column(String(50), nullable=False, default="")
    cf_faq_skin = Column(String(50), nullable=False, default="")
    cf_read_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_write_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_comment_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_download_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_write_pages = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_mobile_pages = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_link_target = Column(String(50), nullable=False, default="")
    cf_bbs_rewrite = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_delay_sec = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_filter = Column(Text, nullable=False, default="")
    cf_possible_ip = Column(Text, nullable=False, default="")
    cf_intercept_ip = Column(Text, nullable=False, default="")
    cf_analytics = Column(Text, nullable=False, default="")
    cf_add_meta = Column(Text, nullable=False, default="")
    cf_member_skin = Column(String(50), nullable=False, default="")
    cf_use_homepage = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_req_homepage = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_tel = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_req_tel = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_hp = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_req_hp = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_addr = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_req_addr = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_signature = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_req_signature = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_profile = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_req_profile = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_register_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_register_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_icon_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_use_recommend = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_recommend_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_leave_day = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_search_part = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_use = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_wr_super_admin = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_wr_group_admin = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_wr_board_admin = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_wr_write = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_wr_comment_all = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_mb_super_admin = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_mb_member = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_email_po_super_admin = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_prohibit_id = Column(Text, nullable=False, default="")
    cf_prohibit_email = Column(Text, nullable=False, default="")
    cf_new_del = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_memo_del = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_visit_del = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_popular_del = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_optimize_date = Column(String(10), nullable=False, default="")
    cf_use_member_icon = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_member_icon_size = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_member_icon_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_member_icon_height = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_member_img_size = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_member_img_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_member_img_height = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_login_minutes = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_image_extension = Column(String(255), nullable=False, default="")
    cf_flash_extension = Column(String(255), nullable=False, default="")
    cf_movie_extension = Column(String(255), nullable=False, default="")
    cf_formmail_is_member = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_page_rows = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_mobile_page_rows = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_visit = Column(String(255), nullable=False, default="")
    cf_max_po_id = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_stipulation = Column(Text, nullable=False, default="")
    cf_privacy = Column(Text, nullable=False, default="")
    cf_open_modify = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_memo_send_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_mobile_new_skin = Column(String(50), nullable=False, default="")
    cf_mobile_search_skin = Column(String(50), nullable=False, default="")
    cf_mobile_connect_skin = Column(String(50), nullable=False, default="")
    cf_mobile_faq_skin = Column(String(50), nullable=False, default="")
    cf_mobile_member_skin = Column(String(50), nullable=False, default="")
    cf_captcha_mp3 = Column(String(255), nullable=False, default="")
    cf_editor = Column(String(50), nullable=False, default="")
    cf_cert_use = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_cert_find = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_cert_ipin = Column(String(255), nullable=False, default="")
    cf_cert_hp = Column(String(255), nullable=False, default="")
    cf_cert_simple = Column(String(255), nullable=False, default="")
    cf_cert_kg_cd = Column(String(255), nullable=False, default="")
    cf_cert_kg_mid = Column(String(255), nullable=False, default="")
    cf_cert_kcb_cd = Column(String(255), nullable=False, default="")
    cf_cert_kcp_cd = Column(String(255), nullable=False, default="")
    cf_lg_mid = Column(String(100), nullable=False, default="")
    cf_lg_mert_key = Column(String(100), nullable=False, default="")
    cf_cert_limit = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_cert_req = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_sms_use = Column(String(255), nullable=False, default="")
    cf_sms_type = Column(String(10), nullable=False, default="")
    cf_icode_id = Column(String(255), nullable=False, default="")
    cf_icode_pw = Column(String(255), nullable=False, default="")
    cf_icode_server_ip = Column(String(50), nullable=False, default="")
    cf_icode_server_port = Column(String(50), nullable=False, default="")
    cf_icode_token_key = Column(String(100), nullable=False, default="")
    cf_googl_shorturl_apikey = Column(String(50), nullable=False, default="")
    cf_social_login_use = Column(Integer, nullable=False, default=0, server_default=text("0"))
    cf_social_servicelist = Column(String(255), nullable=False, default="")
    cf_payco_clientid = Column(String(100), nullable=False, default="")
    cf_payco_secret = Column(String(100), nullable=False, default="")
    cf_facebook_appid = Column(String(100), nullable=False, default="")
    cf_facebook_secret = Column(String(100), nullable=False, default="")
    cf_twitter_key = Column(String(100), nullable=False, default="")
    cf_twitter_secret = Column(String(100), nullable=False, default="")
    cf_google_clientid = Column(String(100), nullable=False, default="")
    cf_google_secret = Column(String(100), nullable=False, default="")
    cf_naver_clientid = Column(String(100), nullable=False, default="")
    cf_naver_secret = Column(String(100), nullable=False, default="")
    cf_kakao_rest_key = Column(String(100), nullable=False, default="")
    cf_kakao_client_secret = Column(String(100), nullable=False, default="")
    cf_kakao_js_apikey = Column(String(100), nullable=False, default="")
    cf_captcha = Column(String(100), nullable=False, default="")
    cf_recaptcha_site_key = Column(String(100), nullable=False, default="")
    cf_recaptcha_secret_key = Column(String(100), nullable=False, default="")
    cf_1_subj = Column(String(255), nullable=False, default="")
    cf_2_subj = Column(String(255), nullable=False, default="")
    cf_3_subj = Column(String(255), nullable=False, default="")
    cf_4_subj = Column(String(255), nullable=False, default="")
    cf_5_subj = Column(String(255), nullable=False, default="")
    cf_6_subj = Column(String(255), nullable=False, default="")
    cf_7_subj = Column(String(255), nullable=False, default="")
    cf_8_subj = Column(String(255), nullable=False, default="")
    cf_9_subj = Column(String(255), nullable=False, default="")
    cf_10_subj = Column(String(255), nullable=False, default="")
    cf_1 = Column(String(255), nullable=False, default="")
    cf_2 = Column(String(255), nullable=False, default="")
    cf_3 = Column(String(255), nullable=False, default="")
    cf_4 = Column(String(255), nullable=False, default="")
    cf_5 = Column(String(255), nullable=False, default="")
    cf_6 = Column(String(255), nullable=False, default="")
    cf_7 = Column(String(255), nullable=False, default="")
    cf_8 = Column(String(255), nullable=False, default="")
    cf_9 = Column(String(255), nullable=False, default="")
    cf_10 = Column(String(255), nullable=False, default="")


class Member(Base):
    """
    회원 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "member"

    mb_no = Column(Integer, primary_key=True)
    mb_id = Column(String(20), unique=True, nullable=False, default="")
    mb_password = Column(String(255), nullable=False, default="")
    mb_name = Column(String(255), nullable=False, default="")
    mb_nick = Column(String(255), nullable=False, default="")
    mb_nick_date = Column(Date, nullable=False, default=date(1, 1, 1))
    mb_email = Column(String(255), nullable=False, default="")
    mb_homepage = Column(String(255), nullable=False, default="")
    mb_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_sex = Column(String(1), nullable=False, default="")
    mb_birth = Column(String(255), nullable=False, default="")
    mb_tel = Column(String(255), nullable=False, default="")
    mb_hp = Column(String(255), nullable=False, default="")
    mb_certify = Column(String(20), nullable=False, default="")
    mb_adult = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_dupinfo = Column(String(255), nullable=False, default="")
    mb_zip1 = Column(String(3), nullable=False, default="")
    mb_zip2 = Column(String(3), nullable=False, default="")
    mb_addr1 = Column(String(255), nullable=False, default="")
    mb_addr2 = Column(String(255), nullable=False, default="")
    mb_addr3 = Column(String(255), nullable=False, default="")
    mb_addr_jibeon = Column(String(255), nullable=False, default="")
    mb_signature = Column(Text, nullable=False, default="")
    mb_recommend = Column(String(255), nullable=False, default="")
    mb_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_today_login = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    mb_login_ip = Column(String(255), nullable=False, default="")
    mb_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    mb_ip = Column(String(255), nullable=False, default="")
    mb_leave_date = Column(String(8), nullable=False, default="")
    mb_intercept_date = Column(String(8), nullable=False, default="")
    mb_email_certify = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    mb_email_certify2 = Column(String(255), nullable=False, default="")
    mb_memo = Column(Text, nullable=False, default="")
    mb_lost_certify = Column(String(255), nullable=False, default="")
    mb_mailling = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_sms = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_open = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_open_date = Column(Date, nullable=False, default=datetime(1, 1, 1))
    mb_profile = Column(Text, nullable=False, default="")
    mb_memo_call = Column(String(255), nullable=False, default="")
    mb_memo_cnt = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_scrap_cnt = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_1 = Column(String(255), nullable=False, default="")
    mb_2 = Column(String(255), nullable=False, default="")
    mb_3 = Column(String(255), nullable=False, default="")
    mb_4 = Column(String(255), nullable=False, default="")
    mb_5 = Column(String(255), nullable=False, default="")
    mb_6 = Column(String(255), nullable=False, default="")
    mb_7 = Column(String(255), nullable=False, default="")
    mb_8 = Column(String(255), nullable=False, default="")
    mb_9 = Column(String(255), nullable=False, default="")
    mb_10 = Column(String(255), nullable=False, default="")

    auths: Mapped[List["Auth"]] = relationship("Auth", back_populates="member")
    groups: Mapped[List["GroupMember"]] = relationship(back_populates="member")
    points: Mapped[List["Point"]] = relationship("Point", back_populates="member")
    socials: Mapped[List["MemberSocialProfiles"]] = relationship("MemberSocialProfiles", back_populates="member")
    recv_memos: Mapped[List["Memo"]] = relationship("Memo", back_populates="recv_member", foreign_keys="Memo.me_recv_mb_id")
    send_memos: Mapped[List["Memo"]] = relationship("Memo", back_populates="send_member", foreign_keys="Memo.me_send_mb_id")
    scraps: DynamicMapped["Scrap"] = relationship("Scrap", back_populates="member", lazy="dynamic")


class Board(Base):
    """
    게시판 설정 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "board"

    bo_table = Column(String(20), primary_key=True, nullable=False)
    gr_id = Column(String(255), ForeignKey(DB_TABLE_PREFIX + "group.gr_id"), nullable=False, default="")
    bo_subject = Column(String(255), nullable=False, default="")
    bo_mobile_subject = Column(String(255), nullable=False, default="")
    bo_device = Column(Enum("both", "pc", "mobile", name="bo_device"), nullable=False, default="both")
    bo_admin = Column(String(255), nullable=False, default="")
    bo_list_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_read_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_write_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_reply_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_comment_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_upload_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_download_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_html_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_link_level = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_count_delete = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_count_modify = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_read_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_write_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_comment_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_download_point = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_category = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_category_list = Column(Text, nullable=False, default="")
    bo_use_sideview = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_file_content = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_secret = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_dhtml_editor = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_select_editor = Column(String(50), nullable=False, default="")
    bo_use_rss_view = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_good = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_nogood = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_name = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_signature = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_ip_view = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_list_view = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_list_file = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_list_content = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_table_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_subject_len = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_mobile_subject_len = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_page_rows = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_mobile_page_rows = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_new = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_hot = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_image_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_skin = Column(String(255), nullable=False, default="")
    bo_mobile_skin = Column(String(255), nullable=False, default="")
    bo_include_head = Column(String(255), nullable=False, default="")
    bo_include_tail = Column(String(255), nullable=False, default="")
    bo_content_head = Column(Text, nullable=False, default="")
    bo_mobile_content_head = Column(Text, nullable=False, default="")
    bo_content_tail = Column(Text, nullable=False, default="")
    bo_mobile_content_tail = Column(Text, nullable=False, default="")
    bo_insert_content = Column(Text, nullable=False, default="")
    bo_gallery_cols = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_gallery_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_gallery_height = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_mobile_gallery_width = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_mobile_gallery_height = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_upload_size = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_reply_order = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_search = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_order = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_count_write = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_count_comment = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_write_min = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_write_max = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_comment_min = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_comment_max = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_notice = Column(Text, nullable=False, default="")
    bo_upload_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_email = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_cert = Column(Enum("", "cert", "adult", "hp-cert", "hp-adult", name="bo_use_cert"), nullable=False, default="")
    bo_use_sns = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_use_captcha = Column(Integer, nullable=False, default=0, server_default=text("0"))
    bo_sort_field = Column(String(255), nullable=False, default="")
    bo_1_subj = Column(String(255), nullable=False, default="")
    bo_2_subj = Column(String(255), nullable=False, default="")
    bo_3_subj = Column(String(255), nullable=False, default="")
    bo_4_subj = Column(String(255), nullable=False, default="")
    bo_5_subj = Column(String(255), nullable=False, default="")
    bo_6_subj = Column(String(255), nullable=False, default="")
    bo_7_subj = Column(String(255), nullable=False, default="")
    bo_8_subj = Column(String(255), nullable=False, default="")
    bo_9_subj = Column(String(255), nullable=False, default="")
    bo_10_subj = Column(String(255), nullable=False, default="")
    bo_1 = Column(String(255), nullable=False, default="")
    bo_2 = Column(String(255), nullable=False, default="")
    bo_3 = Column(String(255), nullable=False, default="")
    bo_4 = Column(String(255), nullable=False, default="")
    bo_5 = Column(String(255), nullable=False, default="")
    bo_6 = Column(String(255), nullable=False, default="")
    bo_7 = Column(String(255), nullable=False, default="")
    bo_8 = Column(String(255), nullable=False, default="")
    bo_9 = Column(String(255), nullable=False, default="")
    bo_10 = Column(String(255), nullable=False, default="")

    group: Mapped["Group"] = relationship("Group", back_populates="boards")
    board_news: Mapped[List["BoardNew"]] = relationship("BoardNew", back_populates="board")
    scraps: Mapped[List["Scrap"]] = relationship("Scrap", back_populates="board")


class WriteBaseModel(Base):
    """
    게시글, 댓글 테이블
    wr_is_comment : 0=글, 1=댓글
    """

    # __tablename__ = DB_TABLE_PREFIX + 'write'
    __abstract__ = True

    wr_id = Column(Integer, primary_key=True, nullable=False)
    wr_num = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_reply = Column(String(10), nullable=False, default="")
    wr_parent = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_is_comment = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_comment = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_comment_reply = Column(String(5), nullable=False, default="")
    ca_name = Column(String(255), nullable=False, default="")
    # wr_option = Column(Enum("html1", "html2", "secret", "mail", name="wr_option"), nullable=False, default="html1")
    wr_option = Column(String(40), nullable=False, default="html1")
    wr_subject = Column(String(255), nullable=False, default="")
    wr_content = Column(Text, nullable=False, default="")
    wr_seo_title = Column(String(255), nullable=False, default="")
    wr_link1 = Column(Text, nullable=False, default="")
    wr_link2 = Column(Text, nullable=False, default="")
    wr_link1_hit = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_link2_hit = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_hit = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_good = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_nogood = Column(Integer, nullable=False, default=0, server_default=text("0"))
    mb_id = Column(String(20), nullable=False, default="")
    wr_password = Column(String(255), nullable=False, default="")
    wr_name = Column(String(255), nullable=False, default="")
    wr_email = Column(String(255), nullable=False, default="")
    wr_homepage = Column(String(255), nullable=False, default="")
    wr_datetime = Column(DateTime, nullable=False, default="")
    wr_file = Column(Integer, nullable=False, default=0, server_default=text("0"))
    wr_last = Column(String(30), nullable=False, default="")
    wr_ip = Column(String(255), nullable=False, default="")
    wr_facebook_user = Column(String(255), nullable=False, default="")
    wr_twitter_user = Column(String(255), nullable=False, default="")
    wr_1 = Column(String(255), nullable=False, default="")
    wr_2 = Column(String(255), nullable=False, default="")
    wr_3 = Column(String(255), nullable=False, default="")
    wr_4 = Column(String(255), nullable=False, default="")
    wr_5 = Column(String(255), nullable=False, default="")
    wr_6 = Column(String(255), nullable=False, default="")
    wr_7 = Column(String(255), nullable=False, default="")
    wr_8 = Column(String(255), nullable=False, default="")
    wr_9 = Column(String(255), nullable=False, default="")
    wr_10 = Column(String(255), nullable=False, default="")
    # 종속관계
    # comments = relationship("Comment", backref="write")

    # __table_args__['extend_existing'] = False

    # try:
    #     __table_args__ = (
    #         Index('idx_wr_num_reply', 'wr_num', 'wr_reply'),
    #         Index('idex_wr_is_comment', 'wr_is_comment'),
    #          {"extend_existing": True}
    #     )
    # except ArgumentError:
    #     # Index already exists
    #     pass
    # # except InvalidRequestError:
    # #     print("InvalidRequestError")


# Create a composite index for wr_id and bo_table
# Index('idx_write_bo_table_wr_id', WriteBaseModel.bo_table, WriteBaseModel.wr_id)


class Group(Base):
    """
    게시판 그룹 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "group"

    gr_id = Column(String(10), primary_key=True, nullable=False)
    gr_subject = Column(String(255), nullable=False, default="")
    gr_device = Column(Enum("both", "pc", "mobile", name="gr_device"), nullable=False, default="both")
    gr_admin = Column(String(255), nullable=False, default="")
    gr_use_access = Column(Integer, nullable=False, default=0, server_default=text("0"))
    gr_order = Column(Integer, nullable=False, default=0, server_default=text("0"))
    gr_1_subj = Column(String(255), nullable=False, default="")
    gr_2_subj = Column(String(255), nullable=False, default="")
    gr_3_subj = Column(String(255), nullable=False, default="")
    gr_4_subj = Column(String(255), nullable=False, default="")
    gr_5_subj = Column(String(255), nullable=False, default="")
    gr_6_subj = Column(String(255), nullable=False, default="")
    gr_7_subj = Column(String(255), nullable=False, default="")
    gr_8_subj = Column(String(255), nullable=False, default="")
    gr_9_subj = Column(String(255), nullable=False, default="")
    gr_10_subj = Column(String(255), nullable=False, default="")
    gr_1 = Column(String(255), nullable=False, default="")
    gr_2 = Column(String(255), nullable=False, default="")
    gr_3 = Column(String(255), nullable=False, default="")
    gr_4 = Column(String(255), nullable=False, default="")
    gr_5 = Column(String(255), nullable=False, default="")
    gr_6 = Column(String(255), nullable=False, default="")
    gr_7 = Column(String(255), nullable=False, default="")
    gr_8 = Column(String(255), nullable=False, default="")
    gr_9 = Column(String(255), nullable=False, default="")
    gr_10 = Column(String(255), nullable=False, default="")
    # 종속관계

    boards: Mapped[List["Board"]] = relationship(back_populates="group")
    members: Mapped[List["GroupMember"]] = relationship(back_populates="group")


class GroupMember(Base):
    '''
    그룹회원 테이블
    '''    
    __tablename__ = DB_TABLE_PREFIX + "group_member"

    gm_id = Column(Integer, primary_key=True, autoincrement=True)
    gr_id = Column(String(10), ForeignKey(DB_TABLE_PREFIX + "group.gr_id"), nullable=False, default="")
    mb_id = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "member.mb_id"), nullable=False, default="")
    gm_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))

    gr_id_index = Index("gr_id", gr_id)
    mb_id_index = Index("mb_id", mb_id)

    member: Mapped["Member"] = relationship(back_populates="groups")
    group: Mapped["Group"] = relationship(back_populates="members")


class Content(Base):
    """
    내용 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "content"

    co_id = Column(String(20), primary_key=True, nullable=False, default="")
    co_html = Column(Integer, nullable=False, default=0)
    co_subject = Column(String(255), nullable=False, default="")
    co_content = Column(Text, nullable=False, default="")
    co_seo_title = Column(String(255), nullable=False, default="")
    co_mobile_content = Column(Text, nullable=False, default="")
    co_skin = Column(String(255), nullable=False, default="")
    co_mobile_skin = Column(String(255), nullable=False, default="")
    co_tag_filter_use = Column(Integer, nullable=False, default=0)
    co_hit = Column(Integer, nullable=False, default=0)
    co_include_head = Column(String(255), nullable=False, default="")
    co_include_tail = Column(String(255), nullable=False, default="")


class FaqMaster(Base):
    __tablename__ = DB_TABLE_PREFIX + "faq_master"

    fm_id = Column(Integer, primary_key=True, autoincrement=True)
    fm_subject = Column(String(255), nullable=False, default="")
    fm_head_html = Column(Text, nullable=False, default="")
    fm_tail_html = Column(Text, nullable=False, default="")
    fm_mobile_head_html = Column(Text, nullable=False, default="")
    fm_mobile_tail_html = Column(Text, nullable=False, default="")
    fm_order = Column(Integer, nullable=False, default=0)

    # 연관관계
    faqs = relationship(
        "Faq", back_populates="faq_master", cascade="all, delete-orphan"
    )


class Faq(Base):
    __tablename__ = DB_TABLE_PREFIX + "faq"

    fa_id = Column(Integer, primary_key=True, autoincrement=True)
    fm_id = Column(
        Integer,
        ForeignKey(DB_TABLE_PREFIX + "faq_master.fm_id"),
        nullable=False,
        default=0,
    )
    fa_subject = Column(Text, nullable=False, default="")
    fa_content = Column(Text, nullable=False, default="")
    fa_order = Column(Integer, nullable=False, default=0)

    # 연관관계
    faq_master = relationship("FaqMaster", back_populates="faqs", foreign_keys=[fm_id])


class Visit(Base):
    __tablename__ = DB_TABLE_PREFIX + "visit"

    vi_id = Column(Integer, primary_key=True, autoincrement=True)
    vi_ip = Column(String(100), nullable=False, default="")
    vi_date = Column(Date, nullable=False, default="")
    vi_time = Column(Time, nullable=False, default="")
    vi_referer = Column(Text, nullable=False, default="")
    vi_agent = Column(String(200), nullable=False, default="")
    vi_browser = Column(String(255), nullable=False, default="")
    vi_os = Column(String(255), nullable=False, default="")
    vi_device = Column(String(255), nullable=False, default="")


class VisitSum(Base):
    __tablename__ = DB_TABLE_PREFIX + "visit_sum"

    vs_date = Column(Date, primary_key=True, nullable=False, default="")
    vs_count = Column(Integer, nullable=False, default=0)


class QaConfig(Base):
    """Q&A 설정 테이블"""

    __tablename__ = DB_TABLE_PREFIX + "qa_config"

    id = Column(Integer, primary_key=True)
    qa_title = Column(String(255), nullable=False, default="")
    qa_category = Column(String(255), nullable=False, default="")
    qa_skin = Column(String(255), nullable=False, default="")
    qa_mobile_skin = Column(String(255), nullable=False, default="")
    qa_use_email = Column(Integer, nullable=False, default=0)
    qa_req_email = Column(Integer, nullable=False, default=0)
    qa_use_hp = Column(Integer, nullable=False, default=0)
    qa_req_hp = Column(Integer, nullable=False, default=0)
    qa_use_sms = Column(Integer, nullable=False, default=0)
    qa_send_number = Column(String(255), nullable=False, default="0")
    qa_admin_hp = Column(String(255), nullable=False, default="")
    qa_admin_email = Column(String(255), nullable=False, default="")
    qa_use_editor = Column(Integer, nullable=False, default=0)
    qa_subject_len = Column(Integer, nullable=False, default=0)
    qa_mobile_subject_len = Column(Integer, nullable=False, default=0)
    qa_page_rows = Column(Integer, nullable=False, default=0)
    qa_mobile_page_rows = Column(Integer, nullable=False, default=0)
    qa_image_width = Column(Integer, nullable=False, default=0)
    qa_upload_size = Column(Integer, nullable=False, default=0)
    qa_insert_content = Column(Text, nullable=True)
    qa_include_head = Column(String(255), nullable=True)
    qa_include_tail = Column(String(255), nullable=True)
    qa_content_head = Column(Text, nullable=True)
    qa_content_tail = Column(Text, nullable=True)
    qa_mobile_content_head = Column(Text, nullable=True)
    qa_mobile_content_tail = Column(Text, nullable=True)
    qa_1_subj = Column(String(255), nullable=True)
    qa_2_subj = Column(String(255), nullable=True)
    qa_3_subj = Column(String(255), nullable=True)
    qa_4_subj = Column(String(255), nullable=True)
    qa_5_subj = Column(String(255), nullable=True)
    qa_1 = Column(String(255), nullable=True)
    qa_2 = Column(String(255), nullable=True)
    qa_3 = Column(String(255), nullable=True)
    qa_4 = Column(String(255), nullable=True)
    qa_5 = Column(String(255), nullable=True)


class QaContent(Base):
    """Q&A 데이터 테이블"""

    __tablename__ = DB_TABLE_PREFIX + "qa_content"

    qa_id = Column(Integer, primary_key=True, autoincrement=True)
    qa_num = Column(Integer, nullable=False, default=0)
    qa_parent = Column(Integer, nullable=False, default=0)
    qa_related = Column(Integer, nullable=False, default=0)
    mb_id = Column(
        String(20),
        ForeignKey(DB_TABLE_PREFIX + "member.mb_id"),
        nullable=False,
        default="",
    )
    qa_name = Column(String(255), nullable=False, default="")
    qa_email = Column(String(255), nullable=False, default="")
    qa_hp = Column(String(255), nullable=False, default="")
    qa_type = Column(Integer, nullable=False, default=0)
    qa_category = Column(String(255), nullable=False, default="")
    qa_email_recv = Column(Integer, nullable=False, default=0)
    qa_sms_recv = Column(Integer, nullable=False, default=0)
    qa_html = Column(Integer, nullable=False, default=0)
    qa_subject = Column(String(255), nullable=False, default="")
    qa_content = Column(Text, nullable=False)
    qa_status = Column(Integer, nullable=False, default=0)
    qa_file1 = Column(String(255), nullable=False, default="")
    qa_source1 = Column(String(255), nullable=False, default="")
    qa_file2 = Column(String(255), nullable=False, default="")
    qa_source2 = Column(String(255), nullable=False, default="")
    qa_ip = Column(String(255), nullable=False, default="")
    qa_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    qa_1 = Column(String(255), nullable=False, default="")
    qa_2 = Column(String(255), nullable=False, default="")
    qa_3 = Column(String(255), nullable=False, default="")
    qa_4 = Column(String(255), nullable=False, default="")
    qa_5 = Column(String(255), nullable=False, default="")

    # Index 추가
    qa_num_parent_index = Index("qa_num_parent", qa_num, qa_parent)


class Menu(Base):
    __tablename__ = DB_TABLE_PREFIX + "menu"

    me_id = Column(Integer, primary_key=True, autoincrement=True)
    me_code = Column(String(255), nullable=False, default="")
    me_name = Column(String(255), nullable=False, default="")
    me_link = Column(String(255), nullable=False, default="")
    me_target = Column(String(255), nullable=False, default="")
    me_order = Column(Integer, nullable=False, default=0)
    me_use = Column(Integer, nullable=False, default=0)
    me_mobile_use = Column(Integer, nullable=False, default=0)


class Point(Base):
    """
    포인트 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "point"

    po_id = Column(Integer, primary_key=True, autoincrement=True)
    mb_id = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "member.mb_id"), nullable=False, default="")
    po_datetime = Column(DateTime, nullable=False, default=datetime.now())
    po_content = Column(String(255), nullable=False, default="")
    po_point = Column(Integer, nullable=False, default=0)
    po_use_point = Column(Integer, nullable=False, default=0)
    po_expired = Column(Integer, nullable=False, default=0)
    po_expire_date = Column(Date, nullable=False, default=datetime.now())
    po_mb_point = Column(Integer, nullable=False, default=0)
    po_rel_table = Column(String(20), nullable=False, default="")
    po_rel_id = Column(String(20), nullable=False, default="")
    po_rel_action = Column(String(100), nullable=False, default="")

    member: Mapped["Member"] = relationship("Member", back_populates="points", lazy="joined")


class Memo(Base):
    """
    쪽지 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "memo"

    me_id = Column(Integer, primary_key=True, autoincrement=True)
    me_recv_mb_id = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "member.mb_id"), nullable=False, default="")
    me_send_mb_id = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "member.mb_id"), nullable=False, default="")
    me_send_datetime = Column(DateTime, nullable=False, default=datetime.now())
    me_read_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    me_memo = Column(Text, nullable=False)
    me_send_id = Column(Integer, nullable=False, default=0)
    me_type = Column(Enum("send", "recv", name="me_type"), nullable=False, default="recv")
    me_send_ip = Column(String(100), nullable=False, default="")

    # 종속관계
    recv_member: Mapped["Member"] = relationship("Member", back_populates="recv_memos", foreign_keys=[me_recv_mb_id])
    send_member: Mapped["Member"] = relationship("Member", back_populates="send_memos", foreign_keys=[me_send_mb_id])


class Popular(Base):
    """
    인기검색어 테이블
    """

    __tablename__ = DB_TABLE_PREFIX + "popular"

    pp_id = Column(Integer, primary_key=True, autoincrement=True)
    pp_word = Column(String(50), nullable=False, default="")
    pp_date = Column(Date, nullable=False)
    pp_ip = Column(String(50), nullable=False, default="")

    # Index 추가
    index1 = Index("index1", pp_date, pp_word, pp_ip, unique=True)


class Auth(Base):
    __tablename__ = DB_TABLE_PREFIX + "auth"

    mb_id = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "member.mb_id"), primary_key=True, nullable=False, default="")
    au_menu = Column(String(20), primary_key=True, nullable=False, default="")
    au_auth = Column(String(255), nullable=False, default="")

    member: Mapped["Member"] = relationship("Member", back_populates="auths")



class Poll(Base):
    __tablename__ = DB_TABLE_PREFIX + "poll"

    po_id = Column(Integer, primary_key=True, autoincrement=True)
    po_subject = Column(String(255), nullable=False, default='')
    po_poll1 = Column(String(255), nullable=False, default='')
    po_poll2 = Column(String(255), nullable=False, default='')
    po_poll3 = Column(String(255), nullable=False, default='')
    po_poll4 = Column(String(255), nullable=False, default='')
    po_poll5 = Column(String(255), nullable=False, default='')
    po_poll6 = Column(String(255), nullable=False, default='')
    po_poll7 = Column(String(255), nullable=False, default='')
    po_poll8 = Column(String(255), nullable=False, default='')
    po_poll9 = Column(String(255), nullable=False, default='')
    po_cnt1 = Column(Integer, nullable=False, default=0)
    po_cnt2 = Column(Integer, nullable=False, default=0)
    po_cnt3 = Column(Integer, nullable=False, default=0)
    po_cnt4 = Column(Integer, nullable=False, default=0)
    po_cnt5 = Column(Integer, nullable=False, default=0)
    po_cnt6 = Column(Integer, nullable=False, default=0)
    po_cnt7 = Column(Integer, nullable=False, default=0)
    po_cnt8 = Column(Integer, nullable=False, default=0)
    po_cnt9 = Column(Integer, nullable=False, default=0)
    po_etc = Column(String(255), nullable=False, default='')
    po_level = Column(Integer, nullable=False, default=0)
    po_point = Column(Integer, nullable=False, default=0)
    po_date = Column(Date, nullable=False, default=datetime.now())
    po_ips = Column(Text, nullable=False, default='')
    mb_ids = Column(Text, nullable=False, default='')
    po_use = Column(Integer, nullable=False, default=1)

    etcs: Mapped[List["PollEtc"]] = relationship("PollEtc", back_populates="poll")


class PollEtc(Base):
    __tablename__ = DB_TABLE_PREFIX + "poll_etc"

    pc_id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey(DB_TABLE_PREFIX + "poll.po_id"), nullable=False, default=0)
    mb_id = Column(String(20), nullable=False, default='')
    pc_name = Column(String(255), nullable=False, default='')
    pc_idea = Column(String(255), nullable=False, default='')
    pc_datetime = Column(DateTime, nullable=False, default=datetime.now())

    poll: Mapped["Poll"] = relationship("Poll", back_populates="etcs")

class AutoSave(Base):
    __tablename__ = DB_TABLE_PREFIX + "autosave"

    as_id = Column(Integer, primary_key=True, autoincrement=True)
    mb_id = Column(String(20), nullable=False, default="")
    as_uid = Column(BIGINT, nullable=False, unique=True, default=0)
    as_subject = Column(String(255), nullable=False, default="")
    as_content = Column(Text, nullable=False, default="")
    as_datetime = Column(DateTime, nullable=False, default=datetime.now())


class UniqId(Base):
    __tablename__ = DB_TABLE_PREFIX + "uniqid"

    uq_id = Column(BIGINT, primary_key=True)
    uq_ip = Column(String(255), nullable=False, default="")


class NewWin(Base):
    __tablename__ = DB_TABLE_PREFIX + 'new_win'

    nw_id = Column(Integer, primary_key=True, autoincrement=True)
    nw_division = Column(String(10), nullable=False, default='both')
    nw_device = Column(String(10), nullable=False, default='both')
    nw_begin_time = Column(DateTime, nullable=False, default=datetime.now())
    nw_end_time = Column(DateTime, nullable=False, default=datetime.now())
    nw_disable_hours = Column(Integer, nullable=False, default=0)
    nw_left = Column(Integer, nullable=False, default=0)
    nw_top = Column(Integer, nullable=False, default=0)
    nw_height = Column(Integer, nullable=False, default=0)
    nw_width = Column(Integer, nullable=False, default=0)
    nw_subject = Column(Text, nullable=False)
    nw_content = Column(Text, nullable=False)
    nw_content_html = Column(Integer, nullable=False, default=0)
    
    
# 회원메일발송 테이블
class Mail(Base):
    __tablename__ = DB_TABLE_PREFIX + 'mail'

    ma_id = Column(Integer, primary_key=True, autoincrement=True)
    ma_subject = Column(String(255), nullable=False, default='')
    ma_content = Column(Text, nullable=False, default='')
    ma_time = Column(DateTime, nullable=False, default=datetime.now())
    ma_ip = Column(String(255), nullable=False, default='')
    ma_last_option = Column(Text, nullable=False, default='')
    

class BoardNew(Base):
    """
    최신 게시물 테이블
    """
    __tablename__ = DB_TABLE_PREFIX + 'board_new'
    
    bn_id = Column(Integer, primary_key=True, autoincrement=True)
    bo_table = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "board.bo_table"), nullable=False, default='')
    wr_id = Column(Integer, nullable=False, default=0)
    wr_parent = Column(Integer, nullable=False, default=0)
    bn_datetime = Column(DateTime, nullable=False, default=datetime.now())
    mb_id = Column(String(20), nullable=False, default='')

    board: Mapped["Board"] = relationship("Board", back_populates="board_news")


class Scrap(Base):
    """
    게시글 스크랩 테이블
    """
    __tablename__ = DB_TABLE_PREFIX + 'scrap'

    ms_id = Column(Integer, primary_key=True, autoincrement=True)
    mb_id = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "member.mb_id"), nullable=False, default='')
    bo_table = Column(String(20), ForeignKey(DB_TABLE_PREFIX + "board.bo_table"), nullable=False, default='')
    wr_id = Column(Integer, nullable=False, default=0)
    ms_datetime = Column(DateTime, nullable=False, default=datetime.now())

    board: Mapped["Board"] = relationship("Board", back_populates="scraps")
    member: Mapped["Member"] = relationship("Member", back_populates="scraps")


class BoardGood(Base):
    """
    게시글 좋아요/싫어요 테이블
    """
    __tablename__ = DB_TABLE_PREFIX + 'board_good'
    __table_args__ = (UniqueConstraint('bo_table', 'wr_id', 'mb_id', name='fkey1'), )

    bg_id = Column(Integer, primary_key=True, autoincrement=True)
    bo_table = Column(String(20), nullable=False, default='')
    wr_id = Column(Integer, nullable=False, default=0)
    mb_id = Column(String(20), nullable=False, default='')
    bg_flag = Column(String(255), nullable=False, default='')
    bg_datetime = Column(DateTime, nullable=False, default=datetime.now())


class BoardFile(Base):
    """
    게시글 파일 테이블
    """
    __tablename__ = DB_TABLE_PREFIX + 'board_file'

    bo_table = Column(String(20), primary_key=True, nullable=False, default='')
    wr_id = Column(Integer, primary_key=True, nullable=False, default=0)
    bf_no = Column(Integer, primary_key=True, nullable=False, default=0)
    bf_source = Column(String(255), nullable=False, default='')
    bf_file = Column(String(255), nullable=False, default='')
    bf_download = Column(Integer, nullable=False, default=0)
    bf_content = Column(Text, nullable=False)
    bf_fileurl = Column(String(255), nullable=False, default='')
    bf_thumburl = Column(String(255), nullable=False, default='')
    bf_storage = Column(String(50), nullable=False, default='')
    bf_filesize = Column(Integer, nullable=False, default=0)
    bf_width = Column(Integer, nullable=False, default=0)
    bf_height = Column(Integer, nullable=False, default=0)
    bf_type = Column(Integer, nullable=False, default=0)
    bf_datetime = Column(DateTime, nullable=False, default=datetime.now())    
    

class MemberSocialProfiles(Base):
    __tablename__ = DB_TABLE_PREFIX + "member_social_profiles"

    mp_no = Column(Integer, primary_key=True, autoincrement=True)
    mb_id = Column(String(255), ForeignKey(DB_TABLE_PREFIX + "member.mb_id"), nullable=False, default="")
    provider = Column(String(50), nullable=False, default="")
    object_sha = Column(String(45), nullable=False, default="")
    identifier = Column(String(255), nullable=False, default="")
    profileurl = Column(String(255), nullable=False, default="")
    photourl = Column(String(255), nullable=False, default="")
    displayname = Column(String(255), nullable=False, default="")
    description = Column(String(255), nullable=False, default="")
    mp_register_day = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    mp_latest_day = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))

    member: Mapped["Member"] = relationship("Member", back_populates="socials")


class Login(Base):
    """현재 로그인 및 접속자 테이블"""
    __tablename__ = DB_TABLE_PREFIX + "login"

    lo_id = Column(Integer, primary_key=True, autoincrement=True)  # 새로 추가된 기본키
    lo_ip = Column(String(100), nullable=False, default='')
    mb_id = Column(String(20), nullable=False, default='')
    lo_datetime = Column(DateTime, nullable=False, default=datetime(1, 1, 1, 0, 0, 0))
    lo_location = Column(Text, nullable=False)
    lo_url = Column(Text, nullable=False)