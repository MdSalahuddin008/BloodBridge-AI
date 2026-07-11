from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.database import Base


class Donor(Base):
    __tablename__ = "donors"

    donor_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    gender = Column(String)
    date_of_birth = Column(Date)
    blood_group = Column(String, index=True)
    weight = Column(Float)
    city = Column(String)
    state = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    last_donation_date = Column(Date)
    tattoo_date = Column(Date)
    currently_available = Column(Boolean, default=True)


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    gender = Column(String)
    date_of_birth = Column(Date)
    blood_group = Column(String, index=True)
    city = Column(String)
    state = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

class Notification(Base):
    __tablename__ = "notifications"
    notification_id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(
        Integer,
        ForeignKey("donors.donor_id"),
        nullable=False
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.patient_id"),
        nullable=False
    )
    blood_group = Column(String, nullable=False)
    city = Column(String, nullable=False)
    status = Column(
        String,
        default="Pending"
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now()
    )

    donor = relationship("Donor")
    patient = relationship("Patient")


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True)

    user_type = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)

    created_at = Column(
    DateTime,
    default=lambda: datetime.now()
)

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.conversation_id"),
        nullable=False
    )

    sender = Column(String, nullable=False)

    content = Column(Text, nullable=False)

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now()
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )
