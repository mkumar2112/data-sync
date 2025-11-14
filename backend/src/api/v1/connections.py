from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.src.db.session import get_db
from backend.src.schemas.connection import DatabaseConnectionCreate, DatabaseConnectionOut
from backend.src.services.connection_manager import connection_manager

router = APIRouter(prefix="/connections", tags=["Database Connections"])


@router.post("/", response_model=DatabaseConnectionOut)
def create_db_connection(payload: DatabaseConnectionCreate, db: Session = Depends(get_db)):
    return connection_manager.add_connection(db, payload)


@router.get("/", response_model=list[DatabaseConnectionOut])
def get_all_db_connections(db: Session = Depends(get_db)):
    return connection_manager.list_connections(db)
