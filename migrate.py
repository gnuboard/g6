import os
import sqlalchemy
from sqlalchemy.exc import OperationalError
from datetime import datetime
import argparse

mysql_host = "localhost"
mysql_port = 3306
mysql_user = "root"
mysql_password = "ahffk"
mysql_db = "gnu6"

DATABASE_URL = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"  # pymysql을 사용합니다.

engine = sqlalchemy.create_engine(DATABASE_URL)

def log_history(message):
    with open("./migrations/history.txt", "a") as file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(f"{timestamp}: {message}\n")

def get_current_version():
    with open("./migrations/version.txt", "r") as file:
        version_str = file.read().strip()
        if version_str:
            try:
                return int(version_str)
            except ValueError:
                print(f"Warning: Invalid version number '{version_str}' in version.txt. Using 0 as default.")
                return 0
        else:
            print("Warning: Empty version.txt. Using 0 as default version.")
            return 0

def update_version(version):
    with open("./migrations/version.txt", "w") as file:
        file.write(str(version))

def apply_migrations(rebuilding=0):
    if rebuilding == 1:
        log_history(f"Rebuilding : {rebuilding}")
    
    current_version = get_current_version()
    migration_files = sorted(os.listdir("./migrations/versions"))
    
    for file in migration_files:
        version = int(file.split("_")[0])
        
        if version > current_version or rebuilding == 1:
            with open(f"./migrations/versions/{file}") as f:
                sql_commands = f.read().split(";")
                
                for command in sql_commands:
                    if command.strip():
                        try:
                            engine.execute(command)
                            log_history(f"Applied migration {file}: {command}")
                        except OperationalError as e:
                            if "Duplicate column name" in str(e):
                                log_history(f"Warning: {e}. Migration {file} skipped.")
                            else:
                                log_history(f"Error: {e}. Migration {file} failed.")
                                raise e
                                                    
            update_version(version)
            
# 커맨드 라인 인자 파싱
parser = argparse.ArgumentParser(description='Apply database migrations.')
parser.add_argument('--rebuilding', type=int, default=0, help='Reapply all migrations if set to 1.')

args = parser.parse_args()

# 마이그레이션 적용
# rebuilding = 1 : 마이그레이션을 다시 적용합니다.
apply_migrations(rebuilding=args.rebuilding)