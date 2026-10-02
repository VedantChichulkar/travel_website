from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.communication import ConversationKind, ConversationStatus, NotificationChannel, NotificationEventType, NotificationJobStatus


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    hotel_id: int | None = Field(default=None, gt=0)
    booking_id: int | None = Field(default=None, gt=0)
    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=1, max_length=5000)
    kind: ConversationKind | None = None

    @model_validator(mode="after")
    def require_target(self):
        if self.hotel_id is None and self.booking_id is None:
            raise ValueError("hotel_id or booking_id is required")
        return self


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class MessageRead(OrmModel):
    id: int
    sender: str
    is_mine: bool
    body: str
    created_at: datetime


class ConversationRead(OrmModel):
    id: int
    hotel_id: int
    hotel_name: str
    booking_id: int | None
    booking_reference: str | None
    subject: str
    kind: ConversationKind
    status: ConversationStatus
    unread_count: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = Field(default_factory=list)


class ConversationList(BaseModel):
    items: list[ConversationRead]
    total: int
    unread_count: int


class AdminConversationAccess(BaseModel):
    reason: str = Field(min_length=10, max_length=255)


class NotificationJobRead(OrmModel):
    id: int
    channel: NotificationChannel
    status: NotificationJobStatus
    provider: str | None
    attempts: int
    last_error: str | None
    next_retry_at: datetime | None
    sent_at: datetime | None


class NotificationRead(OrmModel):
    id: int
    event_type: NotificationEventType
    title: str
    body: str
    data: dict[str, object]
    read_at: datetime | None
    created_at: datetime
    jobs: list[NotificationJobRead]


class NotificationList(BaseModel):
    items: list[NotificationRead]
    total: int
    unread_count: int
