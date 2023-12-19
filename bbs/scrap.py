from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import literal
from sqlalchemy.orm import aliased

from lib.board_lib import *
from lib.common import *
from common.database import db_session
from common.models import Scrap

router = APIRouter()
templates = UserTemplates()
templates.env.filters["datetime_format"] = datetime_format


@router.get("/scrap_popin/{bo_table}/{wr_id}")
async def scrap_form(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    wr_id: int = Path(...),
):
    """
    스크랩 등록 폼(팝업창)
    """
    member = request.state.login_member
    if not member:
        raise AlertCloseException("로그인 후 이용 가능합니다.", 403)
    
    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise AlertCloseException("존재하지 않는 글 입니다.", 404)

    exists_scrap = db.scalar(
        exists(Scrap)
        .where(Scrap.mb_id == member.mb_id, Scrap.bo_table == bo_table, Scrap.wr_id == wr_id)
        .select()
    )
    if exists_scrap:
        raise AlertException("이미 스크랩하신 글 입니다.", 302, request.url_for('scrap_list'))
    
    context = {
        "request": request,
        "bo_table": bo_table,
        "write": write,
    }
    return templates.TemplateResponse("bbs/scrap_popin.html", context)
    

@router.post("/scrap_popin_update/{bo_table}/{wr_id}", dependencies=[Depends(validate_token)])
async def scrap_form_update(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    wr_content: str = Form(None),
):
    """
    스크랩 등록
    """
    member: Member = request.state.login_member
    if not member:
        raise AlertCloseException("로그인 후 이용 가능합니다.", 403)
    
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertCloseException("존재하지 않는 게시판 입니다.", 404)
    
    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise AlertCloseException("존재하지 않는 글 입니다.", 404)
    
    exists_scrap = db.scalar(
        exists(Scrap)
        .where(Scrap.mb_id == member.mb_id, Scrap.bo_table == bo_table, Scrap.wr_id == wr_id)
        .select()
    )
    if exists_scrap:
        raise AlertException("이미 스크랩하신 글 입니다.", 302, request.url_for('scrap_list'))
    
    # 댓글 추가
    if wr_content and board_config.is_comment_level():
        # 글쓰기 간격 검증
        if not is_write_delay(request):
            raise AlertException("너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.", 400)

        max_comment = db.scalar(
            select(func.max(write_model.wr_comment).label('max_comment'))
            .where(write_model.wr_parent == wr_id, write_model.wr_is_comment == 1)
        )
        # TODO: 게시글/댓글을 등록하는 공용함수를 만들어서 사용하도록 수정
        comment_model = dynamic_create_write_table(bo_table)
        comment = comment_model(
            mb_id=member.mb_id,
            wr_content=wr_content,
            ca_name=write.ca_name,
            wr_option="",
            wr_num=write.wr_num,
            wr_reply="",
            wr_parent=wr_id,
            wr_comment=max_comment + 1 if max_comment else 1,
            wr_is_comment=1,
            wr_name=board_config.set_wr_name(member),
            wr_password=member.mb_password,
            wr_email=member.mb_email,
            wr_homepage=member.mb_homepage,
            wr_datetime=datetime.now(),
            wr_ip=request.client.host,
        )
        db.add(comment)
        db.commit()

        # 글 작성 시간 기록
        set_write_delay(request)

        # 게시판&스크랩 글에 댓글 수 증가
        board.bo_count_comment += 1
        write.wr_comment += 1

        # 새글 테이블에 추가
        insert_board_new(bo_table, comment)

        # 포인트 부여
        insert_point(request, member.mb_id, board.bo_comment_point, f"{board.bo_subject} {write.wr_id}-{comment.wr_id} 댓글쓰기(스크랩)", board.bo_table, comment.wr_id, '댓글')

        db.commit()

    # 스크랩 추가
    scrap = Scrap(
        mb_id=member.mb_id,
        bo_table=bo_table,
        wr_id=wr_id
    )
    db.add(scrap)
    # 회원 테이블 스크랩 카운트 증가
    db.execute(
        update(Member)
        .where(Member.mb_id == member.mb_id)
        .values(mb_scrap_cnt=get_scrap_totals(member.mb_id) + 1)
    )
    db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')
    
    return RedirectResponse(request.url_for('scrap_list'), 302)


@router.get("/scrap")
async def scrap_list(
    request: Request,
    db: db_session,
    current_page: int = Query(default=1, alias="page")
):
    """
    스크랩 목록
    """
    login_member = request.state.login_member
    if not login_member:
        raise AlertCloseException("로그인 후 이용 가능합니다.", 403)
    member = db.scalar(select(Member).where(Member.mb_id == login_member.mb_id))

    # 스크랩 목록 조회
    query = member.scraps.order_by(desc(Scrap.ms_id))

    # 페이징 처리
    records_per_page = request.state.config.cf_page_rows
    total_records = query.count()
    offset = (current_page - 1) * records_per_page
    scraps: List["Scrap"] = db.scalars(
        query.offset(offset).limit(records_per_page)
    ).all()
    
    for scrap in scraps:
        # 스크랩 정보
        scrap.num = total_records - offset - (scraps.index(scrap))
        scrap.bo_subject = scrap.board.bo_subject or "[게시판 없음]"
        # 게시글 정보
        write_model = dynamic_create_write_table(scrap.bo_table)
        write = db.get(write_model, scrap.wr_id)
        scrap.subject = write.wr_subject or write.wr_content[:100] if write else "[글 없음]"

    context = {
        "request": request,
        "scraps": scraps,
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("bbs/scrap_list.html", context)


@router.get("/scrap_delete/{ms_id}", dependencies=[Depends(validate_token)])
async def scrap_delete(
    request: Request,
    db: db_session, 
    ms_id: int = Path(...)
):
    """
    스크랩 삭제
    """
    member: Member = request.state.login_member
    if not member:
        raise AlertCloseException(status_code=403, detail="로그인 후 이용 가능합니다.")
    
    scrap = db.get(Scrap, ms_id)
    if not scrap:
        raise AlertException("스크랩이 존재하지 않습니다.", 404)
    if scrap.mb_id != member.mb_id:
        raise AlertException("본인의 스크랩만 삭제 가능합니다.", 403)

    # 스크랩 삭제
    db.delete(scrap)
    # 회원 테이블 스크랩 카운트 감소
    db.execute(
        update(Member)
        .where(Member.mb_id == member.mb_id)
        .values(mb_scrap_cnt=get_scrap_totals(member.mb_id) - 1)
    )
    db.commit()

    query_params = dict(request.query_params)
    query_params.pop("token", None)
    query_params = "&".join([f"{key}={value}" for key, value in query_params.items()])
    query_params = query_params.replace("&amp;", "&")
    query_string = "?" + query_params if query_params else ""
    return_url = request.url_for('scrap_list').path + query_string

    return RedirectResponse(url=return_url, status_code=302)


def get_scrap_totals(mb_id: str) -> int:
    """회원의 전체 스크랩 수를 구한다.

    Args:
        mb_id (str): 회원 아이디
    
    Returns:
        int: 스크랩 수
    """
    db = SessionLocal()
    count = db.scalar(
        select(func.count(Scrap.ms_id))
        .where(Scrap.mb_id == mb_id)
    )
    db.close()

    return count