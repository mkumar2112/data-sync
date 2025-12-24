from pymongo import MongoClient
import os
from bson import ObjectId, Decimal128, Timestamp
from datetime import datetime



ENTRIES = int(os.getenv('DATA_ENTRIES',50))

def bson_to_json(data):
    if isinstance(data, dict):
        return {k: bson_to_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [bson_to_json(i) for i in data]
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, Decimal128):
        return float(data.to_decimal())
    elif isinstance(data, Timestamp):
        return str(data)            # or convert to ISO timestamp
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data
    
def escape_name(name):
    if not name:  # Handle empty or None names
        raise ValueError("The name to escape cannot be None or empty.")
    return name


class connectsql:
    def __init__(self):
        self.conn = None
        self.connection_details = {}
    def setup_connection(self, url=None, database=None):
        try:
            if not url:
                raise ValueError("URL is required for MongoDB.")
            self.conn = MongoClient(url)
            self.conn.server_info()  # Verifies the connection
            return True
        except Exception as e:
            return False
        
    def connectdb(self, db_name):
        try:
            if not self.conn:
                raise ValueError("Database connection is not established. Call setup_connection first.")
            self.conn[db_name]
            return True , f"Connected to MongoDB database: {db_name}"
        except Exception as e:
            return False, str(e)

    def get_mongo_version(self):
        try:
            server_info = self.conn.server_info()
            version = server_info.get("version", "Unknown")
            return True, version
        except Exception as e:
            return False, str(e)

    def get_server_status(self):
        try:
            db = self.conn.admin
            status = db.command("serverStatus")
            return True, status
        except Exception as e:
            return False, str(e)

    def get_global_variables(self):
        try:
            db = self.conn.admin
            params = db.command({"getParameter": "*"})
            return True, params
        except Exception as e:
            return False, str(e)

    def get_storage_engines(self):
        try:
            db = self.conn.admin
            engine = db.command("serverStatus").get("storageEngine", {})
            return True, engine
        except Exception as e:
            return False, str(e)

    def get_database_metadata(self, db_name):
        try:
            db = self.conn[db_name]
            stats = db.command("dbstats")
            return True, {
                "db": stats.get("db"),
                "collections": stats.get("collections"),
                "objects": stats.get("objects"),
                "avg_obj_size": stats.get("avgObjSize"),
                "data_size": stats.get("dataSize"),
                "storage_size": stats.get("storageSize"),
                "indexes": stats.get("indexes"),
                "index_size": stats.get("indexSize"),
                "fs_used_size": stats.get("fsUsedSize"),
                "fs_total_size": stats.get("fsTotalSize"),
            }
        except Exception as e:
            return False, str(e)

    def get_all_metadata(self, db_name):
        try:
            meta = {}

            # 1. Version
            status, version = self.get_mongo_version()
            meta["version"] = version if status else f"Error: {version}"

            # 2. Server Status
            status, server_status = self.get_server_status()
            meta["server_status"] = server_status if status else f"Error: {server_status}"

            # 3. Global Variables
            status, vars_data = self.get_global_variables()
            meta["global_variables"] = vars_data if status else f"Error: {vars_data}"

            # 4. Storage Engine
            status, engine_data = self.get_storage_engines()
            meta["storage_engines"] = engine_data if status else f"Error: {engine_data}"

            # 5. Database Metadata
            status, db_data = self.get_database_metadata(db_name)
            meta["database"] = db_data if status else f"Error: {db_data}"

            return True, bson_to_json(meta)

        except Exception as e: 
            return False, str(e)

    def db_exists(self, db_name):
        try:
            db_exit = db_name in self.conn.list_database_names()
            return db_exit
        except Exception as e:
            return False

    def show_tables(self):
        try:
            tables = self.conn.list_database_names()
            return tables
        except Exception as e:
            return False
        
    def create_db(self, db_name):
        try:
            database = self.conn[db_name]
            database['init_collection'].insert_one({'init': 'created'})
            return True, f"Database {db_name} created."
        except Exception as e:
            return False, f"Error creating database {db_name}: {e}"

    def deletedb(self, db_type, db_name):
        try:
            if not self.conn:
                raise ValueError("Database connection is not established. Call setup_connection first.")
            return False
        except Exception as e:
            return False

    def close_connection(self):
        try:
            if self.conn:
                self.conn.close()
                self.conn = None 
        except Exception as e:
            print(f"Error closing connection: {e}")

                
