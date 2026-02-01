from sqlalchemy.orm import Session
from backend.src.schemas.connection import *
from backend.src.crud.connection import create_connection, get_all_connections
from ...data_hub.v1.data_hub_connection import DBClientLoader, make_json_serializable, Table_Operation, ddl_operation, dql_operation
from ...core.config import available_db_in_nosql, available_db_in_sql
from ...core.status import DBStatus, api_response
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
                return  api_response(200, message =f'Connection already established') 
            
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
            return api_response(500, message =str(e)) 
    
    async def delete_db(self, uuid):
        try:
            db_conn_crud = CRUDBase(DatabaseConnection)
            db_table_crud = CRUDBase(DatabaseTable)
            db_column_crud = CRUDBase(DatabaseColumn)
            db_constraint_crud = CRUDBase(DatabaseConstraint)

            replica_conn_crud = CRUDBase(ReplicaDatabaseConnection)
            replica_table_crud = CRUDBase(ReplicaDatabaseTable)
            replica_column_crud = CRUDBase(ReplicaDatabaseColumn)
            replica_constraint_crud = CRUDBase(ReplicaDatabaseConstraint)

            # -------------------------
            # Fetch DB connection
            # -------------------------
            db_instance = db_conn_crud.get(db=self.db, schema=None, uuid=uuid)
            if not db_instance:
                return api_response(404, "DB Not Found")
            replica_db_instance = replica_conn_crud.get(db=self.db, schema=None, original_connection_id=db_instance.id)
            connection_id = db_instance.id


            # =========================
            # DELETE REPLICA DATA FIRST
            # =========================

            if replica_db_instance:
                replica_connection_id = replica_db_instance.id
                # --- Replica Constraints ---
                replica_constraints = replica_constraint_crud.filter(
                    db=self.db, per_page='all',
                    filters={"connection_id": replica_connection_id}
                ).get("items", [])

                for rc in replica_constraints:
                    replica_constraint_crud.delete(db=self.db, id=rc.id)

                # --- Replica Columns ---
                replica_columns = replica_column_crud.filter(
                    db=self.db, per_page='all',
                    filters={"connection_id": replica_connection_id}
                ).get("items", [])

                for col in replica_columns:
                    replica_column_crud.delete(db=self.db, id=col.id)

                # --- Replica Tables ---
                replica_tables = replica_table_crud.filter(
                    db=self.db, per_page='all',
                    filters={"connection_id": replica_connection_id}
                ).get("items", [])

                for table in replica_tables:
                    replica_table_crud.delete(db=self.db, id=table.id)

                # --- Replica Connections ---
                replica_conns = replica_conn_crud.filter(
                    db=self.db, per_page='all',
                    filters={"original_connection_id": replica_connection_id}
                ).get("items", [])

                for conn in replica_conns:
                    replica_conn_crud.delete(db=self.db, id=conn.id)

            # =========================
            # DELETE MAIN DB DATA
            # =========================

            # --- Constraints ---
            constraints = db_constraint_crud.filter(
                db=self.db, per_page='all',
                filters={"connection_id": connection_id}
            ).get("items", [])

            for cons in constraints:
                db_constraint_crud.delete(db=self.db, id=cons.id)

            # --- Columns ---
            columns = db_column_crud.filter(
                db=self.db, per_page='all',
                filters={"connection_id": connection_id}
            ).get("items", [])

            for col in columns:
                db_column_crud.delete(db=self.db, id=col.id)

            # --- Tables ---
            tables = db_table_crud.filter(
                db=self.db, per_page='all',
                filters={"connection_id": connection_id}
            ).get("items", [])

            for table in tables:
                db_table_crud.delete(db=self.db, id=table.id)

            # --- DB Connection ---
            db_conn_crud.delete(db=self.db, id=connection_id)

            # -------------------------
            # Commit transaction
            # -------------------------
            self.db.commit()

            return api_response(200, "Deleted successfully")

        except Exception as e:
            self.db.rollback()
            return api_response(500, str(e))


