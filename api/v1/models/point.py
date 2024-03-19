from typing import List

from pydantic import BaseModel

from api.v1.models import ResponsePageListModel


class ResponsePointModel(BaseModel):
    po_content: str
    po_point: int
    po_rel_table: str
    po_rel_id: str
    po_rel_action: str

    class Config:
        from_attributes = True


class ResponsePointListModel(ResponsePageListModel):
    points: List[ResponsePointModel]