from typing_extensions import Union, List
from datetime import datetime

from fastapi import Request
from sqlalchemy import select, insert, func

from core.database import db_session
from core.formclass import AutoSaveForm
from core.models import Board, Member, WriteBaseModel, BoardGood, AutoSave
from core.exception import JSONException
from lib.common import dynamic_create_write_table, get_unique_id
from lib.token import check_token
from api.v1.models.ajax import AutoSaveModel, responses


class AJAXService:
    """AJAX 요청을 처리하는 서비스 클래스"""

    responses = responses

    def __init__(
        self,
        request: Request,
        db: db_session,
    ):
        self.request = request
        self.db = db

    def validate_member(self, member: Member):
        """회원 여부 검증"""
        if not member:
            raise JSONException(status_code=403, message="로그인 후 이용 가능합니다.")

    def validate_token(self, token: str):
        """토큰 검증"""
        if not check_token(self.request, token):
            raise JSONException(status_code=403, message="토큰이 유효하지 않습니다.")

    def get_board(self, bo_table: str) -> Board:
        """게시판 존재여부 확인"""
        board = self.db.get(Board, bo_table)
        if not board:
            raise JSONException(status_code=403, message="존재하지 않는 게시판입니다.")
        return board

    def validate_board_good_use(self, board: Board, type: str):
        """게시판 추천/비추천 기능 사용여부 확인"""
        bo_use_type = getattr(board, f"bo_use_{type}", None)
        if bo_use_type is None:
            raise JSONException(status_code=403, message="잘못된 type 입력입니다. good 또는 nogood만 가능합니다.")
        if not bo_use_type:
            raise JSONException(status_code=403, message="이 게시판은 추천 기능을 사용하지 않습니다.")

    def get_write(self, bo_table: str, wr_id: int) -> WriteBaseModel:
        """게시글 존재여부 확인"""
        write_model = dynamic_create_write_table(bo_table)
        write = self.db.get(write_model, wr_id)
        if not write:
            raise JSONException(status_code=404, message="존재하지 않는 게시글입니다.")
        return write

    def validate_write_owner(self, write: WriteBaseModel, member: Member, type: str):
        """자신글은 좋아요/싫어요 불가"""
        type_str = "추천" if type == "good" else "비추천"
        if write.mb_id == member.mb_id:
            raise JSONException(status_code=403, message=f"자신의 글에는 {type_str}을 할 수 없습니다.")

    def get_ajax_good_result(self, bo_table: str, member: Member, write: WriteBaseModel, type: str) -> dict:
        """게시글의 추천/비추천 데이터 확인"""
        result = {"status": "success", "message": "", "good": 0, "nogood": 0}
        type_str = "추천" if type == "good" else "비추천"
        type_attr = f"wr_{type}"  # 선택한 타입
        type_attr_rev = "wr_good" if type == "nogood" else "wr_nogood"  # 반대 타입
        good_query = select(BoardGood).where(
            BoardGood.bo_table == bo_table,
            BoardGood.wr_id == write.wr_id,
            BoardGood.mb_id == member.mb_id
        )
        good_data = self.db.scalars(good_query).first()
        if good_data:
            # 추천/비추천의 bg_flag가 선택한 타입과 같다면,
            # 데이터 삭제 + 게시글의 추천/비추천 카운트 감소
            if good_data.bg_flag == type:
                self.db.delete(good_data)
                setattr(write, type_attr, getattr(write, type_attr) - 1)
                self.db.commit()
                result["status"] = "cancel"
                result["message"] = f"{type_str}이 취소되었습니다."
            # 존재하는데 다른 타입이라면
            # 데이터 수정 + 게시글의 추천/비추천 카운트 증가 + 반대 타입 카운트 감소
            else:
                good_data.bg_flag = type
                setattr(write, type_attr, getattr(write, type_attr) + 1)
                setattr(write, type_attr_rev, getattr(write, type_attr_rev) - 1)
                self.db.commit()
                result["message"] = f"게시글을 {type_str} 했습니다."
        else:
            # 존재하지 않으면
            # 데이터 추가 + 게시글의 추천/비추천 카운트 증가
            self.db.execute(
                insert(BoardGood).values(
                    bo_table=bo_table,
                    wr_id=write.wr_id,
                    mb_id=member.mb_id,
                    bg_flag=type
                )
            )
            setattr(write, type_attr, getattr(write, type_attr) + 1)
            self.db.commit()
            result["message"] = f"게시글을 {type_str} 했습니다."

        # 게시글의 추천/비추천 카운트 조회
        self.db.refresh(write)
        result["good"] = write.wr_good
        result["nogood"] = write.wr_nogood
        return result

    def validate_login(self, member: Member):
        """로그인 여부 검증"""
        if not member:
            raise JSONException(status_code=403, message="로그인 후 이용 가능합니다.")

    def get_autosave_list(self, member: Member) -> List[AutoSave]:
        """자동저장 목록을 반환한다."""
        save_list = self.db.scalars(
            select(AutoSave)
            .where(AutoSave.mb_id == member.mb_id)
            .order_by(AutoSave.as_datetime.desc())
        ).all()
        return save_list

    def get_autosave_content(self, as_id: int, member: Member) -> AutoSave:
        """자동저장 데이터를 반환한다."""
        save_data = self.db.get(AutoSave, as_id)
        if not save_data:
            raise JSONException(status_code=404, message="저장된 글이 없습니다.")
        if save_data.mb_id != member.mb_id:
            raise JSONException(status_code=403, detail="접근 권한이 없습니다.")
        return save_data

    def get_autosave_count(self, mb_id: str) -> int:
        """자동저장글 개수를 반환한다."""
        count = self.db.scalar(
            select(func.count(AutoSave.as_id))
            .where(AutoSave.mb_id == mb_id)
        )
        return count

    def autosave_save(self, member: Member, data: Union[AutoSaveForm, AutoSaveModel]):
        """임시저장 데이터가 있는지 확인 후 수정 또는 추가"""
        if not data.as_uid:
            data.as_uid = get_unique_id(self.request)

        save_data = self.db.scalar(
            select(AutoSave)
            .where(AutoSave.mb_id == member.mb_id, AutoSave.as_uid == data.as_uid)
        )
        if save_data:
            save_data.as_subject = data.as_subject
            save_data.as_content = data.as_content
            save_data.as_datetime = datetime.now()
        else:
            self.db.add(AutoSave(mb_id=member.mb_id, **data.__dict__))
        self.db.commit()

    def autosave_delete(self, as_id: int, member: Member):
        """임시저장글 삭제"""
        save_data = self.db.get(AutoSave, as_id)
        if not save_data:
            raise JSONException(status_code=404, message="저장된 글이 없습니다.")
        if save_data.mb_id != member.mb_id:
            raise JSONException(status_code=403, message="접근 권한이 없습니다.")
        self.db.delete(save_data)
        self.db.commit()