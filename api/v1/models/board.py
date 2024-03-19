"""게시글 모델"""
from typing_extensions import Annotated, List
from datetime import datetime

from fastapi import Body
from pydantic import BaseModel, ConfigDict, model_validator



class WriteModel(BaseModel):
    """게시판 개별 글 모델"""

    # 추가 필드 허용
    model_config = ConfigDict(extra='allow')

    wr_subject: Annotated[str, Body(..., max_length=255, title="제목")]
    wr_content: Annotated[str, Body("", title="내용")]
    wr_name: Annotated[str, Body("", max_length=255, title="작성자", 
                                 description="비회원일 경우 작성자 이름")]
    wr_password: Annotated[str, Body("", max_length=255, title="비밀번호",
                                     description="비회원일 경우 비밀번호")]
    wr_email: Annotated[str, Body("", max_length=255, title="이메일")]
    wr_homepage: Annotated[str, Body("", max_length=255, title="홈페이지")]
    wr_link1: Annotated[str, Body("", title="링크1")]
    wr_link2: Annotated[str, Body("", title="링크2")]
    wr_option: Annotated[str, Body("", title="옵션")]
    html: Annotated[str, Body("", title="HTML 여부")]
    mail: Annotated[str, Body("", title="메일링 여부")]
    secret: Annotated[str, Body("", title="비밀글 여부")]
    ca_name: Annotated[str, Body("", title="카테고리")]
    notice: Annotated[bool, Body(False, title="공지글 여부")]
    parent_id: Annotated[int, Body(None, title="부모글 ID")]

    @model_validator(mode='after')
    def init_fields(self) -> 'WriteModel':
        """WriteModel에서 선언되지 않은 필드를 초기화"""
        self.wr_datetime: datetime = datetime.now()
        return self


class CommentModel(BaseModel):
    """게시판 댓글 모델"""

    # 추가 필드 허용
    model_config = ConfigDict(extra='allow')

    wr_content: Annotated[str, Body(..., title="내용")]
    wr_name: Annotated[str, Body("", title="작성자",
                                  description="비회원일 경우 작성자 이름")]
    wr_password: Annotated[str, Body("", title="비밀번호",
                                     description="비회원일 경우 비밀번호")]
    wr_option: Annotated[str, Body("html1", title="비밀글 여부",
                                   description="secret: 비밀글, html1: HTML 사용")]
    comment_id: Annotated[int, Body(None, title="부모댓글 ID")]

    @model_validator(mode='after')
    def init_fields(self) -> 'WriteModel':
        """CommentModel에서 선언되지 않은 필드를 초기화"""
        self.wr_is_comment: int = 1
        return self


class ResponseFileModel(BaseModel):
    """게시글 파일 모델중 response에 필요한 속성 정의"""
    bf_source: str
    bf_filesize: int
    bf_download: int
    bf_datetime: datetime


class ResponseCommentModel(BaseModel):
    """게시글 댓글 모델중 response에 필요한 속성 정의"""
    wr_id: int
    wr_parent: int
    wr_name: str
    mb_id: str
    save_content: str
    wr_datetime: datetime
    wr_last: datetime
    wr_option: str
    wr_email: str
    wr_comment: int
    is_reply: bool
    is_edit: bool
    is_del: bool
    is_secret: bool
    is_secret_content: bool


class ResponseWriteModel(BaseModel):
    """게시글 모델중 response에 필요한 속성 정의"""
    wr_id: int
    wr_num: int
    wr_reply: str
    wr_subject: str
    wr_name: str
    mb_id: str
    wr_datetime: datetime
    wr_option: str
    wr_email: str
    wr_content: str
    wr_link1: str
    wr_link2: str
    wr_comment: int
    wr_hit: int
    wr_ip: str
    images: List[ResponseFileModel]
    normal_files: List[ResponseFileModel]
    comments: List[ResponseCommentModel]

    class Config:
        from_attributes = True