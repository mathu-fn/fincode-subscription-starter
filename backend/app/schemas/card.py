from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateCardRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2048)


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    created_at: datetime