class tableoperation:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name

    def get_table_metadata(self, table_name):
        try:
            # ✅ Select DB & Collection correctly
            db = self.conn[self.db_name]
            collection = db[table_name]

            # ✅ 1. Row Count (Accurate)
            row_count = collection.count_documents({})

            # ✅ 2. Collection Stats (Size, Index, Engine)
            stats = db.command("collStats", table_name)

            data_size = stats.get("size", 0)               # actual data size
            index_size = stats.get("totalIndexSize", 0)    # index size
            engine = stats.get("storageEngine", {}).get("name")

            # ✅ 3. Table / Collection Type
            table_type = "collection"

            # ✅ 4. Mongo has no schema → keep None
            schema = None

            # ✅ 5. Extra options (sharding, capped, etc.)
            options = {
                "capped": stats.get("capped", False),
                "max_size": stats.get("maxSize"),
                "wiredTiger": stats.get("wiredTiger"),
                "nindexes": stats.get("nindexes"),
                "sharded": stats.get("sharded", False)
            }

            columns_constraints = self.get_columns_and_constraints(table_name=table_name)
            return {
                "schema": schema,
                "engine": engine,
                "row_count": row_count,
                "data_size": data_size,
                "index_size": index_size,
                "table_type": table_type,
                "options": options,
                **columns_constraints
            }

        except Exception as e:
            return {"error": str(e)}

    def get_columns_and_constraints(self, table_name):
        try:
            # ✅ Correct MongoDB access
            db = self.conn[self.db_name]             # Database
            collection = db[table_name]        # Collection
            sample_size = 200

            # ✅ 1. Safe schema inference
            field_map = {}

            samples = list(collection.find({}, limit=sample_size))

            for doc in samples:
                if not isinstance(doc, dict):
                    continue
                for key, value in doc.items():
                    if key not in field_map:
                        field_map[key] = type(value).__name__

            # ✅ Always include _id
            if "_id" not in field_map:
                field_map["_id"] = "ObjectId"

            columns = [
                {
                    "column_name": field,
                    "data_type": dtype,
                    "is_nullable": "NO" if field == "_id" else "YES",
                    "default": None
                }
                for field, dtype in field_map.items()
            ]

            # ✅ 2. Get constraints from indexes (SAFE)
            index_info = collection.index_information()
            constraints = []
            seen = set()

            for index_name, index_data in index_info.items():

                if not index_data or not isinstance(index_data, dict):
                    continue

                keys = index_data.get("key", [])
                is_unique = bool(index_data.get("unique", False))

                for item in keys:
                    if not isinstance(item, (list, tuple)) or len(item) < 1:
                        continue

                    column = item[0]

                    unique_key = (index_name, column)
                    if unique_key in seen:
                        continue
                    seen.add(unique_key)

                    if column == "_id":
                        constraint_type = "PRIMARY KEY"
                    elif is_unique:
                        constraint_type = "UNIQUE"
                    else:
                        constraint_type = "INDEX"

                    constraints.append({
                        "constraint_name": index_name,
                        "constraint_type": constraint_type,
                        "column_name": column,
                        "referenced_table": None,
                        "referenced_column": None
                    })

            return {
                "columns": columns,
                "constraints": constraints
            }

        except Exception as e:
            return {"error": str(e)}


#     def gettableData(self, db_type, db_name, table_name):
#         """
#         Fetches all data from the specified table in the given database.
#         """
#         try:
#             if db_type in available_db_in_sql:
#                 table_name = escape_name(db_type,table_name)
#                 # For postgres
#                 cursor = self.conn.cursor()
#                 query = f"SELECT * FROM {table_name};"
#                 cursor.execute(query)
#                 result = cursor.fetchall()
#                 cursor.close()
#                 return result
#             elif db_type == 'mongo':
#                 # For MongoDB
#                 db = self.conn[db_name]  # MongoDB database
#                 collection = db[table_name]  # MongoDB collection
                
#                 clean_result = [tuple(i.values()) for i in collection.find()]
#                 return clean_result
#             else:
#                 return f"Unsupported database type: {db_type}"
#         except Exception as e:
#             return f"An error occurred: {str(e)}"
    
#     def createtable(self, db_type, db_name, table_name, columns):
#         """
#         Creates a table (MongoDB collection or SQL table) in the specified database.
#         """
#         try:
#             table_names = escape_name(db_type, table_name)
#             if db_type in available_db_in_sql:
#                 cursor = self.conn.cursor()
#                 # List to hold column definitions and constraints
#                 column_definitions = []
#                 constraints = []
                    
#                 # Iterate over columns to build the table schema
#                 for col in columns:
#                     col_name = escape_name(db_type,col.col_name)  # Escape column name

#                     if col.col_name == '_id':
#                         column_definitions.append(f"{col_name} {col.get_db_column_type()} PRIMARY KEY")
#                     else:
#                         column_definitions.append(f"{col_name} {col.get_db_column_type()}")

#                 # Add constraints (if any)
#                 if constraints:
#                     column_definitions.extend(constraints)

#                 # Combine all definitions into a single string
#                 column_definitions_str = ", ".join(column_definitions)

#                 # Execute the query to create the table
#                 try:
#                     cursor.execute(f"CREATE TABLE {table_names} ({column_definitions_str});")
#                     self.conn.commit()
#                 except Exception as e:
#                     self.conn.rollback()
#                     # # print('Table is not created error:', e)
#                     return False, f'Table is not Created Error: {e}'
#                 finally:
#                     cursor.close()
#                 return True, 'Table is created'
            
