from datetime import datetime

from pydantic import BaseModel


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