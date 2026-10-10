import os
from sqlalchemy import create_engine, Column, String, Float, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@postgres:5432/quickdrop")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Rider(Base):
    __tablename__ = "riders"
    rider_id = Column(String, primary_key=True)
    name = Column(String)
    phone = Column(String)
    city = Column(String)

class Trip(Base):
    __tablename__ = "trips"
    trip_id = Column(String, primary_key=True)
    rider_id = Column(String)
    date = Column(String)
    distance_km = Column(Float)
    fare = Column(Float)
    status = Column(String)

class PayoutLine(Base):
    __tablename__ = "payout_lines"
    line_id = Column(String, primary_key=True)
    rider_id = Column(String)
    trip_id = Column(String, nullable=True)
    amount = Column(Float)
    category = Column(String)
    date = Column(String)

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, unique=True)
    rider_id = Column(String)
    sender = Column(String)  # 'rider' or 'agent'
    text = Column(Text)
    created_at = Column(String)

class OpsDispute(Base):
    __tablename__ = "ops_disputes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rider_id = Column(String)
    trip_id = Column(String, nullable=True)
    amount = Column(Float)
    reason = Column(Text)
    status = Column(String, default="PENDING")
    created_at = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)