#             elif db_type == 'mongo':
#                 # MongoDB collections are created dynamically upon insertion
#                 db = self.conn[db_name]
#                 collection = db[table_name]
#                 # Insert a dummy document to create the collection if not already created
#                 collection.insert_one({'_id':1,"init": "created"})
#                 collection.delete_many({})
#                 return True, 'Created Table'
            
#             else:
#                 raise ValueError("Unsupported database type for table creation.")
        
#         except Exception as e:
#             return f"Error creating table {table_name}: {e}"

#     def remove_table_columns(self, db_type, db_name, table_name, columns):
#         try:

#             return True
#         except Exception as e:
#             return f"Error removing columns: {e}"

#     def Add_column(self, db_type, db_name, table_name, columns):
#         try:
#             if db_type in available_db_in_sql:
#                 cursor = self.conn.cursor()
#                 table_name = escape_name(db_type,table_name)  # Escape column name
#                 for col in columns:
#                     col_name = escape_name(db_type,col.col_name)  # Escape column name
#                     column_definitions = ''
#                     column_definitions = f"ALTER TABLE {table_name} ADD COLUMN  {col_name} {col.get_db_column_type()}"
#                     cursor.execute(f"{column_definitions}")
#                 self.conn.commit()
#             elif db_type == 'mongo':
#                 print("MongoDB is schema-less, no need to add columns.")
#             else:
#                 raise ValueError("Unsupported database type")
#             return True
#         except Exception as e:
#             return f"Error Adding columns: {e}"

#     def update_column_type(self, db_type, db_name, table_name, col_instance):
#         try:
#             table_name_ = table_name
#             if db_type in ['mysql', 'postgres']:
#                 cursor = self.conn.cursor()
#                 # Get the column's name and the new data type
#                 new_data_type = col_instance.get_db_column_type()
#                 table_name = escape_name(db_type,table_name_)  # Escape column name
#                 col_name = escape_name(db_type,col_instance.col_name)  # Escape column name
#                 if db_type == 'mysql':
#                     # Fetch current column information
#                     cursor.execute(f"DESCRIBE {table_name} {col_name};")
#                     current_data = cursor.fetchone()
#                     current_data_type = current_data[1]  # Assuming the second element is the data type
#                 elif db_type == 'postgres':
#                     query = f"""
#                     SELECT data_type 
#                     FROM information_schema.columns 
#                     WHERE table_name = '{table_name_}'AND column_name = '{col_instance.col_name}';
#                     """
#                     cursor.execute(query)
#                     current_data = cursor.fetchone()
#                     if not current_data:
#                         raise ValueError(f"Column {col_name} does not exist in table {table_name}.")
#                 # Perform data type conversion if necessary
#                 if db_type in ['mysql', 'postgres']:
#                     if db_type == 'postgres':
#                         query = f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {new_data_type} USING {col_name}::{new_data_type};"
#                     elif db_type == 'mysql':
#                         query = f"ALTER TABLE {table_name} MODIFY COLUMN {col_name} {new_data_type};"
#                     cursor.execute(query)
#                     self.conn.commit()
#             elif db_type == 'mongo':
#                 # print("MongoDB schema is flexible; no need to change column types.")
#                 return True
#             else:
#                 raise ValueError("Unsupported database type")
#             return True

#         except Exception as e:
#             self.conn.rollback()
#             return f"Error updating column type: {e}"
        
#     def getcount(self, db_type, db_name, table_name):
#         try:
#             if db_type in available_db_in_sql:
#                 cursor = self.conn.cursor()
#                 table_name = escape_name(db_type,table_name)  # Escape column name
#                 cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
#                 count = cursor.fetchone()[0]
#                 return count
#             elif db_type == 'mongo':
#                 collection = self.conn[db_name][table_name]
#                 count = collection.count_documents({})
#                 return count
#             else:
#                 raise ValueError(f"Unsupported database type: {db_type}")
#         except Exception as e:
#             return f"Error getting count: {e}"
        
#     def getcount_aftersearching(self, db_type, db_name, tablename, filters):
#         try:
#             if db_type in available_db_in_sql:
#                 cursor = self.conn.cursor()
#                 # Escape the table name
#                 escaped_table = escape_name(db_type, tablename)
                
#                 # Initialize query and conditions
#                 query = f"SELECT COUNT(*) FROM {escaped_table} WHERE"
#                 conditions = []
#                 params = []

