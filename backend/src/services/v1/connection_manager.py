from sqlalchemy.orm import Session
from backend.src.schemas.connection import DatabaseConnectionCreate
from backend.src.crud.connection import create_connection, get_all_connections
from ...utils.utils import DBClientLoader

class ConnectionManager:

    def add_connection(self, db: Session, payload: DatabaseConnectionCreate):
        return create_connection(db, payload)

    def list_connections(self, db: Session):
        return get_all_connections(db)


connection_manager = ConnectionManager()

class ConnectionService:

    async def validate_connection(self, payload):
        db_type = payload.get("db_type")
        payload.pop('db_type', None)
        return DBClientLoader.check_db_connection(db_type=db_type, **payload)
    
    async def connect_db_client(self, payload):
        db_type = payload.get("db_type")
        payload.pop('db_type', None)
        return DBClientLoader.connect_client_db(db_type=db_type, **payload)
    

