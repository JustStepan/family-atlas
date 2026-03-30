from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.config import BASE_DIR
from .models import Base


DB_DIR = BASE_DIR / 'family-atlas.db'
engine = create_engine(f'sqlite:///{DB_DIR}', echo=True)
Base.metadata.create_all(engine)


@contextmanager
def get_db():
    with Session(engine) as session:
        yield session