import mysql.connector
import os

ENTRIES = int(os.getenv('DATA_ENTRIES',50))

def escape_name(name):
    if not name:  # Handle empty or None names
        raise ValueError("The name to escape cannot be None or empty.")
    return f"`{name}`"


class connectsql:
    def __init__(self):
        self.conn = None
        self.connection_details = {}

    def setup_connection(self, host=None, port=3306,  user=None, password=None, database=None):
        try:
            if not host or not user or not password:
                raise ValueError("Host, user, and password are required for MySQL.")
            self.connection_details = {
                'host': host,
                'user': user,
                'port': port,
                'password': password,
                'database': database if database else None
            }
            self.conn = mysql.connector.connect(**self.connection_details)
            self.conn.ping(reconnect=True)
            return True
        except Exception as e:
            return False
        
    def connectdb(self, db_name):
        try:
            if not self.conn:
                raise ValueError("Database connection is not established. Call setup_connection first.")
            if self.db_exists(db_name):
                cursor = self.conn.cursor()
                cursor.execute(f"USE {db_name}")  # Valid for MySQL only
                return True, f"Connected to MySQL database: {db_name}"
            return False, f"Failed to connect database {db_name}: Database not exist..."
        except Exception as e:
            return False, str(e)
        
    def get_mysql_version(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            return True, version
        except Exception as e:
            return False, str(e)

    def get_server_status(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SHOW STATUS")
            status = cursor.fetchall()  # list of (Variable_name, Value)
            return True, status
        except Exception as e:
            return False, str(e)
        
    def get_global_variables(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SHOW VARIABLES")
            variables = cursor.fetchall()  # list of (Variable_name, Value)
            return True, variables
        except Exception as e:
            return False, str(e)

    def get_storage_engines(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SHOW ENGINES")
            engines = cursor.fetchall()
            return True, engines
        except Exception as e:
            return False, str(e)

    def get_database_metadata(self, db_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    SCHEMA_NAME,
                    DEFAULT_CHARACTER_SET_NAME,
                    DEFAULT_COLLATION_NAME,
                    SQL_PATH
                FROM INFORMATION_SCHEMA.SCHEMATA
                WHERE SCHEMA_NAME = %s
            """, (db_name,))

            result = cursor.fetchone()
            return True, result
        except Exception as e:
            return False, str(e)

    def get_all_metadata(self, db_name):
        try:
            all_meta = {}

            # 1. MySQL Version
            status, version = self.get_mysql_version()
            all_meta["version"] = version if status else f"Error: {version}"

            # 2. Server Status
            status, server_status = self.get_server_status()
            all_meta["server_status"] = (
                {k: v for k, v in server_status} if status else f"Error: {server_status}"
            )

            # 3. Global Variables
            status, variables = self.get_global_variables()
            all_meta["global_variables"] = (
                {k: v for k, v in variables} if status else f"Error: {variables}"
            )

            # 4. Storage Engines
            status, engines = self.get_storage_engines()
            if status:
                all_meta["storage_engines"] = [
                    {
                        "Engine": row[0],
                        "Support": row[1],
                        "Comment": row[2],
                        "Transactions": row[3],
                        "XA": row[4],
                        "Savepoints": row[5],
                    }
                    for row in engines
                ]
            else:
                all_meta["storage_engines"] = f"Error: {engines}"

            # 5. Database Metadata
            status, db_meta = self.get_database_metadata(db_name)
            if status and db_meta:
                all_meta["database"] = {
                    "schema": db_meta[0],
                    "charset": db_meta[1],
                    "collation": db_meta[2],
                    "sql_path": db_meta[3]
                }
            else:
                all_meta["database"] = f"Error: {db_meta}"

            return True, all_meta

        except Exception as e:
            return False, str(e)


    def db_exists(self, db_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
            db_exit = bool(cursor.fetchone()) 
            return db_exit
        except Exception as e:
            return False
    
    def show_tables(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SHOW TABLES")
            tables = cursor.fetchall() or []
            tables_list = [table[0] for table in tables]
            return tables_list
        except Exception as e:
            return False
    
    def create_db(self, db_name):
        try:
            self.conn.autocommit = True
            cursor = self.conn.cursor()
            cursor.execute(f"CREATE DATABASE {db_name}")
            # # print(f"Database {db_name} created.")
            self.conn.autocommit = False
            return True, f"Database {db_name} created."
        except Exception as e:
            return False, f"Error creating database {db_name}: {e}"

    def deletedb(self, db_name):
        try:
            if not self.conn:
                raise ValueError("Database connection is not established. Call setup_connection first.")
            # cursor = self.conn.cursor()
            # cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
            return True
        except Exception as e:
            return False

    def close_connection(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            print(f"Error closing connection: {e}")




class tableoperation:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name
    
    def get_table_metadata(self, table_name):
        try:
            cursor = self.conn.cursor()

            metadata_query = """
            SELECT 
                TABLE_SCHEMA,
                ENGINE,
                TABLE_ROWS,
                DATA_LENGTH,
                INDEX_LENGTH,
                TABLE_TYPE,
                CREATE_TIME,
                UPDATE_TIME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s;
            """

            cursor.execute(metadata_query, (table_name,))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None
            columns_constraints = self.get_columns_and_constraints(table_name=table_name)
            return {
                "schema": row[0],                  # public / dbo equivalent
                "engine": row[1],                  # InnoDB, MyISAM
                "row_count": row[2],               # Approx rows
                "data_size": row[3],               # In bytes
                "index_size": row[4],              # In bytes
                "table_type": row[5],              # BASE TABLE / VIEW
                "options": {
                    "created_at": str(row[6]) if row[6] else None,
                    "updated_at": str(row[7]) if row[7] else None
                }, **columns_constraints
            }

        except Exception as e:
            return {"error": str(e)}


    def get_columns_and_constraints(self, table_name):
        try:
            cursor = self.conn.cursor()  # ✅ don't use dictionary for portability

            # ✅ 1. Get Column Info
            column_query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COLUMN_KEY,
                EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s;
            """

            cursor.execute(column_query, (table_name,))
            columns = cursor.fetchall()

            formatted_columns = [
                {
                    "column_name": row[0],
                    "data_type": row[1],
                    "is_nullable": row[2],
                    "default": row[3],
                    "column_key": row[4],
                    "extra": row[5],
                }
                for row in columns
            ]

            # ✅ 2. Get Constraints (PK, FK, UNIQUE)
            constraint_query = """
            SELECT 
                tc.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE,
                kcu.COLUMN_NAME,
                kcu.REFERENCED_TABLE_NAME,
                kcu.REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
            WHERE tc.TABLE_SCHEMA = DATABASE()
            AND tc.TABLE_NAME = %s;
            """

            cursor.execute(constraint_query, (table_name,))
            constraints = cursor.fetchall()

            formatted_constraints = [
                {
                    "constraint_name": row[0],
                    "constraint_type": row[1],   # PRIMARY KEY, FOREIGN KEY, UNIQUE
                    "column_name": row[2],
                    "referenced_table": row[3],
                    "referenced_column": row[4],
                }
                for row in constraints
            ]

            cursor.close()

            return {
                "columns": formatted_columns,
                "constraints": formatted_constraints
            }

        except Exception as e:
            return {"error": str(e)}

        
#     def gettableData(self, table_name):
#         try:
#             table_name = escape_name(table_name)
#             cursor = self.conn.cursor()
#             query = f"SELECT * FROM {table_name};"
#             cursor.execute(query)
#             result = cursor.fetchall()
#             cursor.close()
#             return result
#         except Exception as e:
#             return f"An error occurred: {str(e)}"
        

#     def createtable(self, table_name, columns):
#         try:
#             table_names = escape_name(table_name)
#             cursor = self.conn.cursor()
#             # List to hold column definitions and constraints
#             column_definitions = []
#             constraints = []
                
#             # Iterate over columns to build the table schema
#             for col in columns:
#                 col_name = escape_name(col.col_name)  # Escape column name

#                 if col.col_name == 'id':
#                     column_definitions.append(f"{col_name} {col.get_db_column_type()} PRIMARY KEY")
#                 else:
#                     column_definitions.append(f"{col_name} {col.get_db_column_type()}")

#             # Add constraints (if any)
#             if constraints:
#                 column_definitions.extend(constraints)

#             # Combine all definitions into a single string
#             column_definitions_str = ", ".join(column_definitions)

#             # Execute the query to create the table
#             try:
#                 cursor.execute(f"CREATE TABLE {table_names} ({column_definitions_str});")
#                 self.conn.commit()
#             except Exception as e:
#                 self.conn.rollback()
#                 # # print('Table is not created error:', e)
#                 return False, f'Table is not Created Error: {e}'
#             finally:
#                 cursor.close()
#             return True, 'Table is created'

        
#         except Exception as e:
#             return f"Error creating table {table_name}: {e}"

#     def remove_table_columns(self, db_type, db_name, table_name, columns):
#         try:
#             cursor = self.conn.cursor()
#             db_instance = DynamicDB.objects.get(db_name=db_name)
#             table_instance = Table.objects.get(table_name=table_name, db_instance = db_instance)
#             table_names = escape_name(db_type,table_name)  # Escape column name
#             for col in columns:
#                 col_instance = Col.objects.get(col_name=col, table=table_instance)
#                 col = escape_name(db_type,col)  # Escape column name
#                 cursor.execute(f"ALTER TABLE {table_names} DROP COLUMN {col};")
#                 self.conn.commit()
#                 col_instance.delete()

#             return True
#         except Exception as e:
#             return f"Error removing columns: {e}"

#     def Add_column(self, table_name, columns):
#         try:
#             cursor = self.conn.cursor()
#             table_name = escape_name(table_name)  # Escape column name
#             for col in columns:
#                 col_name = escape_name(col.col_name)  # Escape column name
#                 column_definitions = ''
#                 column_definitions = f"ALTER TABLE {table_name} ADD COLUMN  {col_name} {col.get_db_column_type()}"
#                 cursor.execute(f"{column_definitions}")
#             self.conn.commit()
#             return True
#         except Exception as e:
#             return f"Error Adding columns: {e}"

#     def update_column_type(self, table_name, col_instance):
#         try:
#             table_name_ = table_name
#             cursor = self.conn.cursor()
#             # Get the column's name and the new data type
#             new_data_type = col_instance.get_db_column_type()
#             table_name = escape_name(db_type,table_name_)  # Escape column name
#             col_name = escape_name(db_type,col_instance.col_name)  # Escape column name
#             # Fetch current column information
#             cursor.execute(f"DESCRIBE {table_name} {col_name};")
#             current_data = cursor.fetchone()
#             current_data_type = current_data[1]  # Assuming the second element is the data type

        
#             query = f"ALTER TABLE {table_name} MODIFY COLUMN {col_name} {new_data_type};"
#             cursor.execute(query)
#             self.conn.commit()
#             return True

#         except Exception as e:
#             self.conn.rollback()
#             return f"Error updating column type: {e}"
        
#     def getcount(self, table_name):
#         try:
#             cursor = self.conn.cursor()
#             table_name = escape_name(table_name)  # Escape column name
#             cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
#             count = cursor.fetchone()[0]
#             return count
#         except Exception as e:
#             return f"Error getting count: {e}"
        
#     def getcount_aftersearching(self, tablename, filters):
#         try:
#             cursor = self.conn.cursor()
#             # Escape the table name
#             escaped_table = escape_name(tablename)
            
#             # Initialize query and conditions
#             query = f"SELECT COUNT(*) FROM {escaped_table} WHERE"
#             conditions = []
#             params = []

#             # Build conditions dynamically from filters
#             for f in filters:
#                 column = escape_name(f['col_name'])  # Escape column name
#                 search_value = f['search']
#                 # conditions.append(f"{column} LIKE %s")
#                 # params.append(f"%{search_value}%")
#                 if isinstance(search_value, list) and all(isinstance(item, int) for item in search_value):
#                     # Build multiple LIKE conditions for each value in the list
#                     like_conditions = " OR ".join([f"{column} = %s" for _ in search_value])
#                     conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                     params.extend([f"{value}" for value in search_value])  # Add each search value with wildcards
#                 if isinstance(search_value, list):
#                     like_conditions = []
#                     for value in search_value:
#                         if value == None:
#                             # If value is empty string, check for NULL
#                             like_conditions.append(f"{column} IS NULL")
#                         else:
#                             # Normal equality check
#                             like_conditions.append(f"{column} = %s")
#                             params.append(value)  # add only non-empty values as parameter

#                     # Combine all conditions with OR
#                     conditions.append(f"({' OR '.join(like_conditions)})")
#                 elif isinstance(search_value, list):
#                     # Build multiple LIKE conditions for each value in the list
#                     like_conditions = " OR ".join([f"{column} LIKE %s" for _ in search_value])
#                     conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                     params.extend([f"%{value}%" for value in search_value])  # Add each search value with wildcards
#                 # elif isinstance(search_value, int) and db_type== 'postgres':
#                 #     conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                 #     params.append(f"{search_value}%")
#                 # elif isinstance(search_value, str) and db_type== 'postgres' and  search_value is None:
#                 #     conditions.append(f" CAST({column} AS TEXT) IS NULL")  # Cast column to TEXT and use LIKE for partial matching
#                 # elif isinstance(search_value, str) and db_type== 'postgres':
#                 #     conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                 #     params.append(f"%{search_value}%")
#                 else:
#                     # Single LIKE condition
#                     conditions.append(f"{column} LIKE %s")  # Add condition for the column
#                     params.append(f"%{search_value}%")  # Add the search value with wildcards for LIKE# Add the search value with wildcards for LIKE
            
#             # Combine all conditions with AND
#             query += " AND ".join(conditions)

#             # Execute the query
#             cursor.execute(query, tuple(params))
#             count = cursor.fetchone()[0]
#             return count

#         except Exception as e:
#             self.conn.rollback()
#             return f"Error getting count: {e}"

#     def rename_column(self, table_name, old_col_name, col_instance):
#         try:

#             cursor = self.conn.cursor()
#             table_name = escape_name(table_name)  # Escape column name
#             old_col_name = escape_name(old_col_name)  # Escape column name
#             new_col_name = escape_name(col_instance.col_name)  # Escape column name

#             query = f"ALTER TABLE {table_name} CHANGE COLUMN {old_col_name} {new_col_name} {col_instance.get_db_column_type()};"
#             cursor.execute(query)
#             self.conn.commit()
#             return True

#         except Exception as e:
#             self.conn.rollback()
#             return f"Error renaming column: {e}"

#     def deletetable(self, table_name):
#         try:
#             table_name = escape_name(table_name)  # Escape column name
#             cursor = self.conn.cursor()
#             cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
#             self.conn.commit()
#             cursor.close()
#         except Exception as e:
#             return f"Error deleting table {table_name}: {e}"
#         return True

#     def clean_column_data(self, db_type, db_name, table_name, column_name):
#         try:
#             cursor = self.conn.cursor()
#             table_name = escape_name(db_type, table_name) 
#             column_name = escape_name(db_type, column_name)
#             # Clean the column if it exists
#             query = f"UPDATE {table_name} SET {column_name} = %s;"
#             cursor.execute(query, (None,))  # Set column to NULL
#             self.conn.commit()
#             # Ensure to close the cursor after use
#             cursor.close()
#             return True
#         except Exception as e:
#             # It's better to log the error instead of just # printing it
#             return f"Error cleaning column {column_name} in table {table_name}: {e}"

