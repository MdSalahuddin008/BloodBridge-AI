from sqlalchemy.orm import Session

from app.database.models import Conversation, Message


class ChatService:

    @staticmethod
    def get_or_create_conversation(
        db: Session,
        user_type: str,
        user_id: int
    ):

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.user_type == user_type,
                Conversation.user_id == user_id
            )
            .first()
        )

        if conversation is None:
            conversation = Conversation(
                user_type=user_type,
                user_id=user_id
            )

            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        return conversation

    @staticmethod
    def load_messages(
        db: Session,
        conversation_id: int
    ):

        return (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id
            )
            .order_by(Message.timestamp.asc())
            .all()
        )

    @staticmethod
    def save_user_message(
        db: Session,
        conversation_id: int,
        content: str
    ):

        message = Message(
            conversation_id=conversation_id,
            sender="user",
            content=content
        )

        db.add(message)
        db.commit()

    @staticmethod
    def save_ai_message(
        db: Session,
        conversation_id: int,
        content: str
    ):

        message = Message(
            conversation_id=conversation_id,
            sender="assistant",
            content=content
        )

        db.add(message)
        db.commit()