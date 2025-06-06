import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from lib.common import delete_old_records
from core.models import Base, Config, Member
from core.database import DBConnect


def setup_module(module):
    # initialize in-memory database
    engine = DBConnect().engine
    Base.metadata.create_all(bind=engine)


def get_session():
    return DBConnect().sessionLocal()


def test_leave_member_deletion(caplog):
    db = get_session()
    # insert config
    config = Config(cf_id=1, cf_leave_day=7)
    db.add(config)
    old_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
    new_date = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')
    db.add_all([
        Member(mb_id='olduser', mb_leave_date=old_date),
        Member(mb_id='newuser', mb_leave_date=new_date),
    ])
    db.commit()
    db.close()

    with caplog.at_level(logging.INFO):
        delete_old_records()

    db = get_session()
    remaining = {m.mb_id for m in db.scalars(select(Member)).all()}
    assert 'olduser' not in remaining
    assert 'newuser' in remaining
    assert 'olduser' in caplog.text
    db.close()
