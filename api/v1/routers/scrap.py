from datetime import datetime
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy import exists, func, select, update

from bbs.scrap import get_total_scrap_count
from core.database import db_session
from core.exception import AlertException
from core.models import Board, Member, Scrap, WriteBaseModel
from lib.board_lib import BoardConfig, is_write_delay, insert_board_new, set_write_delay
from lib.common import FileCache, dynamic_create_write_table
from lib.point import insert_point

from api.v1.models import responses
from api.v1.dependencies.member import get_current_member
from api.v1.models.scrap import CreateScrapModel, ResponseScrapModel

router = APIRouter()

"""함수(임시)"""
def get_board(db: db_session, bo_table: Annotated[str, Path(...)]):
    """게시판 존재 여부 검사 & 반환"""
    board = db.get(Board, bo_table)
    if not board:
        raise HTTPException(status_code=404, detail=f"{bo_table} : 존재하지 않는 게시판입니다.")
    return board


def get_write(db: db_session, 
              bo_table: Annotated[str, Path(...)],
              wr_id: Annotated[int, Path(...)]):
    """게시글 존재 여부 검사 & 반환"""
    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise HTTPException(status_code=404, detail=f"{wr_id} : 존재하지 않는 게시글입니다.")
    return write

""" Router """

@router.get("/scraps",
            summary="회원 스크랩 목록 조회",
            response_model=List[ResponseScrapModel],
            responses={**responses})
async def read_member_scraps(
    db: db_session,
    current_member: Annotated[Member, Depends(get_current_member)],
):
    """회원 스크랩 목록을 조회합니다."""
    scraps = current_member.scraps.all()
    for scrap in scraps:
        write_model = dynamic_create_write_table(table_name=scrap.bo_table)
        write = db.get(write_model, scrap.wr_id)

        scrap.wr_subject = write.wr_subject
        scrap.bo_subject = scrap.board.bo_subject

    return scraps

# TODO: 댓글 등록 프로세스를 템플릿 부분과 통합해야함 
@router.post("/scraps/{bo_table}/{wr_id}",
             summary="회원 스크랩 등록",
             responses={**responses})
async def create_member_scrap(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    data: Annotated[CreateScrapModel, Depends()]
):
    """회원 스크랩을 등록합니다."""
    bo_table = board.bo_table
    wr_id = write.wr_id
    board_config = BoardConfig(request, board)
    write_model = dynamic_create_write_table(bo_table)

    exists_scrap = db.scalar(
        exists(Scrap).where(
            Scrap.mb_id == member.mb_id,
            Scrap.bo_table == bo_table,
            Scrap.wr_id == wr_id
        ).select()
    )
    if exists_scrap:
        raise AlertException("이미 스크랩하신 글 입니다.", 302, request.url_for('scrap_list'))
    
    # 댓글 추가
    if data.wr_content and board_config.is_comment_level():
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
            wr_content=data.wr_content,
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
        insert_board_new(board.bo_table, comment)

        # 포인트 부여
        insert_point(request, member.mb_id, board.bo_comment_point, 
                     f"{board.bo_subject} {write.wr_id}-{comment.wr_id} 댓글쓰기(스크랩)", board.bo_table, comment.wr_id,
                     '댓글')
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
        .values(mb_scrap_cnt=get_total_scrap_count(member.mb_id) + 1)
    )
    db.commit()

    # 최신글 캐시 삭제
    FileCache().delete_prefix(f'latest-{bo_table}')

    return {"detail": "스크랩을 추가하였습니다."}


@router.delete("/scraps/{ms_id}",
                summary="회원 스크랩 삭제",
                responses={**responses})
async def delete_member_scrap(
    db: db_session,
    ms_id: Annotated[int, Path(title="스크랩 아이디")],
    current_member: Annotated[Member, Depends(get_current_member)],
):
    """회원 스크랩을 삭제합니다."""
    scrap = current_member.scraps.filter_by(ms_id=ms_id).first()
    if scrap is None:
        raise HTTPException(status_code=404, detail="스크랩을 찾을 수 없습니다.")
    if scrap.mb_id != current_member.mb_id:
        raise HTTPException(status_code=403, detail="본인의 스크랩만 삭제할 수 있습니다.")

    db.delete(scrap)
    db.commit()
    db.refresh(current_member)

    return {"detail": "스크랩을 삭제하였습니다."}