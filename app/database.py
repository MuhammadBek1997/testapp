import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if DATABASE_URL and "sslmode=" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL + ("&sslmode=require" if "?" in DATABASE_URL else "?sslmode=require")

# Fallback: build from individual env vars if DATABASE_URL missing
if not DATABASE_URL:
    host = os.getenv("DATABASE_HOST")
    user = os.getenv("DATABASE_USER")
    password = os.getenv("DATABASE_PASSWORD")
    name = os.getenv("DATABASE_NAME")
    port = os.getenv("DATABASE_PORT", "5432")
    if host and user and password and name:
        DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{name}?sslmode=require"

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()