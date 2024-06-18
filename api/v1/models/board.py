"""게시글 모델"""
from datetime import datetime
from enum import Enum
from typing_extensions import Annotated, List, Union

from fastapi import Body, Path, Query
from pydantic import BaseModel, ConfigDict, model_validator, Field


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
    comment_id: Annotated[int, Body(None, title="댓글 ID")]

    @model_validator(mode='after')
    def init_fields(self) -> 'WriteModel':
        """CommentModel에서 선언되지 않은 필드를 초기화"""
        self.wr_is_comment: int = 1
        return self


class ResponseNormalModel(BaseModel):
    result: str


class ResponseCreateWriteModel(ResponseNormalModel):
    wr_id: int


class ResponseFileModel(BaseModel):
    """게시글 파일 모델중 response에 필요한 속성 정의"""
    bf_source: str
    bf_filesize: int
    bf_download: int
    bf_datetime: datetime
    bf_file: str


class ResponseCommentModel(BaseModel):
    """게시글 댓글 모델중 response에 필요한 속성 정의"""
    wr_id: int
    wr_parent: int
    wr_name: str
    mb_id: str
    mb_image_path: str
    mb_icon_path: str
    save_content: str
    wr_datetime: datetime
    wr_last: str
    wr_option: str
    wr_email: str
    wr_comment: int
    is_reply: bool
    is_edit: bool
    is_del: bool
    is_secret: bool
    is_secret_content: bool


class ResponseWriteSearchModel(BaseModel):
    """게시글 모델중 response에 필요한 속성 정의"""
    wr_id: int
    wr_num: int
    wr_reply: str
    wr_subject: str
    wr_name: str
    wr_datetime: datetime
    wr_content: str
    wr_comment: int
    wr_hit: int
    wr_option: str = "",

    class Config:
        from_attributes = True


class ThumbnailModel(BaseModel):
    """게시글 모델에 사용될 썸네일 모델"""
    src: str
    alt: str
    noimg: str


class ResponseWriteModel(BaseModel):
    """게시글 모델중 response에 필요한 속성 정의"""
    wr_id: int
    wr_num: int
    wr_reply: str
    wr_subject: str
    wr_name: str
    mb_id: str
    mb_image_path: str
    mb_icon_path: str
    wr_datetime: datetime
    wr_email: str
    wr_content: str
    wr_link1: str
    wr_link2: str
    wr_comment: int
    wr_hit: int
    wr_ip: str
    good: int
    nogood: int
    thumbnail: ThumbnailModel
    wr_option: str = "",
    images: List[ResponseFileModel] = []
    normal_files: List[ResponseFileModel] = []
    comments: List[ResponseCommentModel] = []

    class Config:
        from_attributes = True


