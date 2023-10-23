# 수정중 ... 완료되지 않음
import sys
from sqlalchemy import MetaData, text
from sqlalchemy.exc import OperationalError

# database.py 가 상위 디렉토리에 있으므로, 상위 디렉토리를 sys.path 에 추가합니다.
sys.path.append('..')
from database import engine

member_table_name = 'g5_member'

metadata = MetaData()

# 테이블 구조를 반영
metadata.reflect(bind=engine)

# g5_config 테이블이 있는지 확인
table = metadata.tables.get(member_table_name)

if table is not None:
    try:
        with engine.connect() as conn:
            # 명시적 트랜잭션 시작
            with conn.begin():
                # 쿼리를 저장할 문자열 초기화
                alter_queries = ""
                
                for column in table.columns:
                    # If the column type is DATE or DATETIME, change it to VARCHAR(20)
                    if str(column.type).lower() in ['date', 'datetime']:
                        alter_query = f"ALTER TABLE `{member_table_name}` MODIFY `{column.name}` VARCHAR(20);"
                        # 쿼리 누적
                        alter_queries += alter_query
                        print(f"Prepared to modify column `{column.name}` to VARCHAR(20) in table `{member_table_name}`.")
                
                # 누적된 쿼리 실행
                if alter_queries:
                    conn.execute(text(alter_queries))
                    print(f"Executed all prepared queries.")
                
    except OperationalError as e:
        print(f"An error occurred: {e}")