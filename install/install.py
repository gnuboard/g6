"""
    터미널 명령어를 통해 설치
    - 미사용으로 인한 삭제 예정
"""
# 프로그램 실행전 필요한 정보 설치하는 스크립트
import os
import sys

# '.env' 파일의 경로를 설정합니다. 현재 작업 디렉토리에 있다고 가정합니다.
env_path = os.path.join(os.getcwd(), '.env')

# 파일이 존재하는지 확인합니다.
if os.path.exists(env_path):
    print(".env 파일이 존재하면 설치를 진행하지 않습니다.")
    sys.exit(1)  # 프로그램 종료


import re
import getpass
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import exists

from core.database import engine, SessionLocal
import core.models as models
from lib.common import dynamic_create_write_table, read_version
from lib.pbkdf2 import create_hash

VERSION = read_version()

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

# 기본값 설정
default_gr_id = 'community'
default_read_point = -1
default_write_point = 5
default_comment_point = 1
default_download_point = -20
# $tmp_bo_subject = array ("공지사항", "질문답변", "자유게시판", "갤러리");
#default_bo_table   = array ("notice", "qa", "free", "gallery");
default_bo_table = {
    'notice':'공지사항', 
    'qa':'질문답변',
    'free':'자유게시판',
    'gallery':'갤러리'
}


# 환경설정 기본값 등록
def config_setup(admin_id, admin_email):
    print(f"환경설정 : 기본값 등록을 시작합니다.")
    
    exists_config = db.scalar(
        exists(models.Config)
        .where(models.Config.cf_id == 1).select()
    )
    if not exists_config:
        new_config = models.Config(
            cf_id=1,
            cf_title=VERSION,
            cf_theme='basic',
            cf_admin=admin_id,
            cf_admin_email=admin_email,
            cf_admin_email_name=VERSION,
            cf_use_point=1,
            cf_use_copy_log=1,
            cf_login_point=100,
            cf_cut_name=15,
            cf_nick_modify=60,
            cf_new_skin='basic',
            cf_new_rows=15,
            cf_search_skin='basic',
            cf_connect_skin='basic',
            cf_faq_skin='basic',
            cf_read_point=default_read_point,
            cf_write_point = default_write_point,
            cf_comment_point = default_comment_point,
            cf_download_point = default_download_point,
            cf_write_pages = '10',
            cf_mobile_pages = '5',
            cf_link_target = '_blank',
            cf_delay_sec = '30',
            cf_filter = '18아,18놈,18새끼,18뇬,18노,18것,18넘,개년,개놈,개뇬,개새,개색끼,개세끼,개세이,개쉐이,개쉑,개쉽,개시키,개자식,개좆,게색기,게색끼,광뇬,뇬,눈깔,뉘미럴,니귀미,니기미,니미,도촬,되질래,뒈져라,뒈진다,디져라,디진다,디질래,병쉰,병신,뻐큐,뻑큐,뽁큐,삐리넷,새꺄,쉬발,쉬밸,쉬팔,쉽알,스패킹,스팽,시벌,시부랄,시부럴,시부리,시불,시브랄,시팍,시팔,시펄,실밸,십8,십쌔,십창,싶알,쌉년,썅놈,쌔끼,쌩쑈,썅,써벌,썩을년,쎄꺄,쎄엑,쓰바,쓰발,쓰벌,쓰팔,씨8,씨댕,씨바,씨발,씨뱅,씨봉알,씨부랄,씨부럴,씨부렁,씨부리,씨불,씨브랄,씨빠,씨빨,씨뽀랄,씨팍,씨팔,씨펄,씹,아가리,아갈이,엄창,접년,잡놈,재랄,저주글,조까,조빠,조쟁이,조지냐,조진다,조질래,존나,존니,좀물,좁년,좃,좆,좇,쥐랄,쥐롤,쥬디,지랄,지럴,지롤,지미랄,쫍빱,凸,퍽큐,뻑큐,빠큐,ㅅㅂㄹㅁ',
            cf_possible_ip = '',
            cf_intercept_ip = '',
            cf_member_skin = 'basic',
            cf_mobile_new_skin = 'basic',
            cf_mobile_search_skin = 'basic',
            cf_mobile_connect_skin = 'basic',
            cf_mobile_member_skin = 'basic',
            cf_mobile_faq_skin = 'basic',
            cf_editor = 'ckeditor4',
            cf_captcha_mp3 = 'basic',
            cf_register_level = '2',
            cf_register_point = '1000',
            cf_icon_level = '2',
            cf_leave_day = '30',
            cf_search_part = '10000',
            cf_email_use = '1',
            cf_prohibit_id = 'admin,administrator,관리자,운영자,어드민,주인장,webmaster,웹마스터,sysop,시삽,시샵,manager,매니저,메니저,root,루트,su,guest,방문객',
            cf_prohibit_email = '',
            cf_new_del = '30',
            cf_memo_del = '180',
            cf_visit_del = '180',
            cf_popular_del = '180',
            cf_use_member_icon = '2',
            cf_member_icon_size = '5000',
            cf_member_icon_width = '22',
            cf_member_icon_height = '22',
            cf_member_img_size = '50000',
            cf_member_img_width = '60',
            cf_member_img_height = '60',
            cf_login_minutes = '10',
            cf_image_extension = 'gif|jpg|jpeg|png|webp',
            cf_flash_extension = 'swf',
            cf_movie_extension = 'asx|asf|wmv|wma|mpg|mpeg|mov|avi|mp3',
            cf_formmail_is_member = '1',
            cf_page_rows = '15',
            cf_mobile_page_rows = '15',
            cf_cert_limit = '2',
            cf_stipulation = '해당 홈페이지에 맞는 회원가입약관을 입력합니다.',
            cf_privacy = '해당 홈페이지에 맞는 개인정보처리방침을 입력합니다.'
    
        )
        try:
            db.add(new_config)
            db.commit()
            print(f"환경설정 : 정상 등록되었습니다.")
        except SQLAlchemyError as e:
            db.rollback()
            print(f"환경설정 에러: {e}")
            print(new_config.__dict__)
            
            
