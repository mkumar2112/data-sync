from sqlalchemy.orm import Session
from backend.src.schemas.connection import DatabaseConnectionCreate
from backend.src.crud.connection import create_connection, get_all_connections

class ConnectionManager:

    def add_connection(self, db: Session, payload: DatabaseConnectionCreate):
        return create_connection(db, payload)

    def list_connections(self, db: Session):
        return get_all_connections(db)


connection_manager = ConnectionManager()
