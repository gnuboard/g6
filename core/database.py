from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from typing_extensions import Annotated

from core.settings import settings


class MySQLCharsetMixin:
    """ MySQL의 기본 charset을 설정하는 Mixin 클래스 """

    @declared_attr.directive
    def __table_args__(cls):
        return {'mysql_charset': DBConnect().charset}


class DBSetting:
    """
    데이터베이스 설정 클래스
    """

    _table_prefix: Annotated[str, ""]
    _db_engine: Annotated[str, ""]
    _user: Annotated[str, ""]
    _password: Annotated[str, ""]
    _host: Annotated[str, ""]
    _port: Annotated[int, 0]
    _name: Annotated[str, ""]
    _url: Annotated[str, ""]
    _charset: Annotated[str, ""]
    _instance: Annotated['DBSetting', None] = None
    _setting_init: Annotated[bool, False]

    supported_engines = {
        "mysql": "mysql+pymysql",
        "postgresql": "postgresql",
        "sqlite": "sqlite:///sqlite3.db"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        if not hasattr(DBSetting, "_setting_init"):
            DBSetting._setting_init = True
            self.set_connect_infomation()
            self.create_url()

    @property
    def charset(self) -> str:
        return self._charset

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
        self._table_prefix = settings.DB_TABLE_PREFIX
        self._db_engine = settings.DB_ENGINE
        self._user = settings.DB_USER
        self._password = settings.DB_PASSWORD
        self._host = settings.DB_HOST
        self._port = settings.DB_PORT
        self._db_name = settings.DB_NAME
        self._charset = settings.DB_CHARSET

    def create_url(self) -> None:
        url = None
        if db_driver := self.supported_engines.get(self._db_engine):
            if self._db_engine == "sqlite":
                url = db_driver
            else:
                query_option = {}
                if self._db_engine == "mysql":
                    query_option = {"charset": self._charset}

                elif self._db_engine == "postgresql":
                    if self._charset == "utf8mb4" or self._charset == "utf8":
                        # pycopg 드라이버 인코딩 설정 utf8 을 사용
                        query_option = {"client_encoding": 'utf8'}
                    else:
                        query_option = {"client_encoding": self._charset}
                url = URL(
                    drivername=db_driver,
                    username=self._user,
                    password=self._password,
                    host=self._host,
                    port=self._port,
                    database=self._db_name,
                    query=query_option,
                )
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
async def get_db() -> AsyncGenerator[Session, None]:
    db = DBConnect().sessionLocal()
    try:
        yield db
    finally:
        db.close()


# Annotated를 사용하여 의존성 주입
db_session = Annotated[Session, Depends(get_db)]
