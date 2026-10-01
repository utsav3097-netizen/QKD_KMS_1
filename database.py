from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_url = "postgresql://postgres:Patil988@localhost:5432/FastAPI"

engine= create_engine(db_url)
session= sessionmaker(autocommit=False, autoflush=False, bind=engine)
