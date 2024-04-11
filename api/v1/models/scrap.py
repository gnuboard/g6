from datetime import datetime
from typing import List
from typing_extensions import Annotated

from fastapi import Body
from pydantic import BaseModel

from api.v1.models.pagination import PaginationResponse


class ResponseScrapModel(BaseModel):
    ms_id: int
    mb_id: str
    bo_table: str
    wr_id: int
    ms_datetime: datetime

    wr_subject: str 
    bo_subject: str

    class Config:
        from_attributes = True


class ResponseScrapListModel(PaginationResponse):
    scraps: List[ResponseScrapModel]


class CreateScrapModel(BaseModel):
    wr_content: Annotated[str, Body("")]