# 관리자 기본값 등록
def admin_member_setup(admin_id, admin_password, admin_email):
    print(f"관리자 : 기본값 등록을 시작합니다.")
    
    # exists_config = db.query(models.Config).filter_by(cf_id=1, cf_admin=admin_id).first()
    # if exists_config:
    #     print(f"관리자 : {admin_id} 관리자 아이디가 이미 등록되어 있어 관리자를 새로 등록하지 않습니다.")
    #     return

    exists_admin_member = db.scalar(
        exists(models.Member)
        .where(models.Member.mb_id == admin_id).select()
    )
    if not exists_admin_member:
        new_admin_member = models.Member(
            mb_id=admin_id,
            mb_password=create_hash(admin_password),
            mb_name=admin_id,
            mb_nick=admin_id,
            mb_email=admin_email,
            mb_level=10,
            mb_mailling=1,
            mb_open=1,
            mb_nick_date=datetime.now(),
            mb_email_certify=datetime.now(),
            mb_datetime=datetime.now(),
            mb_ip='127.0.0.1'            
        )
        try:
            db.add(new_admin_member)
            db.commit()
            print(f"관리자 : 정상 등록되었습니다.")
        except SQLAlchemyError as e:
            db.rollback()
            print(f"관리자 에러: {e}")
            print(new_admin_member.__dict__)   
                
        