#                 # Build conditions dynamically from filters
#                 for f in filters:
#                     column = escape_name(db_type, f['col_name'])  # Escape column name
#                     search_value = f['search']
#                     # conditions.append(f"{column} LIKE %s")
#                     # params.append(f"%{search_value}%")
#                     if isinstance(search_value, list) and all(isinstance(item, int) for item in search_value):
#                         # Build multiple LIKE conditions for each value in the list
#                         like_conditions = " OR ".join([f"{column} = %s" for _ in search_value])
#                         conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                         params.extend([f"{value}" for value in search_value])  # Add each search value with wildcards
#                     if isinstance(search_value, list):
#                         like_conditions = []
#                         for value in search_value:
#                             if value == None:
#                                 # If value is empty string, check for NULL
#                                 like_conditions.append(f"{column} IS NULL")
#                             else:
#                                 # Normal equality check
#                                 like_conditions.append(f"{column} = %s")
#                                 params.append(value)  # add only non-empty values as parameter

#                         # Combine all conditions with OR
#                         conditions.append(f"({' OR '.join(like_conditions)})")
#                     elif isinstance(search_value, list):
#                         # Build multiple LIKE conditions for each value in the list
#                         like_conditions = " OR ".join([f"{column} LIKE %s" for _ in search_value])
#                         conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                         params.extend([f"%{value}%" for value in search_value])  # Add each search value with wildcards
#                     elif isinstance(search_value, int) and db_type== 'postgres':
#                         conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                         params.append(f"{search_value}%")
#                     elif isinstance(search_value, str) and db_type== 'postgres' and  search_value is None:
#                         conditions.append(f" CAST({column} AS TEXT) IS NULL")  # Cast column to TEXT and use LIKE for partial matching
#                     elif isinstance(search_value, str) and db_type== 'postgres':
#                         conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                         params.append(f"%{search_value}%")
#                     else:
#                         # Single LIKE condition
#                         conditions.append(f"{column} LIKE %s")  # Add condition for the column
#                         params.append(f"%{search_value}%")  # Add the search value with wildcards for LIKE# Add the search value with wildcards for LIKE
                
#                 # Combine all conditions with AND
#                 query += " AND ".join(conditions)

#                 # Execute the query
#                 cursor.execute(query, tuple(params))
#                 count = cursor.fetchone()[0]
#                 return count

#             elif db_type == "mongo":
#                 # MongoDB case
#                 collection = self.conn[db_name][tablename]
                
#                 # Build query with $and for multiple filters
#                 mongo_query = {"$and": []}
                
#                 for f in filters:
#                     column = f['col_name']
#                     search_value = f['search']
                    
#                     if isinstance(search_value, list):
#                         # If search_value is a list, handle accordingly
#                         if all(isinstance(item, int) for item in search_value):
#                             # Handle list of integers with $in
#                             mongo_query["$and"].append({column: {"$in": search_value}})
#                         else:
#                             # Handle list of strings with $regex using $or
#                             mongo_query["$and"].append({
#                                 column: {"$regex": "|".join(map(str, search_value)), "$options": "i"}  # Case-insensitive OR match
#                             })
#                     else:
#                         # Single value (either string or other types)
#                         if isinstance(search_value, str):
#                             # If the value is a string, apply $regex
#                             mongo_query["$and"].append({column: {"$regex": search_value, "$options": "i"}})
#                         else:
#                             # If it's a number or other type, do direct matching
#                             mongo_query["$and"].append({column: search_value})
                
#                 # Get the document count
#                 count = collection.count_documents(mongo_query)
#                 return count
#             else:
#                 raise ValueError(f"Unsupported database type: {db_type}")

#         except Exception as e:
#             # Handle errors
#             if db_type in available_db_in_sql:
#                 cursor = self.conn.cursor()
#                 self.conn.rollback()
#             return f"Error getting count: {e}"

#     def rename_column(self, db_type, db_name, table_name, old_col_name, col_instance):
#         try:

#             if db_type in ['mysql', 'postgres']:
#                 cursor = self.conn.cursor()
#                 table_name = escape_name(db_type,table_name)  # Escape column name
#                 old_col_name = escape_name(db_type,old_col_name)  # Escape column name
#                 new_col_name = escape_name(db_type,col_instance.col_name)  # Escape column name
#                 # Renaming column for postgres
#                 if db_type == 'postgres':
#                     query = f"ALTER TABLE {table_name} RENAME COLUMN {old_col_name} TO {new_col_name};"
#                     cursor.execute(query)
#                     self.conn.commit()
                
#                 # Renaming column for MySQL
#                 elif db_type == 'mysql':
#                     query = f"ALTER TABLE {table_name} CHANGE COLUMN {old_col_name} {new_col_name} {col_instance.get_db_column_type()};"
#                     cursor.execute(query)
#                     self.conn.commit()

#             elif db_type == 'mongo':
#                 db = self.conn[db_name]
#                 collection = db[table_name]
#                 collection.update_many({}, {"$rename": {old_col_name: col_instance.col_name}})
#             else:
#                 raise ValueError(f"Unsupported database type: {db_type}")
#             return True

#         except Exception as e:
#             self.conn.rollback()
#             return f"Error renaming column: {e}"

#     def deletetable(self, db_type, db_name, table_name):
#         """
#         Deletes the specified table, including dependent foreign keys for MySQL.
#         """
#         try:
#             pass

