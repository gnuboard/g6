
import sys
from sqlalchemy import MetaData, text
from sqlalchemy.exc import OperationalError

# database.py 가 상위 디렉토리에 있으므로, 상위 디렉토리를 sys.path 에 추가합니다.
sys.path.append('..')
from database import engine

config_table_name = 'g5_config'

metadata = MetaData()

# 테이블 구조를 반영
metadata.reflect(bind=engine)

# g5_config 테이블이 있는지 확인
table = metadata.tables.get(config_table_name)

if table is not None:
    try:
        # cf_id 열이 있는지 확인하고, 없다면 추가
        if 'cf_id' not in table.columns.keys():
            with engine.connect() as conn:
                # 명시적 트랜잭션 시작
                with conn.begin():
                    # text() 구조를 사용하여 쿼리 실행
                    conn.execute(text(f"ALTER TABLE `{config_table_name}` ADD `cf_id` INT NOT NULL DEFAULT 1 FIRST, ADD PRIMARY KEY (`cf_id`);"))
                    print(f"{config_table_name} 테이블에 cf_id 주키(Primary Key)를 추가했습니다.")
        else:
            print(f"{config_table_name} 테이블에 cf_id 주키(Primary Key)가 이미 존재합니다.")
                
    except OperationalError as e:
        print(f"오류가 발생했습니다: {e}")
