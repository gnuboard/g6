from datetime import datetime
from sqlalchemy import MetaData, Table

from core.database import db_session



class G5Compatibility:
    """
    gnuboard5와의 호환성을 위한 메소드를 담은 클래스입니다.
    """

    def __init__(self, db: db_session):
        self.db = db

    def get_wr_last_now(self, table_name):
        """
        write_free, write_notice 등의 테이블의 wr_last 필드에 들어갈 현재 시간을 반환합니다.
        """
        metadata = MetaData()
        metadata.reflect(bind=self.db.bind)
        table = Table(table_name, metadata, autoload_with=self.db.bind)
        wr_last_col = table.columns.get('wr_last')
        wr_last_type = str(wr_last_col.type)
        now = datetime.now()
        if wr_last_type == 'VARCHAR(19)':
            now = now.strftime('%Y-%m-%d %H:%M:%S')
        return now