class ResponseBoardModel(BaseModel):
    """
    게시판 모델중 response에 필요한 속성 정의
    타입 검증과 함께 정의되지 않은 속성은 제거하는 필터링 기능도 포함
    주석된 부분을 풀거나 추가하여 API response에서 보여지는 데이터를 변경할 수 있습니다.
    """
    bo_table: str
    gr_id: str
    bo_subject: str
    bo_mobile_subject: str
    bo_device: str
    bo_admin: str
    bo_list_level: int
    bo_read_level: int
    bo_write_level: int
    bo_reply_level: int
    bo_comment_level: int
    bo_upload_level: int
    bo_download_level: int
    bo_html_level: int
    bo_link_level: int
    bo_count_delete: int
    bo_count_modify: int
    bo_read_point: int
    bo_write_point: int
    bo_comment_point: int
    bo_download_point: int
    bo_use_category: int
    bo_category_list: str
    # bo_use_sideview: int
    # bo_use_file_content: int
    # bo_use_secret: int
    # bo_use_dhtml_editor: int
    # bo_select_editor: str
    # bo_use_rss_view: int
    # bo_use_good: int
    # bo_use_nogood: int
    # bo_use_name: int
    # bo_use_signature: int
    # bo_use_ip_view: int
    # bo_use_list_view: int
    # bo_use_list_file: int
    # bo_use_list_content: int
    # bo_table_width: int
    # bo_subject_len: int
    # bo_mobile_subject_len: int
    # bo_page_rows: int
    # bo_mobile_page_rows: int
    # bo_new: int
    # bo_hot: int
    # bo_image_width: int
    # bo_skin: str
    # bo_mobile_skin: str
    # bo_include_head: str
    # bo_include_tail: str
    # bo_content_head: str
    # bo_mobile_content_head: str
    # bo_content_tail: str
    # bo_mobile_content_tail: str
    # bo_insert_content: str
    # bo_gallery_cols: int
    # bo_gallery_width: int
    # bo_gallery_height: int
    # bo_mobile_gallery_width: int
    # bo_mobile_gallery_height: int
    # bo_upload_size: int
    # bo_reply_order: int
    # bo_use_search: int
    # bo_order: int
    # bo_count_write: int
    # bo_count_comment: int
    # bo_write_min: int
    # bo_write_max: int
    # bo_comment_min: int
    # bo_comment_max: int
    # bo_notice: str
    # bo_upload_count: int
    # bo_use_email: int
    # bo_use_cert: str
    # bo_use_sns: int
    # bo_use_captcha: int
    # bo_sort_field: str
    # bo_1_subj: str
    # bo_2_subj: str
    # bo_3_subj: str
    # bo_4_subj: str
    # bo_5_subj: str
    # bo_6_subj: str
    # bo_7_subj: str
    # bo_8_subj: str
    # bo_9_subj: str
    # bo_10_subj: str
    # bo_1: str
    # bo_2: str
    # bo_3: str
    # bo_4: str
    # bo_5: str
    # bo_6: str
    # bo_7: str
    # bo_8: str
    # bo_9: str
    # bo_10: str


class ResponseBoardListModel(BaseModel):
    """게시판 목록 모델"""
    categories: list
    board: ResponseBoardModel
    writes: List[ResponseWriteModel]
    total_count: int
    current_page: int
    prev_spt: Union[int, None]
    next_spt: Union[int, None]


class ResponseGroupModel(BaseModel):
    """게시판 그룹 모델"""
    gr_id: str
    gr_subject: str
    gr_device: str
    gr_admin: str
    gr_use_access: int
    gr_order: int


class ResponseGroupBoardsModel(BaseModel):
    """게시판 그룹, 게시판 목록 모델"""
    group: ResponseGroupModel
    boards: List[ResponseBoardModel]


class BoardNewViewType(str, Enum):
    WRITE = "write"
    COMMENT = "comment"


class RequestBoardNewWrites(BaseModel):
    """최신글 조회 API 요청 모델"""

    view_type: BoardNewViewType = Field(Query(
        default=BoardNewViewType.WRITE,
        title="조회 유형",
        description="게시글/댓글"
    ))
    rows: int = Field(Query(
        default=10,
        title="출력할 최신글 수",
        description="출력할 최신글 수"
    ))


class ResponseBoardNewModel(BaseModel):
    """최신글 모델"""
    bo_table: str
    wr_id: int
    wr_parent: int
    bn_datetime: datetime
    mb_id: str
    num: int


class ResponseBoardNewListModel(BaseModel):
    """최신글 목록 모델"""
    total_count: int
    board_news: List[ResponseBoardNewModel]
    current_page: int


class ResponseSearchBoardModel(ResponseBoardModel):
    """검색 결과 게시판 모델"""
    writes: List[ResponseWriteSearchModel]


class ResponseSearchModel(BaseModel):
    """검색 결과 모델"""
    total_search_count: int
    onetable: Union[str, None]
    boards: List[ResponseSearchBoardModel]


class WriteTransportation(Enum):
    """게시글 이동/복사"""
    MOVE = 'move'
    COPY = 'copy'


class WriteTransportationRequest(BaseModel):
    """게시글 이동/복사 API 요청 모델"""
    sw: WriteTransportation = Field(Path(title="이동/복사", description="게시글 이동 또는 복사"))
