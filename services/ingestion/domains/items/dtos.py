# services/ingestion/domains/items/dtos.py
from pydantic import BaseModel, Field


class Item(BaseModel):
    """Domain DTO предмету Dota 2.

    OpenDota /constants/items повертає dict де ключ — internal name ('blink'),
    а значення — об'єкт з полями id, dname, cost тощо.
    """

    id: int = Field(..., ge=0)
    name: str                    # internal key: 'blink'
    localized_name: str          # display name: 'Blink Dagger' (поле dname в API)
    cost: int = Field(default=0, ge=0)
    secret_shop: bool = False
    side_shop: bool = False
    recipe: bool = False