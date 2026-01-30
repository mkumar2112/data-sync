from .imports_files import *


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
    
    def get_client_db(db_type, **kwarg):
        try:
            client = DBClientLoader.get_client(db_type=db_type)
            wrong_credentials = DBClientLoader.validate_credentials(db_type=db_type, **kwarg)
            if wrong_credentials:
                print('wrong Credentials ', wrong_credentials)
                return False, wrong_credentials
            
            params = DBClientLoader.make_valid_params(db_type=db_type, **kwarg)
            db_connnection = client.setup_connection(**params)
            if not db_connnection:
                return False, 'Wrong Credentials'
            
            is_connect, msg = client.connectdb(db_name=kwarg.get('database'))
            if not is_connect:
                return False , msg
            return client, client
        except Exception as e:
            return False , str(e)
        
    def setup_connection(db_type, **kwarg):
        client = DBClientLoader.get_client(db_type=db_type)
        params = DBClientLoader.make_valid_params(db_type=db_type, **kwarg)
        db_connnection = client.setup_connection(**params)
        if not db_connnection:
            return False, 'Wrong Credentials'
        return client, client



class Table_Operation:
    def __init__(self, db_type, db_name, client):
        self.client = client
        self.db_type = db_type
        self.db_name = db_name
        self.tableoperation = self.get_tableoperation(db_type=db_type)
    
    def get_tableoperation(self, db_type):
        if db_type == "mysql":
            return mysql_tableoperation(self.client.conn, self.db_name)
        if db_type == "postgres":
            return postgres_tableoperation(self.client.conn, self.db_name)
        if db_type == "mongo":
            return mongo_tableoperation(self.client.conn, self.db_name)
        raise Exception("Invalid or unsupported DB type")
    

    def get_table_metadata(self, table_name):
        try:
            table_operation_obj = self.tableoperation
            columns_and_constraints = table_operation_obj.get_table_metadata(table_name=table_name)
            return columns_and_constraints
        except Exception as e:
            return 


def make_json_serializable(data):
    # If dict → process each key/value
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}

    # If list/tuple/set → convert to list and process each item
    elif isinstance(data, (list, tuple, set)):
        return [make_json_serializable(v) for v in data]

    # MongoDB ObjectId
    elif isinstance(data, ObjectId):
        return str(data)

    # datetime/date
    elif isinstance(data, (datetime.datetime, datetime.date)):
        return data.isoformat()

    # Decimal → float
    elif isinstance(data, decimal.Decimal):
        return float(data)

    # bytes → decode
    elif isinstance(data, bytes):
        try:
            return data.decode()
        except:
            return str(data)

    # Everything else → return as is (int, float, bool, str, None)
    else:
        return data

    
class ddl_operation:
    def __init__(self, db_type, db_name, client):
        self.client = client
        self.db_type = db_type
        self.db_name = db_name
        self.get_ddl = self.get_ddl_d(db_type=db_type)
    
    def get_ddl_d(self, db_type):
        if db_type == "mysql":
            return mysql_ddl(self.client.conn, self.db_name)
        if db_type == "postgres":
            return postgres_ddl(self.client.conn, self.db_name)
        if db_type == "mongo":
            return mongo_ddl(self.client.conn, self.db_name)
        raise Exception("Invalid or unsupported DB type")
    
    def create_database(self, db_name):
        try:
            ddl_obj = self.get_ddl
            created_columns = ddl_obj.create_database(db_name = db_name)
            return created_columns
        except Exception as e:
            return 
    

    def create_table(self, table_name, columns):
        try:
            ddl_obj = self.get_ddl
            created_columns = ddl_obj.create_table( table_name= table_name, columns = columns)
            return created_columns
        except Exception as e:
            print(e)
            return 

    def create_constraints(self, table_name, constraints):
        try:
            ddl_obj = self.get_ddl
            # print(constraints)
            created_constraints = ddl_obj.add_table_constraints( table_name= table_name, constraints = constraints)
            return created_constraints
        except Exception as e:
            
            return 
    
    def truncate_table(self, table_name):
        try:
            return self.get_ddl.truncate_table(table_name=table_name)
        except Exception as e:
            return False , str(e)

class dql_operation:
    def __init__(self, db_type, db_name, client):
        self.client = client
        self.db_type = db_type
        self.db_name = db_name
        self.get_dql = self.get_dql_c(db_type=db_type)
    
    def get_dql_c(self, db_type):
        if db_type == "mysql":
            return mysql_dql(self.client.conn, self.db_name)
        if db_type == "postgres":
            return postgres_dql(self.client.conn, self.db_name)
        if db_type == "mongo":
            return mongo_dql(self.client.conn, self.db_name)
        raise Exception("Invalid or unsupported DB type")
    
    def get_all_data(self, table_name):
        try:
            return make_json_serializable(self.get_dql.extract_data(table_name=table_name))
        except Exception as e:
            return False , str(e)
    
    



class dml_operation:
    def __init__(self, db_type, db_name, client):
        self.client = client
        self.db_type = db_type
        self.db_name = db_name
        self.dml_opr = self.get_dml(db_type=db_type)
    
    def get_dml(self, db_type):
        if db_type == "mysql":
            return mysql_dml(self.client.conn, self.db_name)
        if db_type == "postgres":
            return postgres_dml(self.client.conn, self.db_name)
        if db_type == "mongo":
            return mongo_dml(self.client.conn, self.db_name)
        raise Exception("Invalid or unsupported DB type")
    
    def load_data_from_dataframe(self, table_name, df):
        try:
            
            return self.dml_opr.load_data(table_name=table_name, df=df)
        except Exception as e:
            return str(e)
        
    def load_data_from_dict(self, table_name, rows, columns):
        try:
            columns_list = [col.column_name for col in columns]
            return self.dml_opr.load_data_from_dict(table_name=table_name, rows=rows, columns_list=columns_list)
        except Exception as e:
            return str(e)
    
        
    # def get_all_data(self, table_name):
    #     try:
    #         return make_json_serializable(self.get_dml.extract_data(table_name=table_name))
    #     except Exception as e:
    #         return False , str(e)










