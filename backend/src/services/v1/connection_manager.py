from sqlalchemy.orm import Session
from backend.src.schemas.connection import *
from backend.src.crud.connection import create_connection, get_all_connections
from ...utils.utils import DBClientLoader, make_json_serializable, Table_Operation
from ...core.config import available_db_in_nosql, available_db_in_sql
from ...core.status import DBStatus, APIStatus
from ...crud.connection import CRUDBase
from sqlalchemy.orm import Session
from ...db.models.connection import *
from backend.src.db.session import get_db



class ConnectionManager:

    def add_connection(self, db: Session, payload: DatabaseConnectionCreate):
        return create_connection(db, payload)

    def list_connections(self, db: Session):
        obj_database_connection = CRUDBase(model=DatabaseConnection)
        list_of_db = obj_database_connection.get_all(db=db, schema=DatabaseConnectionOut)
        return list_of_db


connection_manager = ConnectionManager()

class ConnectionService:
    def __init__(self, db: Session = None):
        self.db = db

    async def validate_connection(self, payload):
        db_type = payload.get("db_type")
        payload.pop('db_type', None)
        return DBClientLoader.check_db_connection(db_type=db_type, **payload)
    
    async def connect_db_client(self, payload):
        db_type = payload.get("db_type")
        payload.pop('db_type', None)
        return DBClientLoader.connect_client_db(db_type=db_type, **payload)
    
    async def register_db_client(self, payload):
        try: 
            db_type = payload.get("db_type", None)
            payload.pop('db_type', None)
            db_name = payload.get("database", None)

            client, msg =  DBClientLoader.get_client_db(db_type=db_type, **payload)
            if not client:
                return {**DBStatus.get(1500).to_dict(),  'message': msg}
            
            filters = {
                "db_type": db_type,
                "host": payload.get("host"),
                "port": payload.get("port"),
                "username": payload.get("username"),
                "password": payload.get("password"),
                "database_name": payload.get("database"),
            }
            obj_database_connection = CRUDBase(model=DatabaseConnection)
            dbs = obj_database_connection.filter(db=self.db, per_page='all', **filters )
            if dbs and dbs.get('total') > 0:
                return {**APIStatus.get(200).to_dict(), 'message': f'Connection already established',  }
            
            db_detail = client.get_all_metadata(db_name=db_name)
            if not db_detail or not isinstance(db_detail, tuple)  or not len(db_detail) > 1 :
                return {**DBStatus.get(1500).to_dict(), "message": 'Not a valid data'}
            db_data = {
                    "name": payload.get("name"),
                    "db_type": db_type,
                    "host": payload.get("host"),
                    "port": payload.get("port"),
                    "username": payload.get("username"),
                    "password": payload.get("password"),
                    "database_name": payload.get("database"),
                    "connection_uri": payload.get("url") if db_type in available_db_in_nosql else None,
                    "config": None,
                    "db_metadata": make_json_serializable( db_detail[1]),
                    "auto_sync": False,
                    "sync_frequency": payload.get("sync_frequency", 'daily')
                }
            db_obj = DatabaseConnectionCreate(**db_data)
            created_obj = obj_database_connection.create(db=self.db , obj_in=db_obj)
            return {'id': created_obj.id, 'database-instance-id': created_obj.uuid,  **DBStatus.get(1000).to_dict(), 'message': 'Database Connected', 'payload': payload}
        except Exception as e:
            return {**APIStatus.get(500).to_dict(), 'message': str(e),}
    



class Database_Operation:
    def __init__(self, request, db, **kwargs):
        self.request =  request
        self.db = db

    async def sync_structure_db(self, payload):
        try: 
            db_instance_uuid =  self.request.headers.get("x-db-instance-id")
            if not db_instance_uuid:
                return {**APIStatus.get(400).to_dict(), 'message': 'Required X-DB-INSTANCE-ID'}
            
            DatabaseConnectionInstance = CRUDBase(model=DatabaseConnection)
            db_instance = DatabaseConnectionInstance.get(db=self.db, schema= None, uuid=db_instance_uuid)
            
            if not db_instance:
                return {**APIStatus.get(404).to_dict(), 'message': 'DB not found'}

            credentials = {
                # "db_type": db_instance.db_type,
                "database": db_instance.database_name
            }
            if db_instance.db_type in available_db_in_sql:
                credentials.update( {
                    "name": db_instance.name,
                    "host": db_instance.host,
                    "port": db_instance.port,
                    "username": db_instance.username,
                    "password": db_instance.password,
                })
            elif db_instance.db_type in available_db_in_nosql:
                credentials.update({
                    "name": db_instance.name,
                    "url": db_instance.connection_uri,
                })
            client, msg = DBClientLoader.get_client_db(db_type=db_instance.db_type, **credentials )
            if not client:
                return {**APIStatus.get(400).to_dict(), 'message': msg}

            table_operation_obj = Table_Operation(db_type=db_instance.db_type, db_name=db_instance.database_name,  client= client)
            
            table_list = client.show_tables()
            
            Table_crud = CRUDBase(model=DatabaseTable)
            Column_crud = CRUDBase(model=DatabaseColumn)
            table_metadata_list = []
            for table in table_list:
                table_metadata_obj = table_operation_obj.get_table_metadata(table_name=table)
                # print(table_metadata_obj)
                table_metadata = {
                    'connection_id':db_instance.id,   # ✅ required FK
                    'name':table,                    # ✅ table name
                    'table_type':"table",            # or "collection", "view" etc
                    'schema':table_metadata_obj.get("schema"),
                    'engine':table_metadata_obj.get("engine"),
                    'row_count':table_metadata_obj.get("row_count"),
                    'data_size':table_metadata_obj.get("data_size"),
                    'index_size':table_metadata_obj.get("index_size"),

                    # ✅ Save JSON metadata safely here
                    'options':{
                        "columns": table_metadata_obj.get("columns"),
                        "constraints": table_metadata_obj.get("constraints")
                    },

                    'last_synced_at':datetime.utcnow(),
                    # 'columns': table_metadata_obj.get('columns'),
                    # 'constraints': table_metadata_obj.get('constraints')
                }
                table_instance = Table_crud.get(db = self.db, schema= DatabaseTableOut, connection_id= db_instance.id, name=table )

                if not table_instance and table :
                    table_instance = Table_crud.create(db= self.db, obj_in=table_metadata )
                # elif table_instance:
                #     table_instance = Table_crud.update(db = self.db, db_obj= table_instance, obj_in=table_metadata )
                
                print(table_instance.table)
                # for columns in table_metadata_obj.get("columns"):
                #     pass
                table_metadata_list.append(table_metadata)


                # print(table, table_operation_obj.get_table_metadata(table_name=table))

            return {'table_metadata_list': table_metadata_list}
        except Exception as e:
            return {**APIStatus.get(500).to_dict(), 'message': str(e),}
        

    async def replica_db(self):
        try: 
            db_instance_uuid =  self.request.headers.get("x-db-instance-id")
            if not db_instance_uuid:
                return {**APIStatus.get(400).to_dict(), 'message': 'Required X-DB-INSTANCE-ID'}
            
            DatabaseConnectionInstance = CRUDBase(model=DatabaseConnection)
            db_instance = DatabaseConnectionInstance.get(db=self.db, schema= None, uuid=db_instance_uuid)

            return {}
        except Exception as e:
            return {**APIStatus.get(500).to_dict(), 'message': str(e),}
        
    async def db_structure(self, payload):
        try: 
            pass
            return {}
        except Exception as e:
            return {**APIStatus.get(500).to_dict(), 'message': str(e),}
   

