from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ...core.status import api_response
from backend.src.db.session import get_db
from backend.src.schemas.connection import DatabaseConnectionCreate, DatabaseConnectionOut
from backend.src.services.v1.connection_manager import connection_manager , ConnectionService, Database_Operation, DQL_Operation
from backend.src.services.v1.ETL.etl_pipeline import ETLService


class Database_Operations:   
    def __init__(self):
        self.router = APIRouter(
            prefix="/db/operation",
            tags=["Database Connections Validation"]
        )

        # Register routes
        self.router.post("/sync_structure_db")(self.sync_structure_db)
        self.router.post("/create_replica")(self.create_replica)
        self.router.post("/sync_db_structure_to_db")(self.sync_db_structure_to_db)


    async def sync_structure_db(self, request: Request, db: Session = Depends(get_db)):
        try:
            json_data = request.json()
            db_operation_obj = Database_Operation(request=request, db=db)
            replica_db = await db_operation_obj.sync_structure_db(payload=json_data)
            return replica_db
        except Exception as e:
            return api_response(500, message = f'An error occured: {str(e)}')
        

    async def create_replica(self, request: Request, db: Session = Depends(get_db)):
        try:
            db_operation_obj = Database_Operation(request=request, db=db)
            replica_db = await db_operation_obj.replica_db()
            return replica_db
        except Exception as e:
            return api_response(500, message = f'An error occured: {str(e)}')
        
    async def sync_db_structure_to_db(self, request: Request, db: Session = Depends(get_db)):
        try:
            db_operation_obj = Database_Operation(request=request, db=db)
            replica_db = await db_operation_obj.sync_db_structure_to_db()
            return replica_db
        except Exception as e:
            return api_response(500, message = f'An error occured: {str(e)}')
        

    async def sync_db(self, request: Request, db: Session = Depends(get_db)):
        try:
            json_data = await request.json()
            db_list = connection_manager.list_connections(db=db)
            
            return db_list
        except Exception as e:
            return api_response(500, message = f'An error occured: {str(e)}')


class DQL_operations:
    def __init__(self):
        self.router = APIRouter(
            prefix="/dql/operation",
            tags=["Database Query Language"]
        )

        # Register routes
        self.router.get("/get_data")(self.extract_table_data)
        self.router.get("/get_all_data")(self.extract_all_table_data)

    async def extract_table_data(self, request: Request, db: Session = Depends(get_db)):
        try:

            dql_obj = DQL_Operation(request=request, db=db)
            replica_db = await dql_obj.get_table_all_data()
            return replica_db
        except Exception as e:
            return api_response(500, message = f'An error occured: {str(e)}')
        
    async def extract_all_table_data(self, request: Request, db: Session = Depends(get_db)):
        try:

            dql_obj = DQL_Operation(request=request, db=db)
            replica_db = await dql_obj.get_all_table_all_data()
            return replica_db
        except Exception as e:
            return api_response(500, message = f'An error occured: {str(e)}')
        

# class DML_operations:
#     def __init__(self):
#         self.router = APIRouter(
#             prefix="/dql/operation",
#             tags=["Database Query Language"]
#         )

#         # Register routes
#         self.router.get("/get_data")(self.extract_table_data)
#         self.router.get("/get_all_data")(self.extract_all_table_data)

#     async def load_table_data(self, request: Request, db: Session = Depends(get_db)):
#         try:

#             dql_obj = DQL_Operation(request=request, db=db)
#             replica_db = await dql_obj.get_table_all_data()
#             return replica_db
#         except Exception as e:
#             return api_response(500, message = f'An error occured: {str(e)}')
        



class ETL_operations:
    def __init__(self):
        self.router = APIRouter(
            prefix="/etl/operation",
            tags=["Extract Transform Load Service"]
        )

        # Register routes
        self.router.get("/etl")(self.etl)
        # self.router.get("/get_all_data")(self.extract_all_table_data)

    async def etl(self, request: Request, db: Session = Depends(get_db)):
        try:

            etl_obj = ETLService(request=request, db=db)
            replica_db = await etl_obj.run()
            return replica_db
        except Exception as e:
            return api_response(500, message = f'An error occured: {str(e)}')
        