class Database_Operation:
    def __init__(self, request, db, **kwargs):
        self.request =  request
        self.db = db

    async def sync_structure_db(self, payload):
        try: 
            db_instance_uuid =  self.request.headers.get("x-db-instance-id")
            if not db_instance_uuid:
                return api_response(400, message = 'Required X-DB-INSTANCE-ID')
            
            DatabaseConnectionInstance = CRUDBase(model=DatabaseConnection)
            db_instance = DatabaseConnectionInstance.get(db=self.db, schema= None, uuid=db_instance_uuid)
            
            if not db_instance:
                return api_response(404, message = 'DB not found')

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
                return api_response(400, message = 'DB not found')

            table_operation_obj = Table_Operation(db_type=db_instance.db_type, db_name=db_instance.database_name,  client= client)
            
            table_list = client.show_tables()
            
            Table_crud = CRUDBase(model=DatabaseTable)
            Column_crud = CRUDBase(model=DatabaseColumn)
            Constraint_crud = CRUDBase(model=DatabaseConstraint)

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
                table_instance_for_create_or_update = Table_crud.get(db = self.db, connection_id= db_instance.id, name=table )

                if not table_instance and table :
                    table_instance = Table_crud.create(db= self.db, obj_in=table_metadata )
                elif table_instance:
                    table_instance = Table_crud.update(db = self.db, db_obj= table_instance_for_create_or_update, obj_in=table_metadata )
                

                for column in table_metadata_obj.get("columns"):
                    column_payload = {
                        "connection_id": db_instance.id,
                        "table_id": table_instance.id,

                        "table_name": table,
                        "column_name": column.get("column_name"),

                        "data_type": column.get("data_type"),
                        "udt_name": column.get("udt_name"),
                        "is_nullable": True if column.get("is_nullable") in ["YES", True, 'true', 1] else False,
                        "is_primary_key": column.get("is_primary_key", False),
                        "is_unique": column.get("is_unique", False),
                        "default_value": column.get("default"),

                        "length": column.get("length"),
                        "precision": column.get("precision"),
                        "scale": column.get("scale"),
                        "enum_values": column.get("enum_values"),
                        "is_auto_increment": column.get("is_auto_increment"),
                        "is_unsigned": column.get("is_unsigned"),

                        "foreign_key": column.get("foreign_key"),  # optional
                        "metadata_json": column,  # ✅ store full raw column JSON
                    }

                    existing_column = Column_crud.get(
                        db=self.db,
                        table_id=table_instance.id,
                        column_name=column.get("column_name")
                    )

                    if existing_column:
                        Column_crud.update(
                            db=self.db,
                            db_obj=existing_column,
                            obj_in=column_payload
                        )

                    else:
                        Column_crud.create(
                            db=self.db,
                            obj_in=column_payload
                        )



                for constraint in table_metadata_obj.get("constraints"):

                    constraint_payload = {
                        "connection_id": db_instance.id,
                        "table_id": table_instance.id,

                        "schema": table_metadata_obj.get("schema"),
                        "table_name": table,

                        "constraint_name": constraint.get("constraint_name"),
                        "constraint_type": constraint.get("constraint_type"),

                        # extract columns from definition if not provided
                        "columns": constraint.get("columns"),

                        "referenced_table": constraint.get("referenced_table"),
                        "referenced_columns": constraint.get("referenced_columns"),

                        "on_delete": constraint.get("on_delete"),
                        "on_update": constraint.get("on_update"),

                        "is_deferrable": constraint.get("is_deferrable", False),
                        "initially_deferred": constraint.get("initially_deferred", False),

                        "using_index": constraint.get("using_index", False),
                        "index_name": constraint.get("index_name"),

                        "check_expression": constraint.get("check_expression"),

                        "is_enabled": True,
                        "is_validated": True,

                        "constraint_order": constraint.get("constraint_order", 0),

                        "metadata_json": constraint,   # ✅ raw JSON
                    }

                    # 🔎 check if constraint exists
                    existing_constraint = Constraint_crud.get(
                        db=self.db,
                        table_id=table_instance.id,
                        constraint_name=constraint.get("constraint_name")
                    )

                    if existing_constraint:
                        Constraint_crud.update(
                            db=self.db,
                            db_obj=existing_constraint,
                            obj_in=constraint_payload
                        )

                    else:
                        Constraint_crud.create(
                            db=self.db,
                            obj_in=constraint_payload
                        )

                table_metadata_list.append(table_metadata)

            return {'table_metadata_list': table_metadata_list}
        except Exception as e:
            return api_response(500, message = str(e))
        

    async def replica_db(self):
        try: 
            db_instance_uuid =  self.request.headers.get("x-db-instance-id")
            if not db_instance_uuid:
                return api_response(400, message = 'Required X-DB-INSTANCE-ID')
            
            DatabaseConnectionInstance = CRUDBase(model=DatabaseConnection)
            db_instance = DatabaseConnectionInstance.get(db=self.db, schema= None, uuid=db_instance_uuid)
            if not db_instance:
                return api_response(404, message = 'DB not found')
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
                return api_response(400, message = 'DB not found')

            
            # DatabaseConnectionInstance = CRUDBase(model=DatabaseConnection)
            # db_instance = DatabaseConnectionInstance.get(db=self.db, schema= None, uuid=db_instance_uuid)
            Table_crud = CRUDBase(model=DatabaseTable)
            Column_crud = CRUDBase(model=DatabaseColumn)
            Constraint_crud = CRUDBase(model=DatabaseConstraint)
            Replica_DatabaseConnection = CRUDBase(model=ReplicaDatabaseConnection)
            Replica_Table_crud = CRUDBase(model=ReplicaDatabaseTable)
            Replica_Column_crud = CRUDBase(model=ReplicaDatabaseColumn)
            Replica_Constraint_crud = CRUDBase(model=ReplicaDatabaseConstraint)

            replica_db_connection = db_instance.to_dict()


            for key in ['id', 'uuid', 'config', 'db_metadata', 'connection_status', 'last_connected_at', 'last_error', 'auto_sync', 'sync_frequency', 'last_sync_at', 'next_sync_at', 'created_by',  'updated_by', 'last_used_at', 'created_at', 'database_name' ]:
                replica_db_connection.pop(key, None)
            if db_instance.db_type == 'mysql':
                replica_db_connection.update({'original_connection_id': db_instance.id ,'name': f'{db_instance.db_type}_{db_instance.database_name}_{db_instance.id}', 'db_type': db_instance.db_type,  'host': 'localhost', 'port': 3306, 'username': 'root', 'password': 'monu', 'database_name': f'{db_instance.database_name}_{db_instance.username}_{db_instance.id}'})
            elif db_instance.db_type == 'postgres':
                replica_db_connection.update({'original_connection_id': db_instance.id ,'name': f'{db_instance.db_type}_{db_instance.database_name}_{db_instance.id}', 'db_type': db_instance.db_type,  'host': 'localhost', 'port': 5432, 'username': 'monuk', 'password': 'monu', 'database_name': f'{db_instance.database_name}_{db_instance.username}_{db_instance.id}'})
            elif db_instance.db_type == 'mongo':
                replica_db_connection.update({'original_connection_id': db_instance.id ,'name': f'{db_instance.db_type}_{db_instance.database_name}_{db_instance.id}', 'db_type': db_instance.db_type,  'connection_uri': 'mongodb://localhost:27017/', 'database_name': f'{db_instance.database_name}_{db_instance.username}_{db_instance.id}'})

            replica_db_instance = Replica_DatabaseConnection.get(db=self.db, schema= None, original_connection_id=db_instance.id)
            if not replica_db_instance:
                replica_db_instance = Replica_DatabaseConnection.create(db=self.db, obj_in=replica_db_connection)
            else:
                return {'message': 'Replica already created...'}

                replica_db_instance = Replica_DatabaseConnection.update(db=self.db,db_obj=replica_db_instance, obj_in=replica_db_connection)
            if replica_db_instance.db_type in available_db_in_sql:
                replica_credentials = {
                    "host": replica_db_instance.host,
                    "port": replica_db_instance.port,
                    "username": replica_db_instance.username,
                    "password": replica_db_instance.password,
                }
            elif replica_db_instance.db_type in available_db_in_nosql:
                replica_credentials = {
                    "url": replica_db_instance.connection_uri,
                }
            replica_client, msg = DBClientLoader.setup_connection(db_type=db_instance.db_type, **replica_credentials )
            ddl_operation_obj = ddl_operation(db_type=replica_db_instance.db_type, db_name=replica_db_instance.database_name, client=replica_client)
            flag, msg = ddl_operation_obj.create_database(db_name=replica_db_instance.database_name)

            if replica_db_instance.db_type not in available_db_in_sql:
                return {'message': 'DB Replica has been created....'}
            # print(flag, '---------------')
            if flag:
                replica_credentials['database'] = replica_db_instance.database_name
                replica_client, msg = DBClientLoader.setup_connection(db_type=replica_db_instance.db_type, **replica_credentials )
                ddl_operation_obj = ddl_operation(db_type=replica_db_instance.db_type, db_name=replica_db_instance.name, client=replica_client)
            tables = Table_crud.filter(db=self.db, page=1, per_page='all', connection_id= db_instance.id )
            for table in tables.get('items'):
                replica_table = table.to_dict()
                for key in ['id', 'connection_id', 'table_type',  'options',  'last_synced_at', 'created_at']:
                    replica_table.pop(key, None)
                replica_table['connection_id'] = replica_db_instance.id
                replica_table['original_table_id'] = table.id
                replica_table_instance = Replica_Table_crud.get(db=self.db, schema= None, original_table_id=table.id)
                if not replica_table_instance:
                    replica_table_instance = Replica_Table_crud.create(db=self.db, obj_in=replica_table)


            # for table in tables.get('items'):
                columns = Column_crud.filter(db=self.db, page=1, per_page='all', table_id=table.id)
                replica_table_instance = Replica_Table_crud.get(db=self.db, schema= None, original_table_id=table.id)     
                for col in columns.get('items'):
                    replica_column = col.to_dict()
                    for key in ['id', 'connection_id', 'table_id', 'foreign_key', 'metadata_json', 'created_at', 'updated_at']:
                        replica_column.pop(key, None)
                    replica_column['connection_id'] = replica_db_instance.id
                    replica_column['table_id'] = replica_table_instance.id
                    replica_column['original_column_id'] = col.id
                    replica_column['enum_values'] = col.enum_values
                    replica_column['metadata_json'] = {}
                    replica_column_instance = Replica_Column_crud.get(db=self.db, schema= None, original_column_id=col.id)
                    if not replica_column_instance:
                        replica_column_instance = Replica_Column_crud.create(db=self.db, obj_in=replica_column)
                replica_columns = Replica_Column_crud.filter(db=self.db, page=1, per_page='all', table_id=replica_table_instance.id)
                flag, msg = ddl_operation_obj.create_table(table_name=replica_table_instance.name, columns=replica_columns.get('items'))
                print('--------------------------------------------->', flag, msg)
                if not flag:
                    break
            for table in tables.get('items'):
                constraints = Constraint_crud.filter(db=self.db, page=1, per_page='all', table_id=table.id)
                replica_table_instance = Replica_Table_crud.get(db=self.db, schema= None, original_table_id=table.id)     
                for cons in constraints.get('items'):
                    replica_constraint = cons.to_dict()
                    for key in ['id', 'connection_id', 'table_id', 'created_at', 'updated_at']:
                        replica_constraint.pop(key, None)
                    replica_constraint['connection_id'] = replica_db_instance.id
                    replica_constraint['table_id'] = replica_table_instance.id
                    replica_constraint['original_constraint_id'] = cons.id
                    # replica_constraint['metadata_json'] = {}
                    replica_constraint_instance = Replica_Constraint_crud.get(db=self.db, schema= None, original_constraint_id=cons.id)
                    if replica_constraint_instance:
                        replica_constraint_instance = Replica_Constraint_crud.update(db=self.db, db_obj=replica_constraint_instance, obj_in=replica_constraint)
                    else:
                        replica_constraint_instance = Replica_Constraint_crud.create(db=self.db, obj_in=replica_constraint)
            
            replica_constraints = Replica_Constraint_crud.filter(db=self.db, page=1, per_page='all', connection_id=replica_db_instance.id)
            # flag, msg = ddl_operation_obj.create_constraints(table_name=None, constraints=replica_constraints.get('items'))
            if flag:
                return {'message': 'DB Replica has been created....'}
            if not flag:
                if replica_db_instance:
                    replica_connection_id = replica_db_instance.id
                    # --- Replica Constraints ---
                    replica_constraints = Replica_Constraint_crud.filter(
                        db=self.db, per_page='all',
                        filters={"connection_id": replica_connection_id}
                    ).get("items", [])

                    for rc in replica_constraints:
                        Replica_Constraint_crud.delete(db=self.db, id=rc.id)

                    # --- Replica Columns ---
                    replica_columns = Replica_Column_crud.filter(
                        db=self.db, per_page='all',
                        filters={"connection_id": replica_connection_id}
                    ).get("items", [])

                    for col in replica_columns:
                        Replica_Column_crud.delete(db=self.db, id=col.id)

                    # --- Replica Tables ---
                    replica_tables = Replica_Table_crud.filter(
                        db=self.db, per_page='all',
                        filters={"connection_id": replica_connection_id}
                    ).get("items", [])

                    for table in replica_tables:
                        Replica_Table_crud.delete(db=self.db, id=table.id)

                    # --- Replica Connections ---
                    replica_conns = Replica_DatabaseConnection.filter(
                        db=self.db, per_page='all',
                        filters={"original_connection_id": replica_connection_id}
                    ).get("items", [])

                    for conn in replica_conns:
                        Replica_DatabaseConnection.delete(db=self.db, id=conn.id)

                ok = client.deletedb(replica_db_instance.database_name)
                
                return {'message': f'Something went wrong......{msg}'}
            
        except Exception as e:
            return api_response(500, message = str(e))

    async def sync_db_structure_to_db(self):
        try:
            # =========================
            # CONFIG
            # =========================
            COLUMN_KEYS = [
                "name", "data_type", "is_nullable",
                "default", "length", "precision", "scale"
            ]

            CONSTRAINT_KEYS = [
                "constraint_type", "column_name",
                "referenced_table", "referenced_column",
                "on_delete", "on_update"
            ]

            def is_changed(src, tgt, keys):
                for k in keys:
                    if getattr(src, k, None) != getattr(tgt, k, None):
                        return True
                return False

            # =========================
            # VALIDATION
            # =========================
            db_instance_uuid = self.request.headers.get("x-db-instance-id")
            if not db_instance_uuid:
                return api_response(400, "Required X-DB-INSTANCE-ID")

            db_instance = CRUDBase(DatabaseConnection).get(
                db=self.db, schema=None, uuid=db_instance_uuid
            )
            if not db_instance:
                return api_response(404, "DB not found")

            replica_db = CRUDBase(ReplicaDatabaseConnection).get(
                db=self.db, schema=None, original_connection_id=db_instance.id
            )
            if not replica_db:
                return api_response(500, "Replica DB not found")

            # =========================
            # CRUDS
            # =========================
            Table_crud = CRUDBase(DatabaseTable)
            Column_crud = CRUDBase(DatabaseColumn)
            Constraint_crud = CRUDBase(DatabaseConstraint)

            Replica_Table_crud = CRUDBase(ReplicaDatabaseTable)
            Replica_Column_crud = CRUDBase(ReplicaDatabaseColumn)
            Replica_Constraint_crud = CRUDBase(ReplicaDatabaseConstraint)

            # =========================
            # CHANGE COLLECTOR
            # =========================
            changes = {
                "columns_create": [],
                "columns_update": [],
                "columns_delete": [],
                "constraints_create": [],
                "constraints_update": [],
                "constraints_delete": [],
            }

            # =========================
            # FETCH TABLES
            # =========================
            tables = Table_crud.filter(
                db=self.db, page=1, per_page="all",
                connection_id=db_instance.id
            ).get("items", [])

            # =========================
            # DIFF PHASE (NO WRITES)
            # =========================
            for table in tables:
                replica_table = Replica_Table_crud.get(
                    db=self.db, schema=None,
                    original_table_id=table.id
                )
                if not replica_table:
                    continue

                # ---------- Columns ----------
                original_cols = Column_crud.filter(
                    db=self.db, page=1, per_page="all",
                    table_id=table.id
                ).get("items", [])

                replica_cols = Replica_Column_crud.filter(
                    db=self.db, page=1, per_page="all",
                    table_id=replica_table.id
                ).get("items", [])

                replica_col_map = {
                    c.original_column_id: c for c in replica_cols
                }

                original_col_ids = set()

                for col in original_cols:
                    original_col_ids.add(col.id)
                    replica_col = replica_col_map.get(col.id)

                    if not replica_col:
                        changes["columns_create"].append((replica_table, col))
                    elif is_changed(col, replica_col, COLUMN_KEYS):
                        changes["columns_update"].append((replica_col, col))

                for rc in replica_cols:
                    if rc.original_column_id not in original_col_ids:
                        changes["columns_delete"].append(rc)

                # ---------- Constraints ----------
                original_cons = Constraint_crud.filter(
                    db=self.db, page=1, per_page="all",
                    table_id=table.id
                ).get("items", [])

                replica_cons = Replica_Constraint_crud.filter(
                    db=self.db, page=1, per_page="all",
                    table_id=replica_table.id
                ).get("items", [])

                replica_cons_map = {
                    c.original_constraint_id: c for c in replica_cons
                }

                original_cons_ids = set()

                for cons in original_cons:
                    original_cons_ids.add(cons.id)
                    replica_con = replica_cons_map.get(cons.id)

                    if not replica_con:
                        changes["constraints_create"].append((replica_table, cons))
                    elif is_changed(cons, replica_con, CONSTRAINT_KEYS):
                        changes["constraints_update"].append((replica_con, cons))

                for rc in replica_cons:
                    if rc.original_constraint_id not in original_cons_ids:
                        changes["constraints_delete"].append(rc)

            # =========================
            # APPLY CHANGES (WRITE PHASE)
            # =========================

            # ---- Columns CREATE ----
            # for table, col in changes["columns_create"]:
            #     data = col.to_dict()
            #     for k in ["id", "connection_id", "table_id", "created_at", "updated_at"]:
            #         data.pop(k, None)

            #     data.update({
            #         "connection_id": replica_db.id,
            #         "table_id": table.id,
            #         "original_column_id": col.id,
            #         "metadata_json": {}
            #     })
            #     Replica_Column_crud.create(db=self.db, obj_in=data)

            # # ---- Columns UPDATE ----
            # for replica_col, col in changes["columns_update"]:
            #     data = col.to_dict()
            #     for k in ["id", "connection_id", "table_id", "created_at", "updated_at"]:
            #         data.pop(k, None)

            #     Replica_Column_crud.update(
            #         db=self.db,
            #         db_obj=replica_col,
            #         obj_in=data
            #     )

            # ---- Columns DELETE ----
            # for rc in changes["columns_delete"]:
            #     Replica_Column_crud.remove(db=self.db, id=rc.id)

            # # ---- Constraints CREATE ----
            # for table, cons in changes["constraints_create"]:
            #     data = cons.to_dict()
            #     for k in ["id", "connection_id", "table_id", "created_at", "updated_at"]:
            #         data.pop(k, None)

            #     data.update({
            #         "connection_id": replica_db.id,
            #         "table_id": table.id,
            #         "original_constraint_id": cons.id
            #     })
            #     Replica_Constraint_crud.create(db=self.db, obj_in=data)

            # # ---- Constraints UPDATE ----
            # for replica_cons, cons in changes["constraints_update"]:
            #     data = cons.to_dict()
            #     for k in ["id", "connection_id", "table_id", "created_at", "updated_at"]:
            #         data.pop(k, None)

            #     Replica_Constraint_crud.update(
            #         db=self.db,
            #         db_obj=replica_cons,
            #         obj_in=data
            #     )

            # # ---- Constraints DELETE ----
            # for rc in changes["constraints_delete"]:
            #     Replica_Constraint_crud.remove(db=self.db, id=rc.id)
            # print(changes)
            changes['columns_create'] = [(a.to_dict(), b.to_dict()) for a, b in changes['columns_create']]
            changes['columns_update'] = [(a.to_dict(), b.to_dict()) for a, b in changes['columns_update']]
            changes['columns_delete'] = [(a.to_dict(), b.to_dict()) for a, b in changes['columns_delete']]
            changes['constraints_create'] = [(a.to_dict(), b.to_dict()) for a, b in changes['constraints_create']]
            changes['constraints_update'] = [(a.to_dict(), b.to_dict()) for a, b in changes['constraints_update']]
            changes['constraints_delete'] = [(a.to_dict(), b.to_dict()) for a, b in changes['constraints_delete']]
            return api_response(
                200,
                message="Schema diff applied successfully",
                data=changes
            )

        except Exception as e:
            return api_response(500, message=str(e))