#         except Exception as e:
#             return f"Error deleting table {table_name}: {e}"
#         return True

#     def clean_column_data(self, db_type, db_name, table_name, column_name):
#         try:
#             if db_type in ['mysql', 'postgres']:
#                 cursor = self.conn.cursor()
#                 table_name = escape_name(db_type, table_name) 
#                 column_name = escape_name(db_type, column_name)
#                 # Clean the column if it exists
#                 query = f"UPDATE {table_name} SET {column_name} = %s;"
#                 cursor.execute(query, (None,))  # Set column to NULL
#                 self.conn.commit()
#                 # Ensure to close the cursor after use
#                 cursor.close()
#             elif db_type == 'mongo':
#                 client = MongoClient(self.conn)  # Assuming self.conn is MongoDB URI
#                 db = client[db_name]
#                 collection = db[table_name]
#                 # Check if the field exists in at least one document
#                 if collection.find_one({column_name: {"$exists": True}}) is None:
#                     return f"Field {column_name} does not exist in collection {table_name}."
#                 # Clean the column (set it to None in all documents)
#                 result = collection.update_many({}, {"$set": {column_name: None}})
#                 return f"Cleaned {result.modified_count} documents in {table_name}."
#             else:
#                 raise ValueError("Unsupported database type for cleaning column data.")
#             return True
#         except Exception as e:
#             # It's better to log the error instead of just # printing it
#             return f"Error cleaning column {column_name} in table {table_name}: {e}"


# # MongoDB operations
# class data_operations_mongo:
#     def __init__(self, db):
#         self.db = db

#     def insert_data(self, table, data):
#         try:
#             self.db.command('ping')
#             last_document = self.db[table].find_one(sort=[('_id', -1)])
#             new_id = 1 if last_document is None else (last_document['_id'] + 1)
#             data['_id'] = new_id
#             self.db[table].insert_one(data)
#             return f"Data inserted successfully"
#         except Exception as e:
#             return f"Error occurred while inserting data: {str(e)}"

#     def update_data(self, table, data, id):
#         if not id:
#             return "Id is required for updating data"
#         try:
#             result = self.db[table].find_one({'_id': int(id)})
#             if result is None:
#                 return f"No document found with _id = {id}"
#             # Update the document with the new data
#             self.db[table].update_one({'_id': int(id)}, {"$set": data})
#             return f"Document with _id = {id} updated successfully"

#         except Exception as e:
#             return f"Error occurred while updating data: {str(e)}"

#     def delete_data(self, table, id):
#         if id:
#             try:
#                 result = self.db[table].delete_one({'_id': int(id)})
#                 if result.deleted_count > 0:
#                     return "Data deleted successfully"
#                 else:
#                     return "No document found with the provided _id"
#             except Exception as e:
#                 return f"An error occurred: {e}"
#         else:
#             return "Id is required for deleting data"

#     def get_data(self, table, min=None, max=None, id=None, filters=None, foreign=False):
#         # If min is provided as 0, treat it as 1
#         if min == 0:
#             min = 1
#         clean_result = []
#         try:
#             tablename = table.table_name if hasattr(table, 'table_name') else table

#             # MongoDB - search by ID if provided
#             if id:
#                 clean_result = [tuple(i.values()) for i in self.db[tablename].find({'_id': int(id)}).limit(1)]
#             # MongoDB - search using filters
#             elif filters is not None:
#                 mongo_query = {"$and": []}  # Initialize $and condition

#                 # Loop through the filters and build dynamic conditions
#                 for f in filters:
#                     column = f['col_name']
#                     search_value = f['search']
#                     # Ensure search_value is a string before applying $regex
#                     search_value = str(search_value)  # Convert to string
#                     if column == '_id':
#                         mongo_query["$and"].append({
#                             '_id': str(search_value)  # Direct comparison for _id
#                         })
#                     elif isinstance(search_value, list) and all(isinstance(item, int) for item in search_value):
#                         # If the search value is a list of integers, use $in operator
#                         mongo_query["$and"].append({
#                             column: {"$in": search_value}  # Match any value in the list
#                         })
#                     elif isinstance(search_value, list):
#                         # If it's a list of strings, use $regex with $or for each value
#                         mongo_query["$and"].append({
#                             column: {"$regex": "|".join(map(str, search_value)), "$options": "i"}  # Case-insensitive match for any of the values
#                         })
#                     else:
#                         # For single string searches, use $regex
#                         if isinstance(search_value, str):  # Only apply $regex for string values
#                             mongo_query["$and"].append({
#                                 column: {"$regex": search_value, "$options": "i"}  # Case-insensitive match
#                             })
#                         else:
#                             mongo_query["$and"].append({
#                                 column: search_value  # Direct match for non-string search_value
#                             })
#                 # Execute the query with $and conditions
#                 clean_result = [tuple(i.values()) for i in self.db[tablename].find(mongo_query).skip(min-1).limit(max-min+1)]
#             # MongoDB - Fetch data by range (pagination) if min and max are provided
#             elif min is not None and max is not None:
#                 clean_result = [tuple(i.values()) for i in self.db[tablename].find({}).skip(min-1).limit(max-min+1)]
#             # MongoDB - Fetch all data with default limit
#             else:
#                 clean_result = [tuple(i.values()) for i in self.db[tablename].find({}).limit(ENTRIES)]
#         except Exception as e:
#             print(f"Error fetching data: {e}")
#         return clean_result
    

