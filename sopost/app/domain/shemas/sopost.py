from pydantic import BaseModel


class SopostItemResponse(BaseModel):
    id: str
    name: str
    photo_link: str | None
    length: int | None
    width: int | None
    height: int | None
    manager: str | None


class SubjectsResponse(BaseModel):
    subject_name: str | None
    sopost_items: list[SopostItemResponse]
