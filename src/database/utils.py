from sqlalchemy import select


async def get_or_create(session, model, search_params, create_params=None):
    query = select(model).filter_by(**search_params)
    obj = (await session.execute(query)).scalar_one_or_none()
    if obj:
        return obj, False
    all_params = {**(create_params or {}), **search_params}
    obj = model(**all_params)
    return obj, True