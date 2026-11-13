from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    is_banned = Column(Boolean, default=False)
    warning_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("MessageLog", back_populates="user", cascade="all, delete-orphan")


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_message_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    chat_title = Column(String(255), nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_telegram_id = Column(BigInteger, nullable=False, index=True)
    sender_name = Column(String(255), nullable=True)
    sender_username = Column(String(255), nullable=True)

    original_text = Column(Text, nullable=False)
    translated_uz = Column(Text, nullable=True)
    translated_ru = Column(Text, nullable=True)

    # Status: ALLOWED, BLOCKED, DELETED, REPORTED
    status = Column(String(50), default="ALLOWED", index=True)
    # Stage: CLEAN, REGEX, GEMINI
    detection_stage = Column(String(50), default="CLEAN")
    # Violation: NONE, SPAM, LINK, INSULT, CTA, FLOOD
    violation_type = Column(String(50), default="NONE", index=True)
    
    toxicity_score = Column(Float, default=0.0)
    reason = Column(Text, nullable=True)
    action_taken = Column(String(50), default="NONE") # NONE, DELETED, WARNED, MUTED, BANNED
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="messages")
    reports = relationship("Report", back_populates="message", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("message_logs.id"), nullable=False)
    reporter_telegram_id = Column(BigInteger, nullable=False)
    reporter_name = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    
    # Status: PENDING, APPROVED (Message was violating), REJECTED (False alarm)
    status = Column(String(50), default="PENDING", index=True)
    admin_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    message = relationship("MessageLog", back_populates="reports")


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