# 컨텐츠 기본값 등록
def content_setup():
    print(f"컨텐츠 : 기본값 등록을 시작합니다.")

    content_default = [
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
    
    for content in content_default:
        exists_content = db.scalar(
            exists(models.Content)
            .where(models.Content.co_id == content['co_id']).select()
        )
        if exists_content is None:
            new_content = models.Content(
                co_id=content['co_id'],
                co_html=content['co_html'],
                co_subject=content['co_subject'],
                co_content=content['co_content'],
                co_mobile_content='',
                co_skin=content['co_skin'],
                co_mobile_skin=content['co_mobile_skin'],
            )
            try:
                db.add(new_content)
                db.commit()
                print(f"컨텐츠 - {content['co_subject']}({content['co_id']}) : 정상 등록되었습니다.")
            except SQLAlchemyError as e:
                db.rollback()
                print(f"컨텐츠 에러 - {content['co_subject']}({content['co_id']}): {e}")
                print(new_content.__dict__)


# FAQ Master 기본값 등록
def faq_master_setup():
    print(f"FAQ Master : 기본값 등록을 시작합니다.")
    
    exists_faq_master = db.scalar(
        exists(models.FaqMaster)
        .where(models.FaqMaster.fm_id == 1).select()
    )
    if exists_faq_master is None:
        new_faq_master = models.FaqMaster(
            fm_id=1, 
            fm_subject='자주하시는 질문'
        )
        try:
            db.add(new_faq_master)
            db.commit()
            print(f"FAQ Master : 정상 등록되었습니다.")
        except SQLAlchemyError as e:
            db.rollback()
            print(f"FAQ Master 에러: {e}")
            print(new_faq_master.__dict__)
            

# 게시판 그룹 기본값 생성            
def board_group_setup():
    print(f"게시판 그룹 : 기본값 등록을 시작합니다.")
    
    exists_board_group = db.scalar(
        exists(models.Group)
        .where(models.Group.gr_id == default_gr_id).select()
    )
    if exists_board_group is None:
        new_board_group = models.Group(gr_id=default_gr_id, gr_subject='커뮤니티')
        try:
            db.add(new_board_group)
            db.commit()
            print(f"게시판 그룹 ({default_gr_id}) : 정상 등록되었습니다.")
        except SQLAlchemyError as e:
            db.rollback()
            print(f"게시판 그룹 ({default_gr_id}) 에러: {e}")
            print(new_board_group.__dict__)
            
            
# 게시판 기본값 및 테이블 생성
def board_setup():
    print(f"게시판 : 기본값 등록 및 테이블 생성을 시작합니다.")

    for bo_table, bo_subject in default_bo_table.items():
        bo_skin = 'basic' if bo_table != 'gallery' else 'gallery'
        exists_board = db.scalar(
            exists(models.Board)
            .where(models.Board.bo_table == bo_table).select()
        )
        if exists_board is None:
            new_board = models.Board(
                bo_table=bo_table,
                gr_id=default_gr_id,
                bo_subject=bo_subject,
                bo_skin=bo_skin,
                bo_mobile_skin=bo_skin,
                bo_read_point=default_read_point,
                bo_write_point=default_write_point,
                bo_comment_point=default_comment_point,
                bo_download_point=default_download_point,
                bo_use_category=0,
                bo_category_list='',
                bo_use_sideview=0,
                bo_use_file_content=0,
                bo_use_secret=0,
                bo_use_dhtml_editor=1,
                bo_use_rss_view=0,
                bo_use_good=0,
                bo_use_nogood=0,
                bo_use_name=0,
                bo_use_signature=0,
                bo_use_ip_view=0,
                bo_use_list_view=0,
                bo_use_list_file=0,
                bo_use_list_content=0,
                bo_use_email=0,
                bo_use_cert='',
                bo_use_sns=0,
                bo_order='1',
                bo_notice='',
                bo_upload_count=2,
                bo_upload_size=10485760,
                bo_reply_order='1',
                bo_comment_level=1,
                bo_sort_field='',
                bo_table_width=100,
                bo_1_subj='',
                bo_2_subj='',
                bo_3_subj='',
                bo_4_subj='',
                bo_5_subj='',
                bo_6_subj='',
                bo_7_subj='',
                bo_8_subj='',
                bo_9_subj='',
                bo_10_subj='',
            )
            try:
                db.add(new_board)
                db.commit()
                print(f"게시판 {bo_subject}({bo_table}) : 정상 등록되었습니다.")
            except SQLAlchemyError as e:
                db.rollback()
                print(f"게시판 {bo_subject}({bo_table}) 에러: {e}")
                print(new_board.__dict__)

        # 게시판 테이블 생성
        dynamic_create_write_table(bo_table, True)


def make_directory():        
    data_directory_path = "data"
    print(f"디렉토리 : {data_directory_path} 디렉토리 생성을 시작합니다.")

    if not os.path.exists(data_directory_path):
        os.makedirs(data_directory_path)    
        
        
def is_valid_email(email):
    regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w+$'
    return re.search(regex, email)        

                
def input_admin_information():
    while True:
        admin_id = input("관리자 아이디를 5글자 이상 입력하세요 (기본값: admin): ").strip()
        if not admin_id:
            admin_id = 'admin'
            print(f"관리자 아이디가 admin으로 설정되었습니다.")
        elif len(admin_id) != 5:
            print("관리자 아이디는 5글자이어야 합니다.")
            continue
        break
    print("")
                
    while True:
        admin_password = getpass.getpass("관리자 비밀번호를 5글자 이상 입력하세요: ").strip()
        if len(admin_password) < 5:
            print("비밀번호는 5글자 이상이어야 합니다.")
            continue
        break
    print("")
        
    while True:
        admin_email = input("관리자 이메일 주소를 입력하세요: ")
        if not is_valid_email(admin_email):
            print("유효한 이메일 주소를 입력하세요.")
            continue
        break
    print("")
    
    return admin_id, admin_password, admin_email

# 함수를 호출하여 관리자 정보를 입력 받기
admin_id, admin_password, admin_email = input_admin_information()

config_setup(admin_id, admin_email)
admin_member_setup(admin_id, admin_password, admin_email)
content_setup()
faq_master_setup()
board_group_setup()
board_setup()
make_directory()
print(f"{VERSION} 등록 및 테이블 생성을 완료했습니다.")
