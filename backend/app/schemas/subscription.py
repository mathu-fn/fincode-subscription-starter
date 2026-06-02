from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateSubscriptionRequest(BaseModel):
    fincode_plan_id: str = Field(min_length=1, max_length=128)
    # フリープラン（fincode_plan_id="free"）はカード不要のため任意。
    card_id: int | None = None


class ChangeSubscriptionPlanRequest(BaseModel):
    fincode_plan_id: str = Field(min_length=1, max_length=128)
    # フリープランから有料プランへ変更する場合はカードが必要。
    card_id: int | None = None


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    fincode_subscription_id: str | None = None
    fincode_plan_id: str
    plan_name: str
    plan_amount: int
    plan_interval: str
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime


class PlanOut(BaseModel):
    fincode_plan_id: str
    name: str
    amount: int
    currency: str = "JPY"
    interval: str


class BillingHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    amount: int
    fincode_payment_id: str | None = None
    charged_at: datetime


class PaginatedBillingHistory(BaseModel):
    data: list[BillingHistoryItem]
    page: int
    per_page: int
    total: int