# # SQL operations
# class data_operations_sql:
    
#     def __init__(self, db, db_type):
#         self.db = db
#         self.db_type = db_type

#     def insert_data(self, table, data):
#         self.db.commit()
#         cursor = self.db.cursor()
#         try:
#             table = escape_name(self.db_type, table)
#             # Fetch the last _id value from the table
#             if self.db_type == 'mysql':
#                 cursor.execute(f"SELECT MAX(_id) FROM {table}")
#             elif self.db_type == 'postgres':
#                 cursor.execute(f"SELECT COALESCE(MAX(_id), 0) FROM {table}")
#             last_id = cursor.fetchone()[0]
#             # If last_id is None (i.e., table is empty), start the _id from 1
#             new_id = 1 if last_id is None else (last_id + 1)
#             # Get the column names dynamically from the database (excluding _id)
#             if self.db_type == 'mysql':
#                 cursor.execute(f"SHOW COLUMNS FROM {table}")
#                 columns = [col[0] for col in cursor.fetchall() if col[0] != '_id']  # Exclude '_id' from columns
#             elif self.db_type == 'postgres':
#                 cursor.execute(
#                     """
#                     SELECT column_name
#                     FROM information_schema.columns
#                     WHERE table_schema = 'public' AND table_name = %s AND column_name != '_id'
#                     """,
#                     (table.strip('"'),)  # Remove quotes around the table name
#                 )

#                 columns = [col[0] for col in cursor.fetchall()]
                
#             # Filter data to exclude keys with None or empty string values and replace empty string with None
#             filtered_data = {
#                 key: (None if value == '' else value) for key, value in data.items() if key != '_id'
#             }
#             # Ensure the filtered data keys match the column names
#             if set(filtered_data.keys()) != set(columns):
#                 raise ValueError(f"Data keys {filtered_data.keys()} do not match table columns {columns}")
#             # Adjust the data tuple to include the new _id at the beginning
#             clean_data = (new_id,) + tuple(filtered_data.get(key) for key in columns)
#             columns = [escape_name(self.db_type, col) for col in columns]
#             # Prepare the insert query with dynamic columns
#             column_names = ', '.join(columns)  # Get comma-separated column names
#             placeholders = ', '.join(['%s'] * len(columns))  # Create placeholders for each column
#             # Construct the INSERT query
#             if self.db_type == 'mysql' or self.db_type == 'postgres':
#                 query = f"INSERT INTO {table} (_id, {column_names}) VALUES (%s, {placeholders}) RETURNING _id"
#             # Execute the query
#             cursor.execute(query, clean_data)
#             inserted_id = cursor.fetchone()[0] if self.db_type == 'postgres' else cursor.lastrowid
#             # print(inserted_id)
#             self.db.commit()
#             return ("Data inserted successfully", inserted_id)
#         except Exception as e:
#             self.db.rollback()
#             return (f"Error occurred while inserting data: {str(e)}", -1)

#     def update_data(self, table, data, id):
#         self.db.commit()
#         table = escape_name(self.db_type, table)
#         cursor = self.db.cursor()
#         filtered_data = {escape_name(self.db_type, key): (None if value == '' else value) for key, value in data.items() if key != '_id'}
#         if not filtered_data:
#             return "No valid fields to update."
#         # Dynamically create the SET part of the query
#         set_clause = ', '.join([f"{col} = %s" for col in filtered_data.keys()])
#         query = f"UPDATE {table} SET {set_clause} WHERE _id = %s"
#         values = tuple(filtered_data.values()) + (id,)
#         try:
#             # Execute the query
#             cursor.execute(query, values)
#             self.db.commit()
#             # Check if the update was successful
#             if cursor.rowcount == 0:
#                 return f"No record found with _id = {id} to update."
#             return f"Record with _id = {id} updated successfully."
#         except Exception as e:
#             self.db.rollback()
#             return f"Error occurred while updating data: {str(e)}"

#     def delete_data(self, table, id):
#         if id:
#             try:
#                 table = escape_name(self.db_type, table)
#                 cursor = self.db.cursor()
#                 query = f"DELETE FROM {table} WHERE _id = %s"
#                 cursor.execute(query, (id,))
#                 self.db.commit()

#             except Exception as e:
#                 return e
#         else:
#             return "Id is required for deleting data"

