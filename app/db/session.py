import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Docker container ke andar postgres se connect karne ke liye URL
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/quickdrop")

# Fallback: Agar URL me 'db' ya 'postgres' hostname hai lekin hum host machine pe local uvicorn chala rahe hain,
# toh 'db'/'postgres' resolve nahi hoga. Aise case me transparently 'localhost' par switch karo.
import socket
for host in ["db", "postgres"]:
    if f"@{host}:" in DATABASE_URL:
        try:
            socket.gethostbyname(host)
        except socket.gaierror:
            DATABASE_URL = DATABASE_URL.replace(f"@{host}:", "@localhost:")
            break

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()