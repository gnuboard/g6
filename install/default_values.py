"""그누보드6 설치 시 기본값을 설정합니다.
- 입력받아야 하는 값들은 추가적으로 선언 후 사용합니다.
   - 최고관리자 아이디, 비밀번호, 이메일 등...
"""
import os
from datetime import datetime

from lib.common import read_version


default_version = read_version()
default_data_directory = 'data'
default_cache_directory = os.path.join(default_data_directory, 'cache')
default_gr_id = 'community'
default_read_point = -1
default_write_point = 5
default_comment_point = 1
default_download_point = -20
default_boards = [
    {
        'bo_table': 'free',
        'bo_subject': '자유게시판',
        'bo_skin': 'basic',
        'bo_mobile_skin': 'basic',
    },
    {
        'bo_table': 'gallery',
        'bo_subject': '갤러리',
        'bo_skin': 'gallery',
        'bo_mobile_skin': 'gallery',
    },
    {
        'bo_table': 'qa',
        'bo_subject': '질문답변',
        'bo_skin': 'basic',
        'bo_mobile_skin': 'basic',
    },
    {
        'bo_table': 'notice',
        'bo_subject': '공지사항',
        'bo_skin': 'basic',
        'bo_mobile_skin': 'basic',
    }
]
default_board_data = {
    'gr_id': default_gr_id,
    'bo_count_delete': 1,
    'bo_read_point': default_read_point,
    'bo_write_point': default_write_point,
    'bo_comment_point': default_comment_point,
    'bo_download_point': default_download_point,
    'bo_use_category': 0,
    'bo_category_list': '',
    'bo_use_sideview': 0,
    'bo_use_file_content': 0,
    'bo_use_secret': 0,
    'bo_use_dhtml_editor': 1,
    'bo_use_rss_view': 0,
    'bo_use_good': 0,
    'bo_use_nogood': 0,
    'bo_use_name': 0,
    'bo_use_signature': 0,
    'bo_use_ip_view': 0,
    'bo_use_list_view': 0,
    'bo_use_list_file': 0,
    'bo_use_list_content': 0,
    'bo_use_email': 0,
    'bo_use_cert': '',
    'bo_use_sns': 0,
    'bo_order': '1',
    'bo_notice': '',
    'bo_upload_count': 2,
    'bo_upload_size': 10485760,
    'bo_reply_order': '1',
    'bo_comment_level': 1,
    'bo_sort_field': '',
    'bo_table_width': 100,
    'bo_1_subj': '',
    'bo_2_subj': '',
    'bo_3_subj': '',
    'bo_4_subj': '',
    'bo_5_subj': '',
    'bo_6_subj': '',
    'bo_7_subj': '',
    'bo_8_subj': '',
    'bo_9_subj': '',
    'bo_10_subj': '',
}
default_config = {
    'cf_id': 1,
    'cf_title': default_version,
    'cf_theme': 'basic',
    'cf_admin_email_name': default_version,
    'cf_use_point': 1,
    'cf_use_copy_log': 1,
    'cf_login_point': 100,
    'cf_cut_name': 15,
    'cf_nick_modify': 60,
    'cf_new_skin': 'basic',
    'cf_new_rows': 15,
    'cf_search_skin': 'basic',
    'cf_connect_skin': 'basic',
    'cf_faq_skin': 'basic',
    'cf_read_point': default_read_point,
    'cf_write_point': default_write_point,
    'cf_comment_point': default_comment_point,
    'cf_download_point': default_download_point,
    'cf_write_pages': '10',
    'cf_mobile_pages': '5',
    'cf_link_target': '_blank',
    'cf_delay_sec': '30',
    'cf_filter': '18아,18놈,18새끼,18뇬,18노,18것,18넘,개년,개놈,개뇬,개새,개색끼,개세끼,개세이,개쉐이,개쉑,개쉽,개시키,개자식,개좆,게색기,게색끼,광뇬,뇬,눈깔,뉘미럴,니귀미,니기미,니미,도촬,되질래,뒈져라,뒈진다,디져라,디진다,디질래,병쉰,병신,뻐큐,뻑큐,뽁큐,삐리넷,새꺄,쉬발,쉬밸,쉬팔,쉽알,스패킹,스팽,시벌,시부랄,시부럴,시부리,시불,시브랄,시팍,시팔,시펄,실밸,십8,십쌔,십창,싶알,쌉년,썅놈,쌔끼,쌩쑈,썅,써벌,썩을년,쎄꺄,쎄엑,쓰바,쓰발,쓰벌,쓰팔,씨8,씨댕,씨바,씨발,씨뱅,씨봉알,씨부랄,씨부럴,씨부렁,씨부리,씨불,씨브랄,씨빠,씨빨,씨뽀랄,씨팍,씨팔,씨펄,씹,아가리,아갈이,엄창,접년,잡놈,재랄,저주글,조까,조빠,조쟁이,조지냐,조진다,조질래,존나,존니,좀물,좁년,좃,좆,좇,쥐랄,쥐롤,쥬디,지랄,지럴,지롤,지미랄,쫍빱,凸,퍽큐,뻑큐,빠큐,ㅅㅂㄹㅁ',
    'cf_possible_ip': '',
    'cf_intercept_ip': '',
    'cf_member_skin': 'basic',
    'cf_mobile_new_skin': 'basic',
    'cf_mobile_search_skin': 'basic',
    'cf_mobile_connect_skin': 'basic',
    'cf_mobile_member_skin': 'basic',
    'cf_mobile_faq_skin': 'basic',
    'cf_editor': 'ckeditor4',
    'cf_captcha_mp3': 'basic',
    'cf_register_level': '2',
    'cf_register_point': '1000',
    'cf_icon_level': '2',
    'cf_leave_day': '30',
    'cf_search_part': '10000',
    'cf_email_use': '1',
    'cf_prohibit_id': 'admin,administrator,관리자,운영자,어드민,주인장,webmaster,웹마스터,sysop,시삽,시샵,manager,매니저,메니저,root,루트,su,guest,방문객',
    'cf_prohibit_email': '',
    'cf_new_del': '30',
    'cf_memo_del': '180',
    'cf_visit_del': '180',
    'cf_popular_del': '180',
    'cf_use_member_icon': '2',
    'cf_member_icon_size': '5000',
    'cf_member_icon_width': '22',
    'cf_member_icon_height': '22',
    'cf_member_img_size': '50000',
    'cf_member_img_width': '60',
    'cf_member_img_height': '60',
    'cf_login_minutes': '10',
    'cf_image_extension': 'gif|jpg|jpeg|png|webp',
    'cf_flash_extension': 'swf',
    'cf_movie_extension': 'asx|asf|wmv|wma|mpg|mpeg|mov|avi|mp3',
    'cf_formmail_is_member': '1',
    'cf_page_rows': '15',
    'cf_mobile_page_rows': '15',
    'cf_cert_limit': '2',
    'cf_stipulation': '해당 홈페이지에 맞는 회원가입약관을 입력합니다.',
    'cf_privacy': '해당 홈페이지에 맞는 개인정보처리방침을 입력합니다.'
}
default_contents = [
    {
        'co_id': 'company',
        'co_html': '1',
        'co_subject': '회사소개',
        'co_content': '<p align=center><b>회사소개에 대한 내용을 입력하십시오.</b></p>',
        'co_skin': 'basic',
        'co_mobile_skin': 'basic',
    },
    {
        'co_id': 'provision',
        'co_html': '1',
        'co_subject': '서비스 이용약관',
        'co_content': '<p align=center><b>서비스 이용약관에 대한 내용을 입력하십시오.</b></p>',
        'co_skin': 'basic',
        'co_mobile_skin': 'basic',
    },
    {
        'co_id': 'privacy',
        'co_html': '1',
        'co_subject': '개인정보 처리방침',
        'co_content': '<p align=center><b>개인정보 처리방침에 대한 내용을 입력하십시오.</b></p>',
        'co_skin': 'basic',
        'co_mobile_skin': 'basic',
    }
]
default_member = {
    'mb_level': 10,
    'mb_mailling': 1,
    'mb_open': 1,
    'mb_nick_date': datetime.now(),
    'mb_email_certify': datetime.now(),
    'mb_datetime': datetime.now(),
    'mb_ip': '127.0.0.1'
}
default_qa_config = {
    'qa_title': '1:1문의',
    'qa_category': '회원|포인트',
    'qa_skin': 'basic',
    'qa_mobile_skin': 'basic',
    'qa_use_email': 1,
    'qa_req_email': 0,
    'qa_use_hp': 1,
    'qa_req_hp': 0,
    'qa_use_editor': 1,
    'qa_subject_len': 60,
    'qa_mobile_subject_len': 30,
    'qa_page_rows': 15,
    'qa_mobile_page_rows': 15,
    'qa_image_width': 600,
    'qa_upload_size': 1048576,
    'qa_insert_content': ''
}
default_faq_master = {
    'fm_id': 1,
    'fm_subject': '자주하시는 질문'
}
default_group = {
    'gr_id': default_gr_id,
    'gr_subject': '커뮤니티'
}
