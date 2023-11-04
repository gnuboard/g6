from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
from models import Base
target_metadata = Base.metadata

# Alembic 설정 객체입니다.
config = context.config

# Alembic이 `alembic.ini` 파일을 설정할 때 로깅 설정을 가져옵니다.
fileConfig(config.config_file_name)

# 모델의 MetaData 객체를 정의합니다.
target_metadata = Base.metadata

# 데이터베이스 URL을 설정합니다.
config.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL', ''))



