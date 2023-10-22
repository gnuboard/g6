import sys
import getpass
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

sys.path.append('..')
from database import engine
from models import Config, Member
from common import hash_password

Session = sessionmaker(bind=engine)
db = Session()

def change_password(admin_id, new_password):
    try:
        # config 테이블에서 cf_admin 값을 가져옵니다.
        config_admin = db.query(Config.cf_admin).filter_by(cf_id=1).first()
        if config_admin:
            cf_admin = config_admin[0]
            
            if cf_admin != admin_id:
                print(f"입력하신 관리자 아이디 {admin_id}가 설정테이블에 있는 관리자 아이디와 일치하지 않습니다.")
                return
            
            # cf_admin 값과 일치하는 mb_id를 가진 member를 찾습니다.
            member = db.query(Member).filter_by(mb_id=cf_admin)
            if member:
                # 비밀번호를 변경합니다.
                member.mb_password = hash_password(new_password)
                db.commit()
                print(f"{cf_admin} 관리자 비밀번호가 변경되었습니다.")
            else:
                print(f"설정테이블에 있는 관리자 아이디 {cf_admin}가 회원테이블에 존재하지 않습니다.")
        else:
            print(f"설정테이블에 관리자 아이디가 존재하지 않습니다.")
    except OperationalError as e:
        print(f"오류가 발생했습니다: {e}")
        db.rollback()


# 콘솔에서 관리자 아이디와 비밀번호 입력 받기
while True:
    admin_id = input("관리자 아이디를 입력하세요: ").strip()
    if admin_id:
        break
    continue

while True:
    new_password = getpass.getpass("새로운 비밀번호를 입력하세요: ").strip()
    if new_password:
        break
    continue

# 함수 호출
change_password(admin_id, new_password)
