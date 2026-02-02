from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.annotation import Annotated

from src.db.session import get_db

DBDep = Annotated[AsyncSession, Depends(get_db())]