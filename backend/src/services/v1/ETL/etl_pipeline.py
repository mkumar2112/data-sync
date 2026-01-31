from ....core.config import available_db_in_nosql, available_db_in_sql
from ....core.status import DBStatus, api_response
from ....crud.connection import CRUDBase
from ....db.models.connection import *
from ....data_hub.v1.data_hub_connection import DBClientLoader, make_json_serializable, Table_Operation, ddl_operation, dql_operation, dml_operation
from .extract import *
from .transform import *



class ETLService:

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

    
    async def run(self):
        try:
            client_and_db_inst, api_r = self.validate_db_uuid()
            if api_r:
                return api_r
            client , db_instance = client_and_db_inst

            replica_db_crud = CRUDBase(model=ReplicaDatabaseConnection)
            table_crud = CRUDBase(model=DatabaseTable)
            column_crud = CRUDBase(model=DatabaseColumn)
            replica_table_crud = CRUDBase(model=ReplicaDatabaseTable)
            replica_column_crud = CRUDBase(model=ReplicaDatabaseColumn)

            replica_db_instance = replica_db_crud.get(db=self.db, schema= None, original_connection_id=db_instance.id)
            tables =  table_crud.filter(
                db=self.db, page=1, per_page="all",
                connection_id=db_instance.id
            ).get("items", [])
            replica_tables =  replica_table_crud.filter(
                db=self.db, page=1, per_page="all",
                connection_id=replica_db_instance.id
            ).get("items", [])
            credentials = {}
            if replica_db_instance.db_type in available_db_in_sql:
                credentials.update( {
                    "name": replica_db_instance.name,
                    "host": replica_db_instance.host,
                    "port": replica_db_instance.port,
                    "username": replica_db_instance.username,
                    "password": replica_db_instance.password,
                    "database": replica_db_instance.database_name
                })
            elif replica_db_instance.db_type in available_db_in_nosql:
                credentials.update({
                    "database": replica_db_instance.database_name,
                    "url": replica_db_instance.connection_uri,
                })
            replica_client, msg = DBClientLoader.get_client_db(db_type=replica_db_instance.db_type, **credentials )

            ExtractService_obj = ExtractService(dql_opr=self.dql_opr)
            flag, data = await ExtractService_obj.get_all_table_data(table_list=tables)
            if not flag:
                return api_response(status_code=400, data=data)
            
            TransformService_obj = TransformService()
            dml_opr = dml_operation(db_type=replica_db_instance.db_type, db_name=replica_db_instance.database_name, client=replica_client)
            ddl_opr = ddl_operation(db_type=replica_db_instance.db_type, db_name=replica_db_instance.database_name, client=replica_client)
            transformed_data = {}
            for table in tables:
                flag, msg = ddl_opr.truncate_table(table.name)
                
                if flag:
                    columns = column_crud.filter(
                        db=self.db, page=1, per_page="all",
                        table_id=table.id, sort_by = 'id'
                    )
                    # print(columns.get('items'), data.get(table.name))
                    # t_data = TransformService_obj.run(columns.get('items'), payload= data.get(table.name))
                    # transformed_data[table.name] = t_data
                    # print(transformed_data)
                    dml_opr.load_data_from_dict(table_name=table.name, columns=columns.get('items'), rows=data.get(table.name))
            if not flag:
                return api_response(status_code=400, message=data)
            return api_response(status_code=200, data=data, message='Successfuly fetched')
        except Exception as e:
            print('---->', e)
            return api_response(status_code=500, message=str(e))
        
    
    # async def run(self):
    #     self.extracted_data = await ExtractService(self.request).run()
    #     self.transformed_data = TransformService().run(self.extracted_data)
    #     result = LoadService().run(self.transformed_data)
    #     return result
