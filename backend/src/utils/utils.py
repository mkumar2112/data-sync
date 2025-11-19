from ..data_hub.mysql.db_connection import connectsql as mysql_connectsql
from ..data_hub.postgres.db_connection import connectsql as postgres_connectsql
from ..data_hub.mongo.db_connection import connectsql as mongo_connectsql
from ..core.config import available_db_in_nosql, available_db_in_sql




class DBClientLoader:

    @staticmethod
    def get_client(db_type):
        if db_type == "mysql":
            return mysql_connectsql()
        if db_type == "postgres":
            return postgres_connectsql()
        if db_type == "mongo":
            return mongo_connectsql()
        raise Exception("Invalid or unsupported DB type")
    
    @staticmethod
    def validate_credentials(db_type, **payload):
        if db_type in available_db_in_sql and (not payload.get('host') or not payload.get('port') or not payload.get('username') or not payload.get('password') or not payload.get('database')):
            return {'message': 'Not have valid json', 'json_example': {
                "name": "Local Postgres",
                "db_type": "postgres",
                "host": "localhost",
                "port": 5432,
                "username": "username",
                "password": "********",
                "database": "school"
            }}
        elif db_type in available_db_in_nosql and not payload.get('url') or not payload.get('database'):
            return {'message': 'Not have valid json', 'json_example': {
                "name": "Local Collection",
                "db_type": "mongo",
                "url": "url",
                "database": "school"
            }}
    
    @staticmethod
    def make_valid_params(db_type,  **kwarg):
        params = {}
        if db_type in available_db_in_sql:
            params = {
                'host':kwarg.get('host'),
                'port':kwarg.get('port'),
                'user':kwarg.get('username'),
                'password':kwarg.get('password'),
                'database': kwarg.get('database')
            }
        elif db_type in available_db_in_nosql:
            params = {
                'url':kwarg.get('url'),
                'database': kwarg.get('database')
            }
        return params
    
    @staticmethod
    def check_db_connection(db_type, **kwarg):
        try:
            client = DBClientLoader.get_client(db_type=db_type)
            wrong_credentials = DBClientLoader.validate_credentials(db_type=db_type, **kwarg)
            if wrong_credentials:
                return wrong_credentials
            
            params = DBClientLoader.make_valid_params(db_type=db_type, **kwarg)
            db_connnection = client.setup_connection(**params)
            if not db_connnection:
                return {'message': 'Wrong Credentials.', 'payload': kwarg}
            
            db_exist = client.db_exists(db_name=kwarg.get('database'))
            if db_exist:
                return {'message': 'Database exist in DB.'}
            else:
                return {'message': 'Database exist in DB.', 'payload': kwarg}
        except Exception as e:
            return {'message': f'An error occured in check db connection: {str(e)}'}
    
    def connect_client_db(db_type, **kwarg):
        try:
            client = DBClientLoader.get_client(db_type=db_type)
            wrong_credentials = DBClientLoader.validate_credentials(db_type=db_type, **kwarg)
            if wrong_credentials:
                return wrong_credentials
            
            params = DBClientLoader.make_valid_params(db_type=db_type, **kwarg)
            db_connnection = client.setup_connection(**params)
            if not db_connnection:
                return {'message': 'Wrong Credentials.', 'payload': kwarg}
            
            is_connect, msg = client.connectdb(db_name=kwarg.get('database'))
            if not is_connect:
                return {'message': msg, 'payload': kwarg}

            tables_list = client.show_tables()
            return {'message': 'DB Connected', 'tables': tables_list}
        except Exception as e:
            return {'message': f'An error occured in check db connection: {str(e)}'}
    

    
