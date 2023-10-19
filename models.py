from sqlalchemy import create_engine, Column, Integer, String, Text, Enum, ForeignKey, Index, text, DateTime, Date, Time
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import ArgumentError, InvalidRequestError
from datetime import datetime, date

Base = declarative_base()

class Config(Base):
    '''
    환경설정 테이블
    '''
    __tablename__ = 'g6_config'
    
    cf_id = Column(Integer, primary_key=True)  
    cf_title = Column(String(255), nullable=False, default='')
    cf_theme = Column(String(100), nullable=False, default='')
    cf_admin = Column(String(100), nullable=False, default='')
    cf_admin_email = Column(String(100), nullable=False, default='')
    cf_admin_email_name = Column(String(100), nullable=False, default='')
    cf_add_script = Column(Text, nullable=False, default='')
    cf_use_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_point_term = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_copy_log = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_email_certify = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_login_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_cut_name = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_nick_modify = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_new_skin = Column(String(50), nullable=False, default='')
    cf_new_rows = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_search_skin = Column(String(50), nullable=False, default='')
    cf_connect_skin = Column(String(50), nullable=False, default='')
    cf_faq_skin = Column(String(50), nullable=False, default='')
    cf_read_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_write_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_comment_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_download_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_write_pages = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_mobile_pages = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_link_target = Column(String(50), nullable=False, default='')
    cf_bbs_rewrite = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_delay_sec = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_filter = Column(Text, nullable=False, default='')
    cf_possible_ip = Column(Text, nullable=False, default='')
    cf_intercept_ip = Column(Text, nullable=False, default='')
    cf_analytics = Column(Text, nullable=False, default='')
    cf_add_meta = Column(Text, nullable=False, default='')
    cf_syndi_token = Column(String(255), nullable=False, default='')
    cf_syndi_except = Column(Text, nullable=False, default='')
    cf_member_skin = Column(String(50), nullable=False, default='')
    cf_use_homepage = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_req_homepage = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_tel = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_req_tel = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_hp = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_req_hp = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_addr = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_req_addr = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_signature = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_req_signature = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_profile = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_req_profile = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_register_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_register_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_icon_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_use_recommend = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_recommend_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_leave_day = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_search_part = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_use = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_wr_super_admin = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_wr_group_admin = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_wr_board_admin = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_wr_write = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_wr_comment_all = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_mb_super_admin = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_mb_member = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_email_po_super_admin = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_prohibit_id = Column(Text, nullable=False, default='')
    cf_prohibit_email = Column(Text, nullable=False, default='')
    cf_new_del = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_memo_del = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_visit_del = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_popular_del = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_optimize_date = Column(String(10), nullable=False, default='')
    cf_use_member_icon = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_member_icon_size = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_member_icon_width = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_member_icon_height = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_member_img_size = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_member_img_width = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_member_img_height = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_login_minutes = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_image_extension = Column(String(255), nullable=False, default='')
    cf_flash_extension = Column(String(255), nullable=False, default='')
    cf_movie_extension = Column(String(255), nullable=False, default='')
    cf_formmail_is_member = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_page_rows = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_mobile_page_rows = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_visit = Column(String(255), nullable=False, default='')
    cf_max_po_id = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_stipulation = Column(Text, nullable=False, default='')
    cf_privacy = Column(Text, nullable=False, default='')
    cf_open_modify = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_memo_send_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_mobile_new_skin = Column(String(50), nullable=False, default='')
    cf_mobile_search_skin = Column(String(50), nullable=False, default='')
    cf_mobile_connect_skin = Column(String(50), nullable=False, default='')
    cf_mobile_faq_skin = Column(String(50), nullable=False, default='')
    cf_mobile_member_skin = Column(String(50), nullable=False, default='')
    cf_captcha_mp3 = Column(String(255), nullable=False, default='')
    cf_editor = Column(String(50), nullable=False, default='')
    cf_cert_use = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_cert_find = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_cert_ipin = Column(String(255), nullable=False, default='')
    cf_cert_hp = Column(String(255), nullable=False, default='')
    cf_cert_simple = Column(String(255), nullable=False, default='')
    cf_cert_kg_cd = Column(String(255), nullable=False, default='')
    cf_cert_kg_mid = Column(String(255), nullable=False, default='')
    cf_cert_kcb_cd = Column(String(255), nullable=False, default='')
    cf_cert_kcp_cd = Column(String(255), nullable=False, default='')
    cf_lg_mid = Column(String(100), nullable=False, default='')
    cf_lg_mert_key = Column(String(100), nullable=False, default='')
    cf_cert_limit = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_cert_req = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_sms_use = Column(String(255), nullable=False, default='')
    cf_sms_type = Column(String(10), nullable=False, default='')
    cf_icode_id = Column(String(255), nullable=False, default='')
    cf_icode_pw = Column(String(255), nullable=False, default='')
    cf_icode_server_ip = Column(String(50), nullable=False, default='')
    cf_icode_server_port = Column(String(50), nullable=False, default='')
    cf_icode_token_key = Column(String(100), nullable=False, default='')
    cf_googl_shorturl_apikey = Column(String(50), nullable=False, default='')
    cf_social_login_use = Column(Integer, nullable=False, default=0, server_default=text('0'))
    cf_social_servicelist = Column(String(255), nullable=False, default='')
    cf_payco_clientid = Column(String(100), nullable=False, default='')
    cf_payco_secret = Column(String(100), nullable=False, default='')
    cf_facebook_appid = Column(String(100), nullable=False, default='')
    cf_facebook_secret = Column(String(100), nullable=False, default='')
    cf_twitter_key = Column(String(100), nullable=False, default='')
    cf_twitter_secret = Column(String(100), nullable=False, default='')
    cf_google_clientid = Column(String(100), nullable=False, default='')
    cf_google_secret = Column(String(100), nullable=False, default='')
    cf_naver_clientid = Column(String(100), nullable=False, default='')
    cf_naver_secret = Column(String(100), nullable=False, default='')
    cf_kakao_rest_key = Column(String(100), nullable=False, default='')
    cf_kakao_client_secret = Column(String(100), nullable=False, default='')
    cf_kakao_js_apikey = Column(String(100), nullable=False, default='')
    cf_captcha = Column(String(100), nullable=False, default='')
    cf_recaptcha_site_key = Column(String(100), nullable=False, default='')
    cf_recaptcha_secret_key = Column(String(100), nullable=False, default='')
    cf_1_subj = Column(String(255), nullable=False, default='')
    cf_2_subj = Column(String(255), nullable=False, default='')
    cf_3_subj = Column(String(255), nullable=False, default='')
    cf_4_subj = Column(String(255), nullable=False, default='')
    cf_5_subj = Column(String(255), nullable=False, default='')
    cf_6_subj = Column(String(255), nullable=False, default='')
    cf_7_subj = Column(String(255), nullable=False, default='')
    cf_8_subj = Column(String(255), nullable=False, default='')
    cf_9_subj = Column(String(255), nullable=False, default='')
    cf_10_subj = Column(String(255), nullable=False, default='')
    cf_1 = Column(String(255), nullable=False, default='')
    cf_2 = Column(String(255), nullable=False, default='')
    cf_3 = Column(String(255), nullable=False, default='')
    cf_4 = Column(String(255), nullable=False, default='')
    cf_5 = Column(String(255), nullable=False, default='')
    cf_6 = Column(String(255), nullable=False, default='')
    cf_7 = Column(String(255), nullable=False, default='')
    cf_8 = Column(String(255), nullable=False, default='')
    cf_9 = Column(String(255), nullable=False, default='')
    cf_10 = Column(String(255), nullable=False, default='')
    