#     def get_data(self, table, min=None, max=None, id=None, filters=None, foreign=False,  sort_Column=None, sort_by=None):
#         cursor = self.db.cursor()
#         try:
#             # Escape the table name to prevent SQL injection
#             table = escape_name(self.db_type, table)
#             if id:
#                 query = f"SELECT * FROM {table} WHERE _id = %s"
#                 cursor.execute(query, (str(id),))
#             elif filters is not None:
#                 # Initialize the base query and conditions
#                 query = f"SELECT * FROM {table} WHERE"
#                 conditions = []
#                 params = []
#                 # Loop through the filter list to add conditions
#                 for f in filters:
#                     column = escape_name(self.db_type, f['col_name'])  # Escape column name to prevent SQL injection
#                     search_value = f['search']
#                     if isinstance(search_value, list) and all(isinstance(item, int) for item in search_value):
#                         # Build multiple LIKE conditions for each value in the list
#                         like_conditions = " OR ".join([f"{column} = %s" for _ in search_value])
#                         conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                         params.extend([f"{value}" for value in search_value])  # Add each search value with wildcards
#                     if isinstance(search_value, list):
#                         like_conditions = []
#                         for value in search_value:
#                             if value == None:
#                                 # If value is empty string, check for NULL
#                                 like_conditions.append(f"{column} IS NULL")
#                             else:
#                                 # Normal equality check
#                                 like_conditions.append(f"{column} = %s")
#                                 params.append(value)  # add only non-empty values as parameter

#                         # Combine all conditions with OR
#                         conditions.append(f"({' OR '.join(like_conditions)})")
#                     elif isinstance(search_value, list):
#                         # Build multiple LIKE conditions for each value in the list
#                         like_conditions = " OR ".join([f"{column} LIKE %s" for _ in search_value])
#                         conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                         params.extend([f"%{value}%" for value in search_value])  # Add each search value with wildcards
#                     elif isinstance(search_value, int) and self.db_type== 'postgres':
#                         conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                         params.append(f"{search_value}%") 
#                     elif isinstance(search_value, str) and self.db_type== 'postgres' and search_value is None:
#                         conditions.append(f" CAST({column} AS TEXT) IS NULL")  # Cast column to TEXT and use LIKE for partial matching
#                     elif isinstance(search_value, str) and self.db_type== 'postgres':
#                         conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                         params.append(f"%{search_value}%") 
#                     else:
#                         # Single LIKE condition
#                         conditions.append(f"{column} LIKE %s")  # Add condition for the column
#                         params.append(f"%{search_value}%")  # Add the search value with wildcards for LIKE# Add the search value with wildcards for LIKE

#                 # Join all conditions with 'AND'
#                 query += " AND ".join(conditions)
#                 if not foreign:
#                     # Add LIMIT and OFFSET for pagination
#                     query += f" ORDER BY {sort_Column} {sort_by}" if sort_Column and sort_by else ''
#                     query += " LIMIT %s OFFSET %s"
#                     if min != None and max:
#                         params.extend([max, min])
#                     else:
#                         params.extend([ENTRIES, min])  # `min - 1` for zero-based OFFSET
#                 try:
#                     cursor.execute(query, tuple(params))
#                 except Exception as e:
#                     # print(f"Error executing query: {e}")
#                     return None
#             elif min is not None and max is not None:
#                 if min <= 1:
#                     # Apply only LIMIT
#                     query = f"SELECT * FROM {table}"
#                     query += f" ORDER BY {sort_Column} {sort_by}" if sort_Column and sort_by else ''
#                     query += f" LIMIT %s"
#                     cursor.execute(query, (min+(ENTRIES if not max else max),))
#                 else:
#                     # Apply both LIMIT and OFFSET
#                     query = f"SELECT * FROM {table}"
#                     query += f" ORDER BY {sort_Column} {sort_by}" if sort_Column and sort_by else ''
#                     query += f" LIMIT %s OFFSET %s"
#                     cursor.execute(query, (max - min, min))
#             else:
#                 # Fetch all data
#                 query = f"SELECT * FROM {table}"
#                 query += f" ORDER BY {sort_Column} {sort_by}" if sort_Column and sort_by else ''
#                 query += f" LIMIT %s"
#                 cursor.execute(query, (ENTRIES,))
#             # Fetch and return all results
#             data = cursor.fetchall()
#             return data
        
#         except Exception as e:
#             # Handle and log exceptions (optional logging can be added here)
#             return None
#         finally:
#             cursor.close()

#     def check_ids_in_table(self, table, id_column, ids_to_check=None, filters =None):
#         """
#         Check if given IDs exist in the database table.

#         Args:
#             table (str): Table name.
#             id_column (str): Column name of ID in the table.
#             ids_to_check (list): List of IDs to validate.
#         Returns:
#             tuple: (present_ids, not_present_ids)
#         """
#         cursor = self.db.cursor()
#         try:
#             # Escape table and column names for safety
#             table = escape_name(self.db_type, table)
#             id_column = escape_name(self.db_type, id_column)

