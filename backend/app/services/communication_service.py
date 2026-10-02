from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.booking import Booking
from app.models.communication import Conversation, ConversationAdminAccess, ConversationKind, ConversationReadState, ConversationStatus, Message
from app.models.hotel import Hotel, HotelStatus
from app.models.user import User, UserRole
from app.schemas.communication import ConversationCreate
from app.services import notification_service
from app.models.communication import NotificationEventType
from app.services import audit_service


def _partner_hotel(db: Session, user: User) -> Hotel:
    hotel = db.scalar(select(Hotel).where(Hotel.partner_id == user.id))
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return hotel


def _query():
    return select(Conversation).options(selectinload(Conversation.messages), selectinload(Conversation.read_states)).execution_options(populate_existing=True)


def _scoped(db: Session, user: User, conversation_id: int, *, lock: bool = False) -> Conversation:
    query = _query().where(Conversation.id == conversation_id)
    if user.role in (UserRole.CUSTOMER, UserRole.USER):
        query = query.where(Conversation.customer_id == user.id)
    elif user.role == UserRole.HOTEL_PARTNER:
        query = query.where(Conversation.hotel_id == _partner_hotel(db, user).id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation participant access required")
    if lock:
        query = query.with_for_update()
    conversation = db.scalar(query)
    if conversation is None:
        # Deliberately hide whether a cross-tenant conversation exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def create_conversation(db: Session, customer: User, data: ConversationCreate) -> Conversation:
    if customer.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can start hotel conversations")
    booking = db.get(Booking, data.booking_id) if data.booking_id else None
    if data.booking_id and (booking is None or booking.user_id != customer.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    hotel_id = booking.hotel_id if booking else data.hotel_id
    if booking and data.hotel_id and data.hotel_id != booking.hotel_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Booking does not belong to that hotel")
    hotel = db.get(Hotel, hotel_id) if hotel_id else None
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    if booking is None and hotel.status != HotelStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    kind = data.kind or (ConversationKind.BOOKING if booking else ConversationKind.PRE_BOOKING)
    if booking is None and kind != ConversationKind.PRE_BOOKING:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="This conversation kind requires a booking")
    conversation = Conversation(hotel_id=hotel.id, customer_id=customer.id, booking_id=booking.id if booking else None, subject=" ".join(data.subject.split()), kind=kind)
    conversation.messages.append(Message(sender_user_id=customer.id, body=data.message.strip(), created_at=datetime.now(timezone.utc)))
    db.add(conversation)
    db.flush()
    conversation.read_states.append(ConversationReadState(user_id=customer.id, last_read_at=datetime.now(timezone.utc)))
    first_message = conversation.messages[0]
    if hotel.partner_id:
        notification_service.create(
            db, recipient_user_id=hotel.partner_id, event_type=NotificationEventType.MESSAGE_RECEIVED,
            dedupe_key=f"MESSAGE_RECEIVED:message:{first_message.id}", title="New guest message",
            body="A guest sent a new message. Open Maharashtra Tourist Places Messages to reply.",
            data={"conversation_id": conversation.id, "booking_id": conversation.booking_id, "hotel_id": hotel.id},
        )
    if kind == ConversationKind.DISPUTE and hotel.partner_id:
        notification_service.create(db, recipient_user_id=hotel.partner_id, event_type=NotificationEventType.DISPUTE, dedupe_key=f"DISPUTE:conversation:{conversation.id}", title="Booking dispute opened", body="A guest opened a booking dispute. Review the conversation in Maharashtra Tourist Places.", data={"conversation_id": conversation.id, "booking_id": conversation.booking_id, "hotel_id": hotel.id})
    db.commit()
    return _scoped(db, customer, conversation.id)


def list_conversations(db: Session, user: User) -> list[Conversation]:
    query = _query()
    if user.role in (UserRole.CUSTOMER, UserRole.USER):
        query = query.where(Conversation.customer_id == user.id)
    elif user.role == UserRole.HOTEL_PARTNER:
        query = query.where(Conversation.hotel_id == _partner_hotel(db, user).id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation participant access required")
    return list(db.scalars(query.order_by(Conversation.updated_at.desc())))


def get_conversation(db: Session, user: User, conversation_id: int) -> Conversation:
    return _scoped(db, user, conversation_id)


def send_message(db: Session, user: User, conversation_id: int, body: str) -> Conversation:
    conversation = _scoped(db, user, conversation_id, lock=True)
    if conversation.status != ConversationStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation is closed")
    now = datetime.now(timezone.utc)
    message = Message(sender_user_id=user.id, body=body.strip(), created_at=now)
    conversation.messages.append(message)
    conversation.updated_at = now
    db.flush()
    hotel = db.get(Hotel, conversation.hotel_id)
    recipient_id = conversation.customer_id if user.id != conversation.customer_id else (hotel.partner_id if hotel else None)
    if recipient_id:
        notification_service.create(
            db, recipient_user_id=recipient_id, event_type=NotificationEventType.MESSAGE_RECEIVED,
            dedupe_key=f"MESSAGE_RECEIVED:message:{message.id}", title="New message",
            body="You received a new message. Open Maharashtra Tourist Places Messages to view it.",
            data={"conversation_id": conversation.id, "booking_id": conversation.booking_id, "hotel_id": conversation.hotel_id},
        )
    db.commit()
    return _scoped(db, user, conversation.id)


def mark_read(db: Session, user: User, conversation_id: int) -> Conversation:
    conversation = _scoped(db, user, conversation_id)
    state = next((item for item in conversation.read_states if item.user_id == user.id), None)
    now = datetime.now(timezone.utc)
    if state is None:
        state = ConversationReadState(conversation_id=conversation.id, user_id=user.id, last_read_at=now)
        db.add(state)
    else:
        state.last_read_at = now
    db.commit()
    return _scoped(db, user, conversation.id)


def unread_count(conversation: Conversation, user_id: int) -> int:
    state = next((item for item in conversation.read_states if item.user_id == user_id), None)
    if state is None:
        return sum(1 for item in conversation.messages if item.sender_user_id != user_id)
    read_at = state.last_read_at if state.last_read_at.tzinfo else state.last_read_at.replace(tzinfo=timezone.utc)
    return sum(1 for item in conversation.messages if item.sender_user_id != user_id and (item.created_at if item.created_at.tzinfo else item.created_at.replace(tzinfo=timezone.utc)) > read_at)


def admin_inspect(db: Session, admin: User, conversation_id: int, reason: str) -> Conversation:
    if admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    conversation = db.scalar(_query().where(Conversation.id == conversation_id))
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    db.add(ConversationAdminAccess(conversation_id=conversation.id, admin_user_id=admin.id, reason=reason.strip()))
    audit_service.record(db, actor=admin, action="DISPUTE_CONVERSATION_INSPECTED", target_type="CONVERSATION", target_id=conversation.id, reason=reason, previous_value=None, new_value={"inspected": True})
    db.commit()
    return conversation


def hotel_and_booking(db: Session, conversation: Conversation) -> tuple[Hotel, Booking | None]:
    return db.get(Hotel, conversation.hotel_id), db.get(Booking, conversation.booking_id) if conversation.booking_id else None
