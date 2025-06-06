import pytest
from sqlalchemy import select, func, extract
from sqlalchemy.dialects import mysql, postgresql, sqlite
from core.models import Visit


def build_hour_query(dialect_name):
    query = select()
    if dialect_name == 'mysql':
        query = query.add_columns(func.hour(Visit.vi_time).label('hour'))
    elif dialect_name == 'postgresql':
        query = query.add_columns(extract('hour', Visit.vi_time).label('hour'))
    elif dialect_name == 'sqlite':
        query = query.add_columns(func.strftime('%H', Visit.vi_time).label('hour'))
    return query.add_columns(func.count().label('hour_count')).group_by('hour')


def build_weekday_query(dialect_name):
    query = select()
    if dialect_name == 'mysql':
        query = query.add_columns(func.dayofweek(Visit.vi_date).label('dow'))
    elif dialect_name == 'postgresql':
        query = query.add_columns(extract('dow', Visit.vi_date).label('dow'))
    elif dialect_name == 'sqlite':
        query = query.add_columns(func.strftime('%w', Visit.vi_date).label('dow'))
    return query.add_columns(func.count().label('dow_count')).group_by('dow')


def test_hour_query_mysql():
    sql = str(build_hour_query('mysql').compile(dialect=mysql.dialect()))
    assert 'hour(' in sql.lower()


def test_hour_query_postgresql():
    sql = str(build_hour_query('postgresql').compile(dialect=postgresql.dialect()))
    assert 'extract(hour' in sql.lower()


def test_hour_query_sqlite():
    sql = str(build_hour_query('sqlite').compile(dialect=sqlite.dialect()))
    assert 'strftime' in sql


def test_weekday_query_mysql():
    sql = str(build_weekday_query('mysql').compile(dialect=mysql.dialect()))
    assert 'dayofweek' in sql.lower()


def test_weekday_query_postgresql():
    sql = str(build_weekday_query('postgresql').compile(dialect=postgresql.dialect()))
    assert 'extract(dow' in sql.lower()


def test_weekday_query_sqlite():
    sql = str(build_weekday_query('sqlite').compile(dialect=sqlite.dialect()))
    assert 'strftime' in sql