class Member(Base):
    '''
    회원 테이블
    '''
    __tablename__ = 'g6_member'

    mb_no = Column(Integer, primary_key=True)
    mb_id = Column(String(20), unique=True, nullable=False, default='')
    mb_password = Column(String(255), nullable=False, default='')
    mb_name = Column(String(255), nullable=False, default='')
    mb_nick = Column(String(255), nullable=False, default='')
    mb_nick_date = Column(String(30), nullable=False)
    mb_email = Column(String(255), nullable=False, default='')
    mb_homepage = Column(String(255), nullable=False, default='')
    mb_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_sex = Column(String(1), nullable=False, default='')
    mb_birth = Column(String(255), nullable=False, default='')
    mb_tel = Column(String(255), nullable=False, default='')
    mb_hp = Column(String(255), nullable=False, default='')
    mb_certify = Column(String(20), nullable=False, default='')
    mb_adult = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_dupinfo = Column(String(255), nullable=False, default='')
    mb_zip1 = Column(String(3), nullable=False, default='')
    mb_zip2 = Column(String(3), nullable=False, default='')
    mb_addr1 = Column(String(255), nullable=False, default='')
    mb_addr2 = Column(String(255), nullable=False, default='')
    mb_addr3 = Column(String(255), nullable=False, default='')
    mb_addr_jibeon = Column(String(255), nullable=False, default='')
    mb_signature = Column(Text, nullable=False, default='')
    mb_recommend = Column(String(255), nullable=False, default='')
    mb_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_today_login = Column(String(19), nullable=False, default='') # 오늘 접속일시 YYYY-MM-DD HH:MM:SS
    mb_login_ip = Column(String(255), nullable=False, default='')
    mb_datetime = Column(String(30), nullable=False, default='')
    mb_ip = Column(String(255), nullable=False, default='')
    mb_leave_date = Column(String(8), nullable=False, default='')
    mb_intercept_date = Column(String(8), nullable=False, default='')
    mb_email_certify = Column(String(30), nullable=False, default='')
    mb_email_certify2 = Column(String(255), nullable=False, default='')
    mb_memo = Column(Text, nullable=False, default='')
    mb_lost_certify = Column(String(255), nullable=False, default='')
    mb_mailling = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_sms = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_open = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_open_date = Column(String(30), nullable=False, default='')
    mb_profile = Column(Text, nullable=False, default='')
    mb_memo_call = Column(String(255), nullable=False, default='')
    mb_memo_cnt = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_scrap_cnt = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_1 = Column(String(255), nullable=False, default='')
    mb_2 = Column(String(255), nullable=False, default='')
    mb_3 = Column(String(255), nullable=False, default='')
    mb_4 = Column(String(255), nullable=False, default='')
    mb_5 = Column(String(255), nullable=False, default='')
    mb_6 = Column(String(255), nullable=False, default='')
    mb_7 = Column(String(255), nullable=False, default='')
    mb_8 = Column(String(255), nullable=False, default='')
    mb_9 = Column(String(255), nullable=False, default='')
    mb_10 = Column(String(255), nullable=False, default='')


