from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.src.db.session import get_db
from backend.src.schemas.connection import DatabaseConnectionCreate, DatabaseConnectionOut
from backend.src.services.v1.connection_manager import connection_manager , ConnectionService


class ConnectionRouter:

    def __init__(self):
        self.router = APIRouter(
            prefix="/connections",
            tags=["Database Connections"]
        )

        # Register routes
        self.router.post("/", response_model=DatabaseConnectionOut)(self.create_db_connection)
        self.router.get("/", response_model=list[DatabaseConnectionOut])(self.get_all_db_connections)

    def create_db_connection(self, payload: DatabaseConnectionCreate, db: Session = Depends(get_db)):
        return connection_manager.add_connection(db, payload)

    def get_all_db_connections(self, db: Session = Depends(get_db)):
        return connection_manager.list_connections(db)


class DB_ConnectionRouter:

    def __init__(self):
        self.router = APIRouter(
            prefix="/db",
            tags=["Database Connections Validation"]
        )

        # Register routes
        self.router.post("/check")(self.check_db_connection)
        self.router.post("/connect")(self.connect_db)
        # self.router.get("/", response_model=list[DatabaseConnectionOut])(self.get_all_db_connections)

    async def check_db_connection(self, request:Request):
        try:
            json_data = await request.json()
            connection_service = ConnectionService()
            response = await connection_service.validate_connection(json_data)
            return response
        except Exception as e:
            return {'message': f'An error occured: {str(e)}'}
        
    async def connect_db(self, request:Request):
        try:
            json_data = await request.json()
            connection_service = ConnectionService()
            response = await connection_service.connect_db_client(json_data)
            return response
        except Exception as e:
            return {'message': f'An error occured: {str(e)}'}