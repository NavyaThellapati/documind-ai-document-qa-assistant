from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    message_id: str
    helpful: bool
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackRead(BaseModel):
    id: str
    message_id: str
    helpful: bool
    comment: str | None

    model_config = {"from_attributes": True}
