from sqlalchemy import Column, String, Float, Integer, Text
from app.db.session import Base, engine

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