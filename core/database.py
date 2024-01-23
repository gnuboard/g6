from dotenv import dotenv_values, load_dotenv
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from typing_extensions import Annotated


class DBSetting:
    """
    데이터베이스 설정 클래스
    - 매번 설정이 불러와지는 문제점 해결해야함..
    """

    _table_prefix: Annotated[str, ""]
    _db_engine: Annotated[str, ""]
    _user: Annotated[str, ""]
    _password: Annotated[str, ""]
    _host: Annotated[str, ""]
    _port: Annotated[int, 0]
    _name: Annotated[str, ""]
    _url: Annotated[str, ""]

    supported_engines = {
        "mysql": "mysql+pymysql://",
        "postgresql": "postgresql://",
        "sqlite": "sqlite:///sqlite3.db"
    }

    def __init__(self) -> None:
        self.set_connect_infomation()
        self.create_url()

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, url: str) -> None:
        self._url = url

    @property
    def table_prefix(self) -> str:
        return self._table_prefix

    @table_prefix.setter
    def table_prefix(self, prefix: str) -> None:
        self._table_prefix = prefix

    def set_connect_infomation(self) -> None:
        load_dotenv()
        env_values = dotenv_values()
        port = env_values.get("DB_PORT", "3306")

        self._table_prefix = env_values.get("DB_TABLE_PREFIX", "")
        self._db_engine = env_values.get("DB_ENGINE", "").lower()
        self._user = env_values.get("DB_USER")
        self._password = env_values.get("DB_PASSWORD")
        self._host = env_values.get("DB_HOST")
        self._port = int(port) if port.isdigit() else 3306
        self._db_name = env_values.get("DB_NAME")

    def create_url(self) -> None:
        url = None
        prefix = self.supported_engines.get(self._db_engine)
        if prefix:
            if self._db_engine == "sqlite":
                url = prefix
            else:
                url = prefix + f"{self._user}:{self._password}@{self._host}:{self._port}/{self._db_name}"
        self._url = url


class DBConnect(DBSetting):
    """
    데이터베이스 연결 클래스
    - 데이터베이스 연결을 위한 engine 및 session 생성
    - 싱글톤 패턴 구현 (단일 engine 및 session 유지)
    """
    _engine: Annotated[Engine, None]
    _sessionLocal: Annotated[sessionmaker[Session], None]
    _instance: Annotated['DBConnect', None] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        cls = type(self)
        if not hasattr(cls, "_init"):
            cls._init = True

    @property
    def engine(self) -> Engine:
        return self._engine

    @engine.setter
    def engine(self, engine: Engine) -> None:
        self._engine = engine

    @property
    def sessionLocal(self) -> sessionmaker[Session]:
        return self._sessionLocal

    @sessionLocal.setter
    def sessionLocal(self, sessionLocal: sessionmaker[Session]) -> None:
        self._sessionLocal = sessionLocal

    def create_engine(self) -> None:
        self.engine = create_engine(
            self._url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=40,
            pool_timeout=60
        )

        self.create_sessionmaker()

    def create_sessionmaker(self) -> None:
        self._sessionLocal = sessionmaker(autocommit=False, autoflush=False,
                                          bind=self.engine, expire_on_commit=True)


db_connect = DBConnect()
# 데이터베이스 url이 없을 경우, 설치를 위해 임시로 메모리 DB 사용
db_connect.url = db_connect.url or "sqlite://"
db_connect.create_engine()


# 데이터베이스 세션을 가져오는 의존성 함수
async def get_db() -> Session:
    db = DBConnect().sessionLocal()
    try:
        yield db
    finally:
        db.close()


# Annotated를 사용하여 의존성 주입
db_session = Annotated[Session, Depends(get_db)]
