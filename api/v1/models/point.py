from pydantic import BaseModel


class ResponsePointModel(BaseModel):
    po_content: str
    po_point: int
    po_rel_table: str
    po_rel_id: str
    po_rel_action: str

    class Config:
        from_attributes = True