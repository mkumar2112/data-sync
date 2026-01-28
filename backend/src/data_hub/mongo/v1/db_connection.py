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



class ddl:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name
        self.db_helper = db_helper

    def create_table_from_metadata(self, table_name, columns, constraints):
        """
        Create MySQL table using DatabaseColumn + DatabaseConstraint metadata.
        """
        cursor = self.conn.cursor()

        try:
            table_sql = [f"`{table_name}` ("]
            definitions = []

            # Columns
            for col in columns:
                definitions.append(self.db_helper.build_column_sql(col))

            # Constraints (ordered)
            for cons in sorted(constraints, key=lambda x: x.constraint_order or 0):
                if cons.is_enabled:
                    cons_sql = self.db_helper.build_constraint_sql(cons)
                    if cons_sql:
                        definitions.append(cons_sql)

            table_sql.append(",\n  ".join(definitions))
            table_sql.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")

            final_sql = "\n".join(table_sql)

            print(final_sql)
            # cursor.execute(final_sql)
            # self.conn.commit()

            return True, "Table created successfully"

        except Exception as e:
            self.conn.rollback()
            return False, f"Error creating table: {e}"

        finally:
            cursor.close()



class dql():
    def __init__(self, conn, db_name=None):
        self.conn = conn
        self.db_name = db_name

    def extract_data(self, table_name, **kwargs):
        try:
            query = f'SELECT * FROM {table_name}'
            data = self.run_query(query=query)
            print(data)
        except Exception as e:
            print(e)


class dml():
    def __init__(self):
        pass

    def load_data(self, table_name: str, df):
        pass

    