class DQL_Operation:
    def __init__(self, request, db, **kwargs):
        self.request =  request
        self.db = db
        self.dql_opr = None

    def validate_db_uuid(self):
        try:
            db_instance_uuid =  self.request.headers.get("x-db-instance-id")
            if not db_instance_uuid:
                return None, api_response(400, message = 'Required X-DB-INSTANCE-ID')
            
            DatabaseConnectionInstance = CRUDBase(model=DatabaseConnection)
            db_instance = DatabaseConnectionInstance.get(db=self.db, schema= None, uuid=db_instance_uuid)
            
            if not db_instance:
                return None, api_response(404, message = 'DB not found')
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

            dql_operation_obj = dql_operation(db_type=db_instance.db_type, db_name=db_instance.database_name, client=client)

            if not dql_operation_obj:
                return None, api_response(400, message = 'DB connection unable to connect')

            if not client:
                return None, api_response(400, message = 'DB not found')
            
            self.dql_opr =dql_operation_obj
            return (client, db_instance), None
        except Exception as e:
            return None, api_response(500, message = str(e))

    async def get_table_all_data(self):
        try:
            query_p = self.request.query_params
            table_name = query_p.get('table_name')
            client_and_db_inst, api_r = self.validate_db_uuid()
            if api_r:
                return api_r
            # client , db_instance = client_and_db_inst
            flag , data = self.dql_opr.get_all_data(table_name=table_name)

            if not flag:
                return api_response(status_code=400, message=data)
            return api_response(status_code=200, data=data, message='Successfuly fetched')
        except Exception as e:
            return api_response(status_code=500, message=str(e))
        
    async def get_all_table_all_data(self):
        try:
            # query_p = self.request.query_params
            # table_name = query_p.get('table_name')
            client_and_db_inst, api_r = self.validate_db_uuid()
            if api_r:
                return api_r
            client , db_instance = client_and_db_inst
            table_crud = CRUDBase(model=DatabaseTable)
            tables =  table_crud.filter(
                db=self.db, page=1, per_page="all",
                connection_id=db_instance.id
            ).get("items", [])

            tables_data_json = {}
            for table in tables:
                flag , data = self.dql_opr.get_all_data(table_name=table.name)
                tables_data_json[table.name] = data
            if not flag:
                return api_response(status_code=400, message=data)
            return api_response(status_code=200, data=tables_data_json, message='Successfuly fetched')
        except Exception as e:
            return api_response(status_code=500, message=str(e))