#             # Query only the IDs in the given list
#             query = f'SELECT {id_column} FROM {table}'
#             if filters and id_column:
#                 # Initialize the base query and conditions
#                 query = f"SELECT {id_column} FROM {table} WHERE"
#                 conditions = []
#                 params = []
#                 # Loop through the filter list to add conditions
#                 for f in filters:
#                     column = escape_name(self.db_type, f['col_name'])  # Escape column name to prevent SQL injection
#                     search_value = f['search']
#                     if isinstance(search_value, list) and all(isinstance(item, int) for item in search_value):
#                         # Build multiple LIKE conditions for each value in the list
#                         like_conditions = " OR ".join([f"{column} = %s" for _ in search_value])
#                         conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                         params.extend([f"{value}" for value in search_value])  # Add each search value with wildcards
#                     elif isinstance(search_value, list):
#                         # Build multiple LIKE conditions for each value in the list
#                         like_conditions = " OR ".join([f"{column} LIKE %s" for _ in search_value])
#                         conditions.append(f"({like_conditions})")  # Wrap the LIKE conditions for the list
#                         params.extend([f"%{value}%" for value in search_value])  # Add each search value with wildcards
#                     elif isinstance(search_value, int) and self.db_type== 'postgres':
#                         conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                         params.append(f"{search_value}%") 
#                     elif isinstance(search_value, str) and self.db_type== 'postgres':
#                         conditions.append(f" CAST({column} AS TEXT) LIKE %s")  # Cast column to TEXT and use LIKE for partial matching
#                         params.append(f"%{search_value}%") 
#                     else:
#                         # Single LIKE condition
#                         conditions.append(f"{column} LIKE %s")  # Add condition for the column
#                         params.append(f"%{search_value}%")  # Add the search value with wildcards for LIKE# Add the search value with wildcards for LIKE

#                 # Join all conditions with 'AND'
#                 query += " AND ".join(conditions)
#                 try:
#                     cursor.execute(query, tuple(params))
#                 except Exception as e:
#                     return None
#             elif ids_to_check:
#                 query = f"SELECT {id_column} FROM {table} WHERE {id_column} IN %s"
#                 cursor.execute(query, (tuple(ids_to_check),))
#             else:
#                 cursor.execute(query)
#             rows = cursor.fetchall()
#             # Extract IDs that exist in DB
#             present_ids = {row[0] for row in rows}

#             return list(present_ids)

#         except Exception as e:
#             # Log error if needed
#             return []  # assume all missing if error
#         finally:
#             cursor.close()



# # Wrapper for selecting the database operations based on db_type
# class data_operations:

#     def __init__(self, db_type, db, db_name=None):
#         self.db = db
#         self.db_type = db_type
#         self.db_name = db_name
#         if db_type == 'mysql' or db_type == 'postgres':
#             self.data_operation = data_operations_sql(self.db, self.db_type)
#         elif db_type in available_db_in_nosql:
#             self.data_operation = data_operations_mongo(self.db[ self.db_name])
#         else:
#             raise ValueError("Unsupported database type")

#     def insert_data(self, table, data):
#         if data:
#             return self.data_operation.insert_data(table, data)
#         else:
#             return "Data is required to insert"

#     def update_data(self, table, data=None, id=None):
#         if id:
#             return self.data_operation.update_data(table, data, id)
#         else:
#             return "Id is required for updating data"

#     def delete_data(self, table, id):
#         if id:
#             return self.data_operation.delete_data(table, id)
#         else:
#             return "Id is required for deleting data"

#     def get_data(self, table, min=None, max=None, id=None, filters=None, foreign=False, sort_Column=None, sort_by=None):
#         try:
#             # Ensure `min` is valid only if it's not None and less than 0
#             min = min if min is not None and min >= 0 else None
#             # If both `min` and `max` are None, set them to default values
#             if min is None and max is None:
#                 min, max = 0, ENTRIES  # ENTRIES needs to be defined somewhere
#             # Case 1: Fetch by ID
#             if id:
#                 return self.data_operation.get_data(table=table, id=id)
            
#             # Case 2: Filters are provided with range (min and max)
#             elif filters is not None:
#                 return self.data_operation.get_data(table=table, min=min, max=max, filters=filters, foreign=foreign, sort_Column=sort_Column, sort_by=sort_by)
#             # Case 3: Range (min and max) without filters
#             elif min is not None and max is not None:
#                 return self.data_operation.get_data(table=table, min=min, max=max, sort_Column=sort_Column, sort_by=sort_by)
#             # Case 4: Default fetch (no filters, ID, or range)
#             else:
#                 return self.data_operation.get_data(table=table, sort_Column=sort_Column, sort_by=sort_by)
        
#         except Exception as e:
#             # Enhanced error handling and logging
#             return None


#     def check_ids_in_table(self, table, id_column='_id', ids_to_check=None, filters=None):
#         try:
#             return self.data_operation.check_ids_in_table(table=table, id_column=id_column, ids_to_check=ids_to_check, filters=filters)
#         except Exception as e:
#             return None