class Board(Base):
    '''
    게시판 설정 테이블
    '''
    __tablename__ = 'g6_board'
    
    bo_table = Column(String(20), primary_key=True, nullable=False)
    gr_id = Column(String(255), nullable=False, default='')
    bo_subject = Column(String(255), nullable=False, default='')
    bo_mobile_subject = Column(String(255), nullable=False, default='')
    bo_device = Column(Enum('both', 'pc', 'mobile'), nullable=False, default='both')
    bo_admin = Column(String(255), nullable=False, default='')
    bo_list_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_read_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_write_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_reply_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_comment_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_upload_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_download_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_html_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_link_level = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_count_delete = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_count_modify = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_read_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_write_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_comment_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_download_point = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_category = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_category_list = Column(Text, nullable=False, default='')
    bo_use_sideview = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_file_content = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_secret = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_dhtml_editor = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_select_editor = Column(String(50), nullable=False, default='')
    bo_use_rss_view = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_good = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_nogood = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_name = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_signature = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_ip_view = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_list_view = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_list_file = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_list_content = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_table_width = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_subject_len = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_mobile_subject_len = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_page_rows = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_mobile_page_rows = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_new = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_hot = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_image_width = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_skin = Column(String(255), nullable=False, default='')
    bo_mobile_skin = Column(String(255), nullable=False, default='')
    bo_include_head = Column(String(255), nullable=False, default='')
    bo_include_tail = Column(String(255), nullable=False, default='')
    bo_content_head = Column(Text, nullable=False, default='')
    bo_mobile_content_head = Column(Text, nullable=False, default='')
    bo_content_tail = Column(Text, nullable=False, default='')
    bo_mobile_content_tail = Column(Text, nullable=False, default='')
    bo_insert_content = Column(Text, nullable=False, default='')
    bo_gallery_cols = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_gallery_width = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_gallery_height = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_mobile_gallery_width = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_mobile_gallery_height = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_upload_size = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_reply_order = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_search = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_order = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_count_write = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_count_comment = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_write_min = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_write_max = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_comment_min = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_comment_max = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_notice = Column(Text, nullable=False, default='')
    bo_upload_count = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_email = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_cert = Column(Enum('', 'cert', 'adult', 'hp-cert', 'hp-adult'), nullable=False, default='')
    bo_use_sns = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_use_captcha = Column(Integer, nullable=False, default=0, server_default=text('0'))
    bo_sort_field = Column(String(255), nullable=False, default='')
    bo_1_subj = Column(String(255), nullable=False, default='')
    bo_2_subj = Column(String(255), nullable=False, default='')
    bo_3_subj = Column(String(255), nullable=False, default='')
    bo_4_subj = Column(String(255), nullable=False, default='')
    bo_5_subj = Column(String(255), nullable=False, default='')
    bo_6_subj = Column(String(255), nullable=False, default='')
    bo_7_subj = Column(String(255), nullable=False, default='')
    bo_8_subj = Column(String(255), nullable=False, default='')
    bo_9_subj = Column(String(255), nullable=False, default='')
    bo_10_subj = Column(String(255), nullable=False, default='')
    bo_1 = Column(String(255), nullable=False, default='')
    bo_2 = Column(String(255), nullable=False, default='')
    bo_3 = Column(String(255), nullable=False, default='')
    bo_4 = Column(String(255), nullable=False, default='')
    bo_5 = Column(String(255), nullable=False, default='')
    bo_6 = Column(String(255), nullable=False, default='')
    bo_7 = Column(String(255), nullable=False, default='')
    bo_8 = Column(String(255), nullable=False, default='')
    bo_9 = Column(String(255), nullable=False, default='')
    bo_10 = Column(String(255), nullable=False, default='')
    # 종속관계
    # writes = relationship("Write", backref="board")
    
    
