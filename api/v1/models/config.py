"""기본환경설정 모델 클래스를 정의한 파일입니다."""
from pydantic import BaseModel


class HtmlBaseResponse(BaseModel):
    """HTML 설정 응답 모델"""
    cf_title: str
    cf_add_meta: str
    cf_add_script: str
    cf_analytics: str


class PolicyResponse(BaseModel):
    """회원가입 약관 응답 모델"""
    cf_stipulation: str
    cf_privacy: str


class RegisterResponse(BaseModel):
    """회원가입 설정 응답 모델"""
    cf_use_email_certify: int
    cf_use_homepage: int
    cf_req_homepage: int
    cf_use_tel: int
    cf_req_tel: int
    cf_use_hp: int
    cf_req_hp: int
    cf_use_addr: int
    cf_req_addr: int
    cf_use_signature: int
    cf_use_profile: int
    cf_icon_level: int
    cf_member_img_width: int
    cf_member_img_height: int
    cf_member_img_size: int
    cf_member_icon_width: int
    cf_member_icon_height: int
    cf_member_icon_size: int
    cf_open_modify: int
    cf_use_recommend: int


class MemoResponse(BaseModel):
    """쪽지 발송 시, 설정 포인트 응답 모델"""
    cf_memo_send_point: int


class BoardResponse(BaseModel):
    """게시판 설정 응답 모델"""
    cf_use_point: int
    cf_point_term: int
    cf_use_copy_log: int
    cf_cut_name: int
    cf_new_rows: int
    cf_read_point: int
    cf_write_point: int
    cf_comment_point: int
    cf_download_point: int
    cf_write_pages: int
    cf_mobile_pages: int
    cf_link_target: str
    cf_bbs_rewrite: int
    cf_delay_sec: int
    cf_filter: str
    cf_possible_ip: str
    cf_intercept_ip: str