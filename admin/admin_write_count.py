import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc, case, func, and_, or_, extract, text
from sqlalchemy.sql.expression import func, extract
from sqlalchemy.orm import Session
from database import get_db, engine
from lib.plugin.service import get_admin_plugin_menus
from models import *
from common import *
import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
from collections import defaultdict

router = APIRouter()
templates = Jinja2Templates(directory=[ADMIN_TEMPLATES_DIR, EDITOR_PATH])
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["domain_mail_host"] = domain_mail_host
templates.env.globals["editor_path"] = editor_path

WRITE_COUNT_MENU_KEY = "300820"

@router.get("/write_count")
async def write_count(request: Request, db: Session = Depends(get_db), 
        bo_table: str = Query(None, alias="bo_table"),
        period: str = Query(None, alias="period"),
        graph: str = Query(None, alias="graph")
        ):
    '''
    글, 댓글 현황 그래프
    '''
    request.session["menu_key"] = WRITE_COUNT_MENU_KEY

    period_array = {
        '오늘': ['시간', 0],
        '어제': ['시간', 0],
        '7일전': ['일', 7],
        '14일전': ['일', 14],
        '30일전': ['일', 30],
        '3개월전': ['주', 90],
        '6개월전': ['주', 180],
        '1년전': ['월', 365],
        '2년전': ['월', 365*2],
        '3년전': ['월', 365*3],
        '5년전': ['년', 365*5],
        '10년전': ['년', 365*10],
    }
    is_period = False
    for key, value in period_array.items():
        if key == period:
            is_period = True
            break
    if not is_period:
        period = '오늘'
    day = period_array[period][0]

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
        
    if period == '오늘':
        from_date = today
        to_date = from_date
    elif period == '어제':
        from_date = yesterday
        to_date = from_date
    elif period == '내일':
        from_date = datetime.now() + timedelta(days=2)
        to_date = from_date
    else:
        from_date = datetime.now() - timedelta(days=period_array[period][1])
        to_date = yesterday
    
    bo_table_array = db.query(Board.bo_table, Board.bo_subject).order_by(Board.bo_count_write.desc()).all()

    # Determine the current dialect
    dialect = db.bind.dialect.name

    x_data = []
    y_data = []
    x_label = ""
    
    if day == '시간':
        
        x_label = 'hours'
        if dialect == 'postgresql':
            hours_expr = func.to_char(BoardNew.bn_datetime, 'HH24')
        else:
            # 여기에 다른 방언에 대한 코드를 추가하세요
            hours_expr = func.substr(BoardNew.bn_datetime, 12, 2)  # 이는 일반적인 경우에 대한 예입니다.
        
        result = db.query(
            hours_expr.label(x_label), 
            func.sum(case((BoardNew.wr_id == BoardNew.wr_parent, 1), else_=0)).label('write_count'),
            func.sum(case((BoardNew.wr_id != BoardNew.wr_parent, 1), else_=0)).label('comment_count')
        ).filter(
            BoardNew.bn_datetime.between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()        

        for row in result:
            x_data.append(f"['{row.hours[:8]}',{row.write_count}]")
            y_data.append(f"['{row.hours[:8]}',{row.comment_count}]")
            
    elif day == '일':
        
        x_label = 'days'
        
        if dialect == 'mysql':
            date_expr = func.date_format(BoardNew.bn_datetime, '%Y-%m-%d')
        elif dialect == 'postgresql':
            date_expr = func.to_char(BoardNew.bn_datetime, 'YYYY-MM-DD')
        elif dialect == 'sqlite':
            date_expr = func.strftime('%Y-%m-%d', BoardNew.bn_datetime)
        else:
            raise Exception(f"Unsupported dialect: {dialect}")
                                    
        result = db.query(
            date_expr.label(x_label), 
            func.sum(case((BoardNew.wr_id == BoardNew.wr_parent, 1), else_=0)).label('write_count'),
            func.sum(case((BoardNew.wr_id != BoardNew.wr_parent, 1), else_=0)).label('comment_count')
        ).filter(
            BoardNew.bn_datetime.between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()
        
        for row in result:
            x_data.append(f"['{row.days[5:10]}',{row.write_count}]")
            y_data.append(f"['{row.days[5:10]}',{row.comment_count}]")
            
    elif day == '주':
        
        x_label = 'weeks'
        
        if dialect == 'mysql':
            week_expr = func.week(BoardNew.bn_datetime)
            concat_expr = func.concat(func.substr(BoardNew.bn_datetime, 1, 4), '-', week_expr)
        elif dialect == 'postgresql':
            week_expr = func.extract('week', BoardNew.bn_datetime)
            concat_expr = func.to_char(BoardNew.bn_datetime, 'IYYY-IW')  # Using ISO week numbering
        elif dialect == 'sqlite':
            week_expr = func.strftime('%W', BoardNew.bn_datetime)
            concat_expr = func.substr(BoardNew.bn_datetime, 1, 4) + '-' + week_expr
        else:
            raise Exception(f"Unsupported dialect: {dialect}")

        result = db.query(
            concat_expr.label(x_label), 
            func.sum(case((BoardNew.wr_id == BoardNew.wr_parent, 1), else_=0)).label('write_count'),
            func.sum(case((BoardNew.wr_id != BoardNew.wr_parent, 1), else_=0)).label('comment_count')
        ).filter(
            BoardNew.bn_datetime.between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()
        
        for row in result:
            lyear, lweek = row.weeks.split('-')
            date = (datetime.strptime(f"{lyear}W{str(lweek).zfill(2)}", "%YW%W") + timedelta(days=1)).strftime("%y-%m-%d")
            x_data.append(f"['{date}',{row.write_count}]")
            y_data.append(f"['{date}',{row.comment_count}]")
            
    elif day == '월':
        
        x_label = 'months'

        if dialect == 'mysql':
            month_expr = func.date_format(BoardNew.bn_datetime, '%Y-%m')
        elif dialect == 'postgresql':
            month_expr = func.to_char(BoardNew.bn_datetime, 'YYYY-MM')
        elif dialect == 'sqlite':
            month_expr = func.strftime('%Y-%m', BoardNew.bn_datetime)
        else:
            raise Exception(f"Unsupported dialect: {dialect}")

        result = db.query(
            month_expr.label(x_label), 
            func.sum(case((BoardNew.wr_id == BoardNew.wr_parent, 1), else_=0)).label('write_count'),
            func.sum(case((BoardNew.wr_id != BoardNew.wr_parent, 1), else_=0)).label('comment_count')
        ).filter(
            BoardNew.bn_datetime.between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()

        for row in result:
            x_data.append(f"['{row.months[2:7]}',{row.write_count}]")
            y_data.append(f"['{row.months[2:7]}',{row.comment_count}]")
            
    elif day == '년':
        
        x_label = 'years'
        
        if dialect == 'mysql':
            year_expr = func.year(BoardNew.bn_datetime)
        elif dialect == 'postgresql':
            year_expr = func.extract('year', BoardNew.bn_datetime).cast(Integer)
        elif dialect == 'sqlite':
            year_expr = func.strftime('%Y', BoardNew.bn_datetime)
        else:
            raise Exception(f"Unsupported dialect: {dialect}")

        result = db.query(
            year_expr.label('year'),
            func.sum(case((BoardNew.wr_id == BoardNew.wr_parent, 1), else_=0)).label('write_count'),
            func.sum(case((BoardNew.wr_id != BoardNew.wr_parent, 1), else_=0)).label('comment_count')
        ).filter(
            BoardNew.bn_datetime.between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by('year', BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()

        for row in result:
            x_data.append(f"['{row.years[:4]}',{row.write_count}]")
            y_data.append(f"['{row.years[:4]}',{row.comment_count}]")

    
    # 날짜별로 글과 댓글을 합침
    aggregated_data = defaultdict(lambda: [0, 0])
    for row in result:
        x, write_count, comment_count = row
        aggregated_data[x][0] += int(write_count)
        aggregated_data[x][1] += int(comment_count)
        
    # print(day)            
    # print(result)
    # print(x_label)            
    # print(aggregated_data)
            
    # 데이터 프레임 생성
    df = pd.DataFrame({
        x_label: aggregated_data.keys(),
        'write_count': [wc for wc, _ in aggregated_data.values()],
        'comment_count': [cc for _, cc in aggregated_data.values()]
    })
    
    # x_label에 따라 날짜/시간 형식 변경
    if x_label == "hours":
        df[x_label] = pd.to_datetime(df[x_label]).dt.strftime('%H:%M %p')
    elif x_label == "days":
        df[x_label] = pd.to_datetime(df[x_label]).dt.strftime('%y-%m-%d')
    elif x_label == "weeks":
        # df[x_label] = pd.to_datetime(df[x_label]).dt.strftime('Week %U, %Y')
        # 'weeks' 열의 값을 변환
        df[x_label] = df[x_label].apply(lambda x: datetime.strptime(x + '-1', "%Y-%W-%w"))
        # 변환된 날짜를 'Week %U, %Y' 형식으로 다시 형식화
        # df[x_label] = df[x_label].dt.strftime('Week %U, %Y')
        df[x_label] = pd.to_datetime(df[x_label], errors='coerce')
        df[x_label] = df[x_label].dt.strftime('Week %U, %Y')
    elif x_label == "months":
        df[x_label] = pd.to_datetime(df[x_label]).dt.strftime('%b, %Y')
    elif x_label == "years":
        df[x_label] = pd.to_datetime(df[x_label]).dt.strftime('%Y')
        
    if not (graph == 'bar' or graph == 'line' or graph == 'scatter'):
        graph = 'bar'
    
    # 그래프 생성 함수를 매핑합니다.
    graph_mapping = {
        'bar': px.bar,
        'line': px.line,
        'scatter': px.scatter,
    }
        
    # 그래프 생성
    #fig = px.bar(...)
    fig = graph_mapping[graph](df, x=x_label, y=['write_count', 'comment_count'], 
                labels={'value': 'Count', 'x': x_label, 'variable': 'Type'},
                title=f'글수(write_count), 댓글수(comment_count)')
    # 라인 굵기 변경
    # fig.update_traces(line=dict(width=100)) 
    
    # df = px.data.iris()  # 예제 데이터셋 로드
    # fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species", 
    #                  size='petal_length', hover_data=['petal_width'])    
    graph_html = fig.to_html()
    
    context = {
        "request": request,
        "bo_table_array": bo_table_array,
        "period_array": period_array,
        "bo_table": bo_table,
        "period": period,
        "graph": graph,
        # "templatg": template,
        "graph_html": graph_html,
    }
    return templates.TemplateResponse("write_count.html", context)