class WriteBaseModel(Base):
    '''
    게시글, 댓글 테이블
    wr_is_comment : 0=글, 1=댓글
    '''
    # __tablename__ = 'g6_write'
    __abstract__ = True
    
    wr_id = Column(Integer, primary_key=True, nullable=False)
    wr_num = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_reply = Column(String(10), nullable=False, default='')
    wr_parent = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_is_comment = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_comment = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_comment_reply = Column(String(5), nullable=False, default='')
    ca_name = Column(String(255), nullable=False, default='')
    wr_option = Column(Enum('html1', 'html2', 'secret', 'mail'), nullable=False, default='html1')
    wr_subject = Column(String(255), nullable=False, default='')
    wr_content = Column(Text, nullable=False, default='')
    wr_seo_title = Column(String(255), nullable=False, default='')
    wr_link1 = Column(Text, nullable=False, default='')
    wr_link2 = Column(Text, nullable=False, default='')
    wr_link1_hit = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_link2_hit = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_hit = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_good = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_nogood = Column(Integer, nullable=False, default=0, server_default=text('0'))
    mb_id = Column(String(20), nullable=False, default='')
    wr_password = Column(String(255), nullable=False, default='')
    wr_name = Column(String(255), nullable=False, default='')
    wr_email = Column(String(255), nullable=False, default='')
    wr_homepage = Column(String(255), nullable=False, default='')
    wr_datetime = Column(DateTime, nullable=False,default='')
    wr_file = Column(Integer, nullable=False, default=0, server_default=text('0'))
    wr_last = Column(String(30), nullable=False, default='')
    wr_ip = Column(String(255), nullable=False, default='')
    wr_facebook_user = Column(String(255), nullable=False, default='')
    wr_twitter_user = Column(String(255), nullable=False, default='')
    wr_1 = Column(String(255), nullable=False, default='')
    wr_2 = Column(String(255), nullable=False, default='')
    wr_3 = Column(String(255), nullable=False, default='')
    wr_4 = Column(String(255), nullable=False, default='')
    wr_5 = Column(String(255), nullable=False, default='')
    wr_6 = Column(String(255), nullable=False, default='')
    wr_7 = Column(String(255), nullable=False, default='')
    wr_8 = Column(String(255), nullable=False, default='')
    wr_9 = Column(String(255), nullable=False, default='')
    wr_10 = Column(String(255), nullable=False, default='')
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


