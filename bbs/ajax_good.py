from fastapi import APIRouter, Form, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy import insert, select

from core.database import db_session
from core.models import Board, BoardGood
from lib.common import *
from lib.token import check_token

router = APIRouter()


@router.post("/good/{bo_table}/{wr_id}/{type}")
async def ajax_good(
    request: Request,
    db: db_session,
    token: str = Form(...),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    type: str = Path(...)
):
    """
    게시글 좋아요/싫어요 처리
    """
    result = {"status": "success", "message": "", "good": 0, "nogood": 0}
    type_attr = f"wr_{type}"  # 선택한 타입
    type_attr_rev = "wr_good" if type == "nogood" else "wr_nogood"  # 반대 타입
    type_str = "추천" if type == "good" else "비추천"

    # 회원만 가능
    member = request.state.login_member
    if not member:
        return JSONResponse({"status": "fail", "message": "로그인 후 이용 가능합니다."}, 403)

    # 토큰 검증
    if not check_token(request, token):
        return JSONResponse({"status": "fail", "message": "토큰이 유효하지 않습니다."}, 403)

    # 게시판 존재여부 확인
    board = db.get(Board, bo_table)
    if not board:
        return JSONResponse({"status": "fail", "message": "존재하지 않는 게시판입니다."}, 404)

    # 게시판 추천/비추천 기능 사용여부 확인
    if not getattr(board, f"bo_use_{type}"):
        return JSONResponse({"status": "fail", "message": "이 게시판은 추천 기능을 사용하지 않습니다."}, 403)

    # 게시글 존재여부 확인
    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        return JSONResponse({"status": "fail", "message": "존재하지 않는 게시글입니다."}, 404)

    # 자신글은 좋아요/싫어요 불가
    if write.mb_id == member.mb_id:
        return JSONResponse({"status": "fail", "message": f"자신의 글에는 {type_str}을 할 수 없습니다."}, 403)

    # 게시글의 추천/비추천 데이터 확인
    good_query = select(BoardGood).where(
        BoardGood.bo_table == bo_table,
        BoardGood.wr_id == wr_id,
        BoardGood.mb_id == member.mb_id
    )
    good_data = db.scalars(good_query).first()
    if good_data:
        # 추천/비추천의 bg_flag가 선택한 타입과 같다면,
        # 데이터 삭제 + 게시글의 추천/비추천 카운트 감소
        if good_data.bg_flag == type:
            db.delete(good_data)
            setattr(write, type_attr, getattr(write, type_attr) - 1)
            db.commit()
            result["status"] = "cancel"
            result["message"] = f"{type_str}이 취소되었습니다."
        # 존재하는데 다른 타입이라면
        # 데이터 수정 + 게시글의 추천/비추천 카운트 증가 + 반대 타입 카운트 감소
        else:
            good_data.bg_flag = type
            setattr(write, type_attr, getattr(write, type_attr) + 1)
            setattr(write, type_attr_rev, getattr(write, type_attr_rev) - 1)
            db.commit()
            result["message"] = f"게시글을 {type_str} 했습니다."
    else:
        # 존재하지 않으면
        # 데이터 추가 + 게시글의 추천/비추천 카운트 증가
        db.execute(
            insert(BoardGood).values(
                bo_table=bo_table,
                wr_id=wr_id,
                mb_id=member.mb_id,
                bg_flag=type
            )
        )
        setattr(write, type_attr, getattr(write, type_attr) + 1)
        db.commit()
        result["message"] = f"게시글을 {type_str} 했습니다."

    # 게시글의 추천/비추천 카운트 조회
    db.refresh(write)
    result["good"] = write.wr_good
    result["nogood"] = write.wr_nogood

    return JSONResponse(result, 200)
