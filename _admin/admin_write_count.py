import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc, and_, or_, func, extract, text
from sqlalchemy.orm import Session
from database import get_db, engine
from models import *
from common import *
from fastapi import FastAPI, HTTPException
import ssl
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from sse_starlette.sse import EventSourceResponse
import time
import asyncio
import matplotlib.pyplot as plt
from io import BytesIO
from string import Template
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
templates.env.globals["generate_one_time_token"] = generate_one_time_token
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
    
    # $period_array = array(
    #     '오늘'=>array('시간', 0),
    #     '어제'=>array('시간', 0),
    #     '7일전'=>array('일', 7),
    #     '14일전'=>array('일', 14),
    #     '30일전'=>array('일', 30),
    #     '3개월전'=>array('주', 90),
    #     '6개월전'=>array('주', 180),
    #     '1년전'=>array('월', 365),
    #     '2년전'=>array('월', 365*2),
    #     '3년전'=>array('월', 365*3),
    #     '5년전'=>array('년', 365*5),
    #     '10년전'=>array('년', 365*10),
    # );
    # $is_period = false;
    # foreach($period_array as $key=>$value) {
    #     if ($key == $period) {
    #         $is_period = true;
    #         break;
    #     }
    # }
    # if (!$is_period)
    #     $period = '오늘';
    # $day = $period_array[$period][0];
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
    
    # $today = date('Y-m-d', G5_SERVER_TIME);
    # $yesterday = date('Y-m-d', G5_SERVER_TIME - 86400);

    # if ($period == '오늘') {
    #     $from = $today;
    #     $to = $from;
    # } else if ($period == '어제') {
    #     $from = $yesterday;
    #     $to = $from;
    # } else if ($period == '내일') {
    #     $from = date('Y-m-d', G5_SERVER_TIME + (86400 * 2));
    #     $to = $from;
    # } else {
    #     $from = date('Y-m-d', G5_SERVER_TIME - (86400 * $period_array[$period][1]));
    #     $to = $yesterday;
    # }
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

    
    # foreach($period_array as $key=>$value) {
    #     echo "<option value=\"{$key}\"";
    #     if ($key == $period)
    #         echo " selected=\"selected\"";
    #     echo ">{$key}</option>\n";
    # }
    
    
    # $sql = " select bo_table, bo_subject from {$g5['board_table']} order by bo_count_write desc ";
    # $result = sql_query($sql);
    # for($i=0; $row=sql_fetch_array($result); $i++) {
    #     echo "<option value=\"{$row['bo_table']}\"";
    #     if ($bo_table == $row['bo_table'])
    #         echo ' selected="selected"';
    #     echo ">{$row['bo_subject']}</option>\n";
    # }
    
    bo_table_array = db.query(Board.bo_table, Board.bo_subject).order_by(Board.bo_count_write.desc()).all()
    
    
    # $sql_bo_table = '';
    # if ($bo_table)
    #     $sql_bo_table = "and bo_table = '$bo_table'";

    # $line1 = $line2 = array();

    # switch ($day) {
    #     case '시간' :
    #         $sql = " select substr(bn_datetime,6,8) as hours, sum(if(wr_id=wr_parent,1,0)) as wcount, sum(if(wr_id=wr_parent,0,1)) as ccount from {$g5['board_new_table']} where substr(bn_datetime,1,10) between '$from' and '$to' {$sql_bo_table} group by hours order by bn_datetime ";
    #         $result = sql_query($sql);
    #         for ($i=0; $row=sql_fetch_array($result); $i++) {
    #             // 월-일 시간
    #             $line1[] = "['".substr($row['hours'],0,8)."',".$row['wcount'].']';
    #             $line2[] = "['".substr($row['hours'],0,8)."',".$row['ccount'].']';
    #         }
    #         break;
    #     case '일' :
    #         $sql  = " select substr(bn_datetime,1,10) as days, sum(if(wr_id=wr_parent,1,0)) as wcount, sum(if(wr_id=wr_parent,0,1)) as ccount from {$g5['board_new_table']} where substr(bn_datetime,1,10) between '$from' and '$to' {$sql_bo_table} group by days order by bn_datetime ";
    #         $result = sql_query($sql);
    #         for ($i=0; $row=sql_fetch_array($result); $i++) {
    #             // 월-일
    #             $line1[] = "['".substr($row['days'],5,5)."',".$row['wcount'].']';
    #             $line2[] = "['".substr($row['days'],5,5)."',".$row['ccount'].']';
    #         }
    #         break;
    # case '주' :
    #     $sql  = " select concat(substr(bn_datetime,1,4), '-', weekofyear(bn_datetime)) as weeks, sum(if(wr_id=wr_parent,1,0)) as wcount, sum(if(wr_id=wr_parent,0,1)) as ccount from {$g5['board_new_table']} where substr(bn_datetime,1,10) between '$from' and '$to' {$sql_bo_table} group by weeks order by bn_datetime ";
    #     $result = sql_query($sql);
    #     for ($i=0; $row=sql_fetch_array($result); $i++) {
    #         // 올해의 몇주로 보여주면 바로 확인이 안되므로 주를 날짜로 바꾼다.
    #         // 년-월-일
    #         list($lyear, $lweek) = explode('-', $row['weeks']);
    #         $date = date('y-m-d', strtotime($lyear.'W'.str_pad($lweek, 2, '0', STR_PAD_LEFT)));
    #         $line1[] = "['".$date."',".$row['wcount'].']';
    #         $line2[] = "['".$date."',".$row['ccount'].']';
    #     }
    #     break;
    # case '월' :
    #     $sql  = " select substr(bn_datetime,1,7) as months, sum(if(wr_id=wr_parent,1,0)) as wcount, sum(if(wr_id=wr_parent,0,1)) as ccount from {$g5['board_new_table']} where substr(bn_datetime,1,10) between '$from' and '$to' {$sql_bo_table} group by months order by bn_datetime ";
    #     $result = sql_query($sql);
    #     for ($i=0; $row=sql_fetch_array($result); $i++) {
    #         // 년-월
    #         $line1[] = "['".substr($row['months'],2,5)."',".$row['wcount'].']';
    #         $line2[] = "['".substr($row['months'],2,5)."',".$row['ccount'].']';
    #     }
    #     break;
    # case '년' :
    #     $sql  = " select substr(bn_datetime,1,4) as years, sum(if(wr_id=wr_parent,1,0)) as wcount, sum(if(wr_id=wr_parent,0,1)) as ccount from {$g5['board_new_table']} where substr(bn_datetime,1,10) between '$from' and '$to' {$sql_bo_table} group by years order by bn_datetime ";
    #     $result = sql_query($sql);
    #     for ($i=0; $row=sql_fetch_array($result); $i++) {
    #         // 년(4자리)
    #         $line1[] = "['".substr($row['years'],0,4)."',".$row['wcount'].']';
    #         $line2[] = "['".substr($row['years'],0,4)."',".$row['ccount'].']';
    #     }
    #     break;
    # }
    x_data = []
    y_data = []
    x_label = ""
    if day == '시간':
        x_label = 'hours'
        result = db.query(
            func.substr(BoardNew.bn_datetime, 6, 8).label(x_label), 
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 1, 0)).label('write_count'),
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 0, 1)).label('comment_count')
        ).filter(
            func.substr(BoardNew.bn_datetime, 1, 10).between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()

        for row in result:
            x_data.append(f"['{row.hours[:8]}',{row.write_count}]")
            y_data.append(f"['{row.hours[:8]}',{row.comment_count}]")
    elif day == '일':
        x_label = 'days'
        result = db.query(
            func.substr(BoardNew.bn_datetime, 1, 10).label(x_label), 
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 1, 0)).label('write_count'),
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 0, 1)).label('comment_count')
        ).filter(
            func.substr(BoardNew.bn_datetime, 1, 10).between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()

        for row in result:
            x_data.append(f"['{row.days[5:10]}',{row.write_count}]")
            y_data.append(f"['{row.days[5:10]}',{row.comment_count}]")
    elif day == '주':
        x_label = 'weeks'
        result = db.query(
            func.concat(func.substr(BoardNew.bn_datetime, 1, 4), '-', func.weekofyear(BoardNew.bn_datetime)).label(x_label), 
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 1, 0)).label('write_count'),
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 0, 1)).label('comment_count')
        ).filter(
            func.substr(BoardNew.bn_datetime, 1, 10).between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()

        for row in result:
            lyear, lweek = row.weeks.split('-')
            date = (datetime.strptime(f"{lyear}W{str(lweek).zfill(2)}", "%YW%W") + timedelta(days=1)).strftime("%y-%m-%d")
            x_data.append(f"['{date}',{row.write_count}]")
            y_data.append(f"['{date}',{row.comment_count}]")
    elif day == '월':
        x_label = 'months'
        result = db.query(
            func.substr(BoardNew.bn_datetime, 1, 7).label(x_label), 
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 1, 0)).label('write_count'),
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 0, 1)).label('comment_count')
        ).filter(
            func.substr(BoardNew.bn_datetime, 1, 10).between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()

        for row in result:
            x_data.append(f"['{row.months[2:7]}',{row.write_count}]")
            y_data.append(f"['{row.months[2:7]}',{row.comment_count}]")
    elif day == '년':
        x_label = 'years'
        result = db.query(
            func.substr(BoardNew.bn_datetime, 1, 4).label(x_label), 
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 1, 0)).label('write_count'),
            func.sum(func.if_(BoardNew.wr_id == BoardNew.wr_parent, 0, 1)).label('comment_count')
        ).filter(
            func.substr(BoardNew.bn_datetime, 1, 10).between(from_date, to_date),
            or_(BoardNew.bo_table == bo_table, bo_table == '')
        ).group_by(x_label, BoardNew.bn_datetime).order_by(BoardNew.bn_datetime).all()

        for row in result:
            x_data.append(f"['{row.years[:4]}',{row.write_count}]")
            y_data.append(f"['{row.years[:4]}',{row.comment_count}]")

    print(x_label)            
    print(day)            
    print(result)
    
    # 날짜별로 글과 댓글을 합침
    aggregated_data = defaultdict(lambda: [0, 0])
    for row in result:
        x, write_count, comment_count = row
        aggregated_data[x][0] += int(write_count)
        aggregated_data[x][1] += int(comment_count)
        
    print(aggregated_data)
            
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
        df[x_label] = df[x_label].dt.strftime('Week %U, %Y')
    elif x_label == "months":
        df[x_label] = pd.to_datetime(df[x_label]).dt.strftime('%b, %Y')
    elif x_label == "years":
        df[x_label] = pd.to_datetime(df[x_label]).dt.strftime('%Y')

    # 그래프 생성
    fig = px.line(df, x=x_label, y=['write_count', 'comment_count'], 
                labels={'value': 'Count', 'x': x_label, 'variable': 'Type'},
                title=f'Line plot of {x_label} vs write_count and comment_count')
    
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