# CREATE TABLE `g5_group` (
#   `gr_id` varchar(10) NOT NULL DEFAULT '',
#   `gr_subject` varchar(255) NOT NULL DEFAULT '',
#   `gr_device` enum('both','pc','mobile') NOT NULL DEFAULT 'both',
#   `gr_admin` varchar(255) NOT NULL DEFAULT '',
#   `gr_use_access` tinyint NOT NULL DEFAULT '0',
#   `gr_order` int NOT NULL DEFAULT '0',
#   `gr_1_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_2_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_3_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_4_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_5_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_6_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_7_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_8_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_9_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_10_subj` varchar(255) NOT NULL DEFAULT '',
#   `gr_1` varchar(255) NOT NULL DEFAULT '',
#   `gr_2` varchar(255) NOT NULL DEFAULT '',
#   `gr_3` varchar(255) NOT NULL DEFAULT '',
#   `gr_4` varchar(255) NOT NULL DEFAULT '',
#   `gr_5` varchar(255) NOT NULL DEFAULT '',
#   `gr_6` varchar(255) NOT NULL DEFAULT '',
#   `gr_7` varchar(255) NOT NULL DEFAULT '',
#   `gr_8` varchar(255) NOT NULL DEFAULT '',
#   `gr_9` varchar(255) NOT NULL DEFAULT '',
#   `gr_10` varchar(255) NOT NULL DEFAULT ''
# ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
# 위 sql 문을 model 로 만들어줘
class Group(Base):
    '''
    게시판 그룹 테이블
    '''
    __tablename__ = 'g6_group'
    
    gr_id = Column(String(10), primary_key=True, nullable=False)
    gr_subject = Column(String(255), nullable=False, default='')
    gr_device = Column(Enum('both', 'pc', 'mobile'), nullable=False, default='both')
    gr_admin = Column(String(255), nullable=False, default='')
    gr_use_access = Column(Integer, nullable=False, default=0, server_default=text('0'))
    gr_order = Column(Integer, nullable=False, default=0, server_default=text('0'))
    gr_1_subj = Column(String(255), nullable=False, default='')
    gr_2_subj = Column(String(255), nullable=False, default='')
    gr_3_subj = Column(String(255), nullable=False, default='')
    gr_4_subj = Column(String(255), nullable=False, default='')
    gr_5_subj = Column(String(255), nullable=False, default='')
    gr_6_subj = Column(String(255), nullable=False, default='')
    gr_7_subj = Column(String(255), nullable=False, default='')
    gr_8_subj = Column(String(255), nullable=False, default='')
    gr_9_subj = Column(String(255), nullable=False, default='')
    gr_10_subj = Column(String(255), nullable=False, default='')
    gr_1 = Column(String(255), nullable=False, default='')
    gr_2 = Column(String(255), nullable=False, default='')
    gr_3 = Column(String(255), nullable=False, default='')
    gr_4 = Column(String(255), nullable=False, default='')
    gr_5 = Column(String(255), nullable=False, default='')
    gr_6 = Column(String(255), nullable=False, default='')
    gr_7 = Column(String(255), nullable=False, default='')
    gr_8 = Column(String(255), nullable=False, default='')
    gr_9 = Column(String(255), nullable=False, default='')
    gr_10 = Column(String(255), nullable=False, default='')
    # 종속관계
    # boards = relationship("Board", backref="group")
    
class Content(Base):
    '''
    g5_content 테이블
    '''
    __tablename__ = 'g6_content'

    co_id = Column(String(20), primary_key=True, nullable=False, default='')
    co_html = Column(TINYINT, nullable=False, default=0)
    co_subject = Column(String(255), nullable=False, default='')
    co_content = Column(Text, nullable=False)
    co_seo_title = Column(String(255), nullable=False, default='')
    co_mobile_content = Column(Text, nullable=False)
    co_skin = Column(String(255), nullable=False, default='')
    co_mobile_skin = Column(String(255), nullable=False, default='')
    co_tag_filter_use = Column(TINYINT, nullable=False, default=0)
    co_hit = Column(Integer, nullable=False, default=0)
    co_include_head = Column(String(255), nullable=True)
    co_include_tail = Column(String(255), nullable=True)


