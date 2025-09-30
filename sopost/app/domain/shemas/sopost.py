from datetime import datetime

from pydantic import BaseModel, HttpUrl

# тип для данных в формате json
KitComponents = dict | list | None


class SopostItemResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    is_kit: bool | None
    share_of_kit: bool | None
    kit_components: KitComponents
    photo_link: HttpUrl | None
    is_inventoried: bool | None
    created_at: datetime
