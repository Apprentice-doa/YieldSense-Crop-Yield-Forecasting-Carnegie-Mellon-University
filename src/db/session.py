import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"), future=True)
DBSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()
