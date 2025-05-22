# app\database\db_config.py
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# PostgreSQL database URI (example: "postgresql://username:password@localhost/db_name")
DATABASE_URL = os.getenv("DATABASE_URL")
# Create database engine
engine = create_engine(DATABASE_URL)


# Session and Base for SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database()
