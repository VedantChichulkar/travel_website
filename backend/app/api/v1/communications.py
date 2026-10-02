from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permission import require_admin, require_customer
from app.dependencies import get_current_user, get_db
from app.models.communication import Conversation, Message
from app.models.user import User, UserRole
from app.schemas.communication import AdminConversationAccess, ConversationCreate, ConversationList, ConversationRead, MessageCreate, MessageRead, NotificationList, NotificationRead
from app.services import communication_service, notification_service


router = APIRouter()
admin_router = APIRouter()


def _message(item: Message, user: User, hotel_name: str) -> MessageRead:
    if item.sender_user_id == user.id:
        sender = "You"
    elif item.sender_user_id == item.conversation.customer_id:
        sender = "Guest"
    else:
        sender = hotel_name
    return MessageRead(id=item.id, sender=sender, is_mine=item.sender_user_id == user.id, body=item.body, created_at=item.created_at)


def _conversation(db: Session, item: Conversation, user: User, *, include_messages: bool = True) -> ConversationRead:
    hotel, booking = communication_service.hotel_and_booking(db, item)
    hotel_name = hotel.name if hotel else "Hotel"
    return ConversationRead(
        id=item.id,
        hotel_id=item.hotel_id,
        hotel_name=hotel_name,
        booking_id=item.booking_id,
        booking_reference=booking.booking_reference if booking else None,
        subject=item.subject,
        kind=item.kind,
        status=item.status,
        unread_count=0 if user.role == UserRole.ADMIN else communication_service.unread_count(item, user.id),
        last_message_at=item.messages[-1].created_at if item.messages else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
        messages=[_message(message, user, hotel_name) for message in item.messages] if include_messages else [],
    )


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return _conversation(db, communication_service.create_conversation(db, current_user, data), current_user)


@router.get("/conversations", response_model=ConversationList)
def list_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = communication_service.list_conversations(db, current_user)
    rendered = [_conversation(db, item, current_user, include_messages=False) for item in items]
    return ConversationList(items=rendered, total=len(rendered), unread_count=sum(item.unread_count for item in rendered))


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _conversation(db, communication_service.get_conversation(db, current_user, conversation_id), current_user)


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def send_message(conversation_id: int, data: MessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _conversation(db, communication_service.send_message(db, current_user, conversation_id, data.body), current_user)


@router.post("/conversations/{conversation_id}/read", response_model=ConversationRead)
def mark_conversation_read(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _conversation(db, communication_service.mark_read(db, current_user, conversation_id), current_user)


@router.get("/notifications", response_model=NotificationList)
def list_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items, unread = notification_service.list_for_user(db, current_user)
    return NotificationList(items=[NotificationRead.model_validate(item) for item in items], total=len(items), unread_count=unread)


@router.post("/notifications/read-all")
def mark_all_notifications_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"updated": notification_service.mark_all_read(db, current_user)}


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = notification_service.mark_read(db, current_user, notification_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return item


@admin_router.post("/conversations/{conversation_id}/inspect", response_model=ConversationRead)
def inspect_conversation(conversation_id: int, data: AdminConversationAccess, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    item = communication_service.admin_inspect(db, current_user, conversation_id, data.reason)
    return _conversation(db, item, current_user)