class DML_Operation:
    def __init__(self, request, db, **kwargs):
        self.request =  request
        self.db = db
        self.dql_opr = None
        self.dml_opr = None
        self.DQL_Operation_obj = DQL_Operation(request=request, db=db, **kwargs)

    def validate_db_uuid(self):
        try:
            db_instance_uuid =  self.request.headers.get("x-db-instance-id")
            if not db_instance_uuid:
                return None, api_response(400, message = 'Required X-DB-INSTANCE-ID')
            
            DatabaseConnectionInstance = CRUDBase(model=DatabaseConnection)
            db_instance = DatabaseConnectionInstance.get(db=self.db, schema= None, uuid=db_instance_uuid)
            
            if not db_instance:
                return None, api_response(404, message = 'DB not found')
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

            dql_operation_obj = dql_operation(db_type=db_instance.db_type, db_name=db_instance.name, client=client)

            if not dql_operation_obj:
                return None, api_response(400, message = 'DB connection unable to connect')

            if not client:
                return None, api_response(400, message = 'DB not found')
            
            self.dql_opr =dql_operation_obj
            return (client, db_instance), None
        except Exception as e:
            return None, api_response(500, message = str(e))

    async def load(self):
        try:
            query_p = self.request.query_params
            table_name = query_p.get('table_name')
            client_and_db_inst, api_r = self.validate_db_uuid()
            if api_r:
                return api_r
            # client , db_instance = client_and_db_inst
            flag , data = self.dql_opr.get_all_data(table_name=table_name)

            if not flag:
                return api_response(status_code=400, message=data)
            return api_response(status_code=200, data=data, message='Successfuly fetched')
        except Exception as e:
            return api_response(status_code=500, message=str(e))
       



























