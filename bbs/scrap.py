from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import literal
from sqlalchemy.orm import aliased, Session

from lib.board_lib import *
from lib.common import *
from common.database import get_db
from common.models import Scrap

router = APIRouter()
templates = MyTemplates(directory=TEMPLATES_DIR)
templates.env.filters["datetime_format"] = datetime_format


@router.get("/scrap_popin/{bo_table}/{wr_id}")
def scrap_form(request: Request, db: Session = Depends(get_db),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
):
    """
    스크랩 등록 폼(팝업창)
    """
    member = request.state.login_member
    if not member:
        raise AlertCloseException("로그인 후 이용 가능합니다.", 403)
    
    models_write = dynamic_create_write_table(bo_table)
    write = db.query(models_write).filter(models_write.wr_id == wr_id).first()
    if not write:
        raise AlertCloseException("존재하지 않는 글 입니다.", 404)
    
    query = db.query(Scrap).filter(Scrap.mb_id == member.mb_id, Scrap.bo_table == bo_table, Scrap.wr_id == wr_id)
    exists_scrap = db.query(literal(True)).filter(query.exists()).scalar()
    if exists_scrap:
        raise AlertException("이미 스크랩하신 글 입니다.", 302, request.url_for('scrap_list'))
    
    context = {
        "request": request,
        "bo_table": bo_table,
        "write": write,
    }
    return templates.TemplateResponse("bbs/scrap_popin.html", context)
    

@router.post("/scrap_popin_update/{bo_table}/{wr_id}")
def scrap_form_update(request: Request, db: Session = Depends(get_db),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    wr_content: str = Form(None),
    token: str = Form(...),
):
    """
    스크랩 등록
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    member = request.state.login_member
    if not member:
        raise AlertCloseException("로그인 후 이용 가능합니다.", 403)
    
    board = db.query(Board).filter(Board.bo_table == bo_table).first()
    board_config = BoardConfig(request, board)
    if not board:
        raise AlertCloseException("존재하지 않는 게시판 입니다.", 404)
    
    models_write = dynamic_create_write_table(bo_table)
    write = db.query(models_write).filter(models_write.wr_id == wr_id).first()
    if not write:
        raise AlertCloseException("존재하지 않는 글 입니다.", 404)
    
    query = db.query(Scrap).filter(Scrap.mb_id == member.mb_id, Scrap.bo_table == bo_table, Scrap.wr_id == wr_id)
    exists_scrap = db.query(literal(True)).filter(query.exists()).scalar()
    if exists_scrap:
        raise AlertException("이미 스크랩하신 글 입니다.", 302, request.url_for('scrap_list'))
    
    # 댓글 추가
    if wr_content and board_config.is_comment_level():
        # 글쓰기 간격 검증
        if not is_write_delay(request):
            raise AlertException("너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.", 400)

        max_comment = db.query(func.max(models_write.wr_comment).label('max_comment')).filter(
            models_write.wr_parent == wr_id,
            models_write.wr_is_comment == 1
        ).first()

        # TODO: 게시글/댓글을 등록하는 공용함수를 만들어서 사용하도록 수정
        models_comment = dynamic_create_write_table(bo_table)
        comment = models_comment(
            mb_id=member.mb_id,
            wr_content=wr_content,
            ca_name=write.ca_name,
            wr_option="",
            wr_num=write.wr_num,
            wr_reply="",
            wr_parent=wr_id,
            wr_comment=max_comment.max_comment + 1 if max_comment.max_comment else 1,
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
    member_object = db.query(Member).filter(Member.mb_id == member.mb_id).first()
    member_object.mb_scrap_cnt = get_scrap_totals(member.mb_id) + 1
    db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')
    
    return RedirectResponse(request.url_for('scrap_list'), 302)


# TODO: 연관관계로 ORM 수정 => (쿼리요청 및 코드량 감소)
@router.get("/scrap")
def scrap_list(request: Request, db: Session = Depends(get_db),
    current_page: int = Query(default=1, alias="page")
):
    """
    스크랩 목록
    """
    member = request.state.login_member
    if not member:
        raise AlertCloseException("로그인 후 이용 가능합니다.", 403)

    # 스크랩 목록 조회
    scrap = aliased(Scrap)
    board = aliased(Board)
    query = db.query(scrap, board).outerjoin(
        board, scrap.bo_table == board.bo_table
    ).filter(scrap.mb_id == member.mb_id).order_by(desc(scrap.ms_id))

    # 페이징 처리
    records_per_page = request.state.config.cf_page_rows
    total_records = query.count()
    offset = (current_page - 1) * records_per_page
    results = query.offset(offset).limit(records_per_page).all()
    
    for result in results:
        scrap = result[0]
        bo_subject = result[1]
        # 스크랩 정보
        scrap.num = total_records - offset - (results.index(result))
        scrap.bo_subject = bo_subject or "[게시판 없음]"
        # 게시글 정보
        write_model = dynamic_create_write_table(scrap.bo_table)
        write = db.query(write_model).filter_by(wr_id = scrap.wr_id).first()
        scrap.subject = write.wr_subject or write.wr_content[:100] if write else "[글 없음]"

    context = {
        "request": request,
        "results": results,
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("bbs/scrap_list.html", context)


@router.get("/scrap_delete/{ms_id}")
def scrap_delete(request: Request, db: Session = Depends(get_db), 
    ms_id: int = Path(...),
    token: str = Query(...),
    page: int = Query(default=1)
):
    """
    스크랩 삭제
    """
    return_url = request.url_for('scrap_list').path + f"?page={page}"

    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)
    
    member = request.state.login_member
    if not member:
        raise AlertCloseException(status_code=403, detail="로그인 후 이용 가능합니다.")
    
    scrap = db.query(Scrap).get(ms_id)
    if not scrap:
        raise AlertException("스크랩이 존재하지 않습니다.", 404, return_url)
    if scrap.mb_id != member.mb_id:
        raise AlertException("본인의 스크랩만 삭제 가능합니다.", 403, return_url)

    # 스크랩 삭제
    db.delete(scrap)
    # 회원 테이블 스크랩 카운트 감소
    member_object = db.query(Member).filter(Member.mb_id == member.mb_id).first()
    member_object.mb_scrap_cnt = get_scrap_totals(member.mb_id) - 1
    db.commit()

    return RedirectResponse(url=return_url, status_code=302)


def get_scrap_totals(mb_id: str) -> int:
    """회원의 전체 스크랩 수를 구한다.

    Args:
        mb_id (str): 회원 아이디
    
    Returns:
        int: 스크랩 수
    """
    db = SessionLocal()
    return db.query(Scrap).filter(Scrap.mb_id == mb_id).count()