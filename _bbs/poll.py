from common import *
from database import get_db
from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from models import Poll, PollEtc

from jinja2.ext import loopcontrols

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["now"] = now
templates.env.globals['getattr'] = getattr
templates.env.globals["generate_one_time_token"] = generate_one_time_token
templates.env.globals["generate_query_string"] = generate_query_string
templates.env.globals["get_member_level"] = get_member_level

# jinja2 에서 continue 문 사용하기 위한 확장 등록
templates.env.add_extension('jinja2.ext.loopcontrols')


@router.post("/update/{po_id}")
def poll_update(request: Request, po_id: int, token: str = Form(...), gb_poll: int = Form(...), db: Session = Depends(get_db)):
    """
    투표하기
    """

    poll = db.query(Poll).get(po_id)
    member = request.state.login_member
    member_level = get_member_level(request)

    if poll.po_level > 1 and member_level < poll.po_level:
        return templates.TemplateResponse(
            "alert.html", {"request": request, "errors": [f"권한 {poll.po_level} 이상의 회원만 투표하실 수 있습니다."]}
        )

    if validate_one_time_token(token, "update"):

        if request.client.host in poll.po_ips or (member and member.mb_id in poll.mb_ids):
            errors = [f"{poll.po_subject} 투표에 이미 참여하셨습니다."]
            return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": f"/poll/result/{po_id}"})

        if member:
            poll.mb_ids = ",".join([poll.mb_ids, member.mb_id]) if poll.mb_ids else member.mb_id
        else:
            poll.po_ips = ",".join([poll.po_ips, request.client.host]) if poll.po_ips else request.client.host
        
        # gb_poll로 전달받은 컬럼번호에 1 증가시킨다.
        poll.__setattr__(f"po_cnt{gb_poll}", poll.__getattribute__(f"po_cnt{gb_poll}") + 1)
        db.commit()
    else:
        return templates.TemplateResponse(
            "alert.html", {"request": request, "errors": ["잘못된 접근입니다."]}
        )

    return RedirectResponse(url=f"/poll/result/{po_id}", status_code=302)
      

@router.get("/result/{po_id}")
def poll_result(request: Request, po_id: int, db: Session = Depends(get_db)):
    """
    투표 결과
    """
    poll = db.query(Poll).get(po_id)
    member_level = get_member_level(request)

    if poll.po_level > 1 and member_level < poll.po_level:
        return templates.TemplateResponse(
            "alert.html", {"request": request, "errors": [f"권한 {poll.po_level} 이상의 회원만 결과를 보실 수 있습니다."]}
        )

    total_count = 0
    max_count = 0
    items = []
    for i in range(1, 10):
        if poll.__getattribute__(f"po_poll{i}"):
            po_cnt = poll.__getattribute__(f"po_cnt{i}")
            # 각 항목 제목/투표 수
            items.append({
                "subject": poll.__getattribute__(f"po_poll{i}"),
                "count": po_cnt
            })
            # 총 투표 수
            total_count += po_cnt
            # 최고 투표 수
            if max_count < po_cnt:
                max_count = po_cnt
    # 기타의견 목록
    etcs = db.query(PollEtc).filter(PollEtc.po_id == po_id).all()
    # 다른 투표결과 목록
    other_list = db.query(Poll).order_by(Poll.po_id.desc()).all()

    return templates.TemplateResponse(
        "bbs/poll_result.html", {
            "request": request, 
            "poll": poll, "items": items, "total_count": total_count, "max_count": max_count, 
            "etcs": etcs, "other_list": other_list
        }
    )


@router.post("/etc/{po_id}")
def poll_etc_update(request: Request,
                    po_id: int, 
                    token: str = Form(...),
                    pc_name: str = Form(...),
                    pc_idea: str = Form(...),
                    db: Session = Depends(get_db)):
    """
    기타의견 등록
    """
    poll = db.query(Poll).get(po_id)
    member = request.state.login_member
    member_level = get_member_level(request)

    if validate_one_time_token(token, "insert"):
        if poll.po_level > 1 and member_level < poll.po_level:
            return templates.TemplateResponse(
                "alert.html", {"request": request, "errors": [f"권한 {poll.po_level} 이상의 회원만 기타의견을 등록할 수 있습니다."]}
            )

        po_etc = PollEtc(po_id=po_id, pc_name=pc_name, pc_idea=pc_idea, mb_id=(member.mb_id if member else ''))
        db.add(po_etc)
        db.commit()
    else:
        return templates.TemplateResponse(
            "alert.html", {"request": request, "errors": ["잘못된 접근입니다."]}
        )

    return RedirectResponse(url=f"/poll/result/{po_id}", status_code=302)


@router.get("/etc/delete/{pc_id}")
def etc_delete(request: Request, pc_id: int, token: str, db: Session = Depends(get_db)):
    """
    기타의견 삭제
    """
    poll_etc = db.query(PollEtc).get(pc_id)
    po_id = poll_etc.po_id
    member = request.state.login_member
    member_level = get_member_level(request)

    if validate_one_time_token(token, "delete"):
        if poll_etc.mb_id != member.mb_id and not member_level == 10:
            return templates.TemplateResponse(
                "alert.html", {"request": request, "errors": ["작성자만 삭제할 수 있습니다."]}
            )

        db.delete(poll_etc)
        db.commit()
    else:
        return templates.TemplateResponse(
            "alert.html", {"request": request, "errors": ["잘못된 접근입니다."]}
        )

    return RedirectResponse(url=f"/poll/result/{po_id}", status_code=302)