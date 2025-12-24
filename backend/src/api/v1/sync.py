from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ...core.status import APIStatus
from backend.src.db.session import get_db
from backend.src.schemas.connection import DatabaseConnectionCreate, DatabaseConnectionOut
from backend.src.services.v1.connection_manager import connection_manager , ConnectionService, Database_Operation


class Database_Operations:   
    def __init__(self):
        self.router = APIRouter(
            prefix="/db/operation",
            tags=["Database Connections Validation"]
        )

        # Register routes
        self.router.post("/sync_structure_db")(self.sync_structure_db)
        self.router.post("/create_replica")(self.create_replica)


    async def sync_structure_db(self, request: Request, db: Session = Depends(get_db)):
        try:
            json_data = request.json()
            db_operation_obj = Database_Operation(request=request, db=db)
            replica_db = await db_operation_obj.sync_structure_db(payload=json_data)
            return replica_db
        except Exception as e:
            return {**APIStatus.get(500).to_dict(), 'message': f'An error occured: {str(e)}'}
        

    async def create_replica(self, request: Request, db: Session = Depends(get_db)):
        try:
            db_operation_obj = Database_Operation(request=request, db=db)
            replica_db = await db_operation_obj.replica_db()
            return replica_db
        except Exception as e:
            return {**APIStatus.get(500).to_dict(), 'message': f'An error occured: {str(e)}'}
        

    async def sync_db(self, request: Request, db: Session = Depends(get_db)):
        try:
            json_data = await request.json()
            db_list = connection_manager.list_connections(db=db)
            
            return db_list
        except Exception as e:
            return {**APIStatus.get(500).to_dict(), 'message': f'An error occured: {str(e)}'}
        
