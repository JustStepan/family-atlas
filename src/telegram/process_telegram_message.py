from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from src.database.engine import get_db
from src.database.models import RawMessages, Author


def get_or_create(session, model, params):
    stmt = select(model).filter_by(**params)
    obj = session.scalar(stmt)
    if obj:
        print(f'Object {obj} already exists') 
        return obj

    params = {**params}
    obj = model(**params)
    session.add(obj)

    try:
        session.commit()
        print(f'Object {obj} was successfuly created')
        return obj
    except IntegrityError:
        session.rollback()
        obj = session.scalar(select(model).filter_by(**params))
        return obj