class FaqMaster(Base):
    __tablename__ = 'g6_faq_master'

    fm_id = Column(Integer, primary_key=True, autoincrement=True)
    fm_subject = Column(String(255), nullable=False, default='')
    fm_head_html = Column(Text, nullable=True)
    fm_tail_html = Column(Text, nullable=True)
    fm_mobile_head_html = Column(Text, nullable=True)
    fm_mobile_tail_html = Column(Text, nullable=False)
    fm_order = Column(Integer, nullable=False, default=0)

    # 연관관계
    faqs = relationship("Faq", back_populates="faq_master", cascade="all, delete-orphan")


class Faq(Base):
    __tablename__ = 'g6_faq'

    fa_id = Column(Integer, primary_key=True, autoincrement=True)
    fm_id = Column(Integer, ForeignKey('g6_faq_master.fm_id'), nullable=False, default=0)
    fa_subject = Column(Text, nullable=False)
    fa_content = Column(Text, nullable=False)
    fa_order = Column(Integer, nullable=False, default=0)

    # 연관관계
    faq_master = relationship("FaqMaster", back_populates="faqs", foreign_keys=[fm_id])


class Visit(Base):
    __tablename__ = 'g6_visit'
    
    vi_id = Column(Integer, primary_key=True, autoincrement=True)
    vi_ip = Column(String(100), nullable=False, default='')
    vi_date = Column(Date, nullable=False, default='')
    vi_time = Column(Time, nullable=False, default='')
    vi_referer = Column(Text, nullable=False, default='')
    vi_agent = Column(String(200), nullable=False, default='')
    vi_browser = Column(String(255), nullable=False, default='')
    vi_os = Column(String(255), nullable=False, default='')
    vi_device = Column(String(255), nullable=False, default='')
    
    
class VisitSum(Base):
    __tablename__ = 'g6_visit_sum'
    
    vs_date = Column(Date, primary_key=True, nullable=False, default='')
    vs_count = Column(Integer, nullable=False, default=0)

class QaConfig(Base):
    """ Q&A 설정 테이블
    """
    __tablename__ = 'g6_qa_config'

    id = Column(Integer, primary_key=True)
    qa_title = Column(String(255), nullable=False, default='')
    qa_category = Column(String(255), nullable=False, default='')
    qa_skin = Column(String(255), nullable=False, default='')
    qa_mobile_skin = Column(String(255), nullable=False, default='')
    qa_use_email = Column(TINYINT, nullable=False, default=0)
    qa_req_email = Column(TINYINT, nullable=False, default=0)
    qa_use_hp = Column(TINYINT, nullable=False, default=0)
    qa_req_hp = Column(TINYINT, nullable=False, default=0)
    qa_use_sms = Column(TINYINT, nullable=False, default=0)
    qa_send_number = Column(String(255), nullable=False, default='0')
    qa_admin_hp = Column(String(255), nullable=False, default='')
    qa_admin_email = Column(String(255), nullable=False, default='')
    qa_use_editor = Column(TINYINT, nullable=False, default=0)
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
    """ Q&A 데이터 테이블
    """
    __tablename__ = 'g6_qa_content'

    qa_id = Column(Integer, primary_key=True, autoincrement=True)
    qa_num = Column(Integer, nullable=False, default=0)
    qa_parent = Column(Integer, nullable=False, default=0)
    qa_related = Column(Integer, nullable=False, default=0)
    mb_id = Column(String(20), ForeignKey('g6_member.mb_id'), nullable=False, default='')
    qa_name = Column(String(255), nullable=False, default='')
    qa_email = Column(String(255), nullable=False, default='')
    qa_hp = Column(String(255), nullable=False, default='')
    qa_type = Column(Integer, nullable=False, default=0)
    qa_category = Column(String(255), nullable=False, default='')
    qa_email_recv = Column(TINYINT, nullable=False, default=0)
    qa_sms_recv = Column(TINYINT, nullable=False, default=0)
    qa_html = Column(TINYINT, nullable=False, default=0)
    qa_subject = Column(String(255), nullable=False, default='')
    qa_content = Column(Text, nullable=False)
    qa_status = Column(Integer, nullable=False, default=0)
    qa_file1 = Column(String(255), nullable=False, default='')
    qa_source1 = Column(String(255), nullable=False, default='')
    qa_file2 = Column(String(255), nullable=False, default='')
    qa_source2 = Column(String(255), nullable=False, default='')
    qa_ip = Column(String(255), nullable=False, default='')
    qa_datetime = Column(DateTime, nullable=False, default=datetime(1900, 1, 1, 0, 0))
    qa_1 = Column(String(255), nullable=False, default='')
    qa_2 = Column(String(255), nullable=False, default='')
    qa_3 = Column(String(255), nullable=False, default='')
    qa_4 = Column(String(255), nullable=False, default='')
    qa_5 = Column(String(255), nullable=False, default='')

    # Index 추가
    qa_num_parent_index = Index('qa_num_parent', qa_num, qa_parent)


class Menu(Base):
    __tablename__ = 'g6_menu'

    me_id = Column(Integer, primary_key=True, autoincrement=True)
    me_code = Column(String(255), nullable=False, default='')
    me_name = Column(String(255), nullable=False, default='')
    me_link = Column(String(255), nullable=False, default='')
    me_target = Column(String(255), nullable=False, default='')
    me_order = Column(Integer, nullable=False, default=0)
    me_use = Column(TINYINT, nullable=False, default=0)
    me_mobile_use = Column(TINYINT, nullable=False, default=0)
    
    
# CREATE TABLE `g5_point` (
#   `po_id` int NOT NULL,
#   `mb_id` varchar(20) NOT NULL DEFAULT '',
#   `po_datetime` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
#   `po_content` varchar(255) NOT NULL DEFAULT '',
#   `po_point` int NOT NULL DEFAULT '0',
#   `po_use_point` int NOT NULL DEFAULT '0',
#   `po_expired` tinyint NOT NULL DEFAULT '0',
#   `po_expire_date` date NOT NULL DEFAULT '0000-00-00',
#   `po_mb_point` int NOT NULL DEFAULT '0',
#   `po_rel_table` varchar(20) NOT NULL DEFAULT '',
#   `po_rel_id` varchar(20) NOT NULL DEFAULT '',
#   `po_rel_action` varchar(100) NOT NULL DEFAULT ''
# ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
    
class Point(Base):
    '''
    포인트 테이블
    '''
    __tablename__ = 'g6_point'
    
    po_id = Column(Integer, primary_key=True, autoincrement=True)
    mb_id = Column(String(20), nullable=False, default='')    
    po_datetime = Column(DateTime, nullable=False, default='0000-00-00 00:00:00')
    po_content = Column(String(255), nullable=False, default='')
    po_point = Column(Integer, nullable=False, default=0)
    po_use_point = Column(Integer, nullable=False, default=0)
    po_expired = Column(TINYINT, nullable=False, default=0)
    po_expire_date = Column(Date, nullable=False, default='0000-00-00')
    po_mb_point = Column(Integer, nullable=False, default=0)
    po_rel_table = Column(String(20), nullable=False, default='')
    po_rel_id = Column(String(20), nullable=False, default='')
    po_rel_action = Column(String(100), nullable=False, default='')


class Memo(Base):
    '''
    쪽지 테이블
    '''
    __tablename__ = 'g6_memo'
    
    me_id = Column(Integer, primary_key=True, autoincrement=True)
    me_recv_mb_id = Column(String(20), nullable=False, default='')
    me_send_mb_id = Column(String(20), nullable=False, default='')
    me_send_datetime = Column(DateTime, nullable=False, default=datetime.now())
    me_read_datetime = Column(DateTime, nullable=True)
    me_memo = Column(Text, nullable=False)
    me_send_id = Column(Integer, nullable=False, default=0)
    me_type = Column(Enum('send', 'recv'), nullable=False, default='recv')
    me_send_ip = Column(String(100), nullable=False, default='')
    
    # 종속관계
    # recv_member = relationship("Member", foreign_keys=[me_recv_mb_id])
    # send_member = relationship("Member", foreign_keys=[me_send_mb_id])


class Popular(Base):
    '''
    인기검색어 테이블
    '''
    __tablename__ = 'g6_popular'
    
    pp_id = Column(Integer, primary_key=True, autoincrement=True)
    pp_word = Column(String(50), nullable=False, default='')
    pp_date = Column(Date, nullable=False)
    pp_ip = Column(String(50), nullable=False, default='')

    # Index 추가
    index1 = Index('index1', pp_date, pp_word, pp_ip, unique=True)