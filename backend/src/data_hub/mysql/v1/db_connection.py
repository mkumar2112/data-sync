import mysql.connector
import os
from ....db.models.connection import DatabaseColumn, DatabaseConstraint
import re
from .utility import *

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
        """
        Drop database safely.
        """
        if not self.conn:
            return False, "Database connection is not established"

        cursor = self.conn.cursor()
        try:
            db_name = db_name.lower()
            cursor.execute("USE `mysql`;")
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`;")
            return True, f"Database `{db_name}` deleted successfully"
        except Exception as e:
            return False, str(e)
        finally:
            cursor.close()


    def close_connection(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            print(f"Error closing connection: {e}")

    def commit(self):
        """
        Commit the current transaction.
        """
        try:
            self.conn.commit()
            return True, "Transaction committed successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Commit failed: {e}"


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
            cursor = self.conn.cursor()

            # 1️⃣ Get Columns
            column_query = """
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    COLUMN_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    EXTRA,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION;
            """

            cursor.execute(column_query, (table_name,))
            columns = cursor.fetchall()

            # 2️⃣ Get constraint-column mapping
            constraint_col_query = """
            SELECT 
                tc.CONSTRAINT_TYPE,
                kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                AND tc.TABLE_NAME = kcu.TABLE_NAME
            WHERE tc.TABLE_SCHEMA = DATABASE()
            AND tc.TABLE_NAME = %s;
            """
            cursor.execute(constraint_col_query, (table_name,))
            constraint_cols = cursor.fetchall()

            # 3️⃣ Build sets for PK & UNIQUE
            primary_keys = set()
            unique_keys = set()

            for ctype, col in constraint_cols:
                if ctype == "PRIMARY KEY":
                    primary_keys.add(col)
                elif ctype == "UNIQUE":
                    unique_keys.add(col)

            # 4️⃣ Format columns with boolean flags
            formatted_columns = []
            for row in columns:
                (
                    col_name,
                    data_type,
                    column_type,
                    is_nullable,
                    default,
                    extra,
                    char_length,
                    numeric_precision,
                    numeric_scale
                ) = row
                enum_values = None
                if data_type.lower() == "enum" and column_type:
                    enum_values = (
                        column_type
                        .replace("enum(", "")
                        .replace(")", "")
                        .replace("'", "")
                        .split(",")
                    )
                is_auto_increment = "auto_increment" in (extra or "").lower()
                is_unsigned = "unsigned" in (column_type or "").lower()


                formatted_columns.append({
                    "column_name": col_name,
                    "data_type": data_type,
                    "is_nullable": is_nullable,
                    "default": default,

                    # 👇 NEW FIELDS
                    "length": char_length,               # VARCHAR / CHAR
                    "precision": numeric_precision,      # INT / DECIMAL / FLOAT
                    "scale": numeric_scale,               # DECIMAL

                    "is_auto_increment": is_auto_increment,
                    "is_unsigned": is_unsigned,


                    "is_primary_key": col_name in primary_keys,
                    "is_unique": col_name in unique_keys,
                    "enum_values": enum_values, 
                })

            # 5️⃣ Get full constraints (same as your logic)
            constraint_query = """
            SELECT 
                tc.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE,
                kcu.COLUMN_NAME,
                kcu.REFERENCED_TABLE_NAME,
                kcu.REFERENCED_COLUMN_NAME,
                rc.UPDATE_RULE,
                rc.DELETE_RULE
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
            AND tc.TABLE_NAME = kcu.TABLE_NAME  
            LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
            ON tc.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
            AND tc.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE tc.TABLE_SCHEMA = DATABASE()
            AND tc.TABLE_NAME = %s
            ORDER BY tc.CONSTRAINT_NAME, kcu.ORDINAL_POSITION;
            """
            cursor.execute(constraint_query, (table_name,))
            rows = cursor.fetchall()

            constraint_map = {}
            for (
                name, ctype, col,
                ref_table, ref_col,
                on_update, on_delete
            ) in rows:
                if name not in constraint_map:
                    constraint_map[name] = {
                        "constraint_name": name,
                        "constraint_type": ctype,
                        "columns": [],
                        "ref_table": ref_table,
                        "ref_columns": [],
                        "on_update": on_update,
                        "on_delete": on_delete,
                    }
                if col:
                    constraint_map[name]["columns"].append(col)
                if ref_col:
                    constraint_map[name]["ref_columns"].append(ref_col)

            formatted_constraints = []
            for c in constraint_map.values():
                cols = ", ".join(c["columns"])
                if c["constraint_type"] == "PRIMARY KEY":
                    definition = f"PRIMARY KEY ({cols})"
                elif c["constraint_type"] == "UNIQUE":
                    definition = f"UNIQUE ({cols})"
                elif c["constraint_type"] == "FOREIGN KEY":
                    ref_cols = ", ".join(c["ref_columns"])
                    # definition = f"FOREIGN KEY ({cols}) REFERENCES {c['ref_table']}({ref_cols})"
                    definition = (
                        f"FOREIGN KEY ({cols}) "
                        f"REFERENCES {c['ref_table']} ({ref_cols}) "
                        f"ON DELETE {c['on_delete']} "
                        f"ON UPDATE {c['on_update']}"
                    )
                else:
                    continue

                formatted_constraints.append({
                    "constraint_name": c["constraint_name"],
                    "constraint_type": c["constraint_type"],
                    "definition": definition,
                })

            cursor.close()

            return {
                "columns": formatted_columns,
                "constraints": formatted_constraints,
            }

        except Exception as e:
            return {"error": str(e)}


class db_helper:
    def __init__(self, db_name):
        self.db_name = db_name

    def extract_columns_from_definition(self, definition: str):
        """
        Extract column names from SQL like:
        UNIQUE (col1, col2)
        PRIMARY KEY (id)
        """
        match = re.search(r"\((.*?)\)", definition)
        if not match:
            return []

        cols = match.group(1)
        return [c.strip(" `") for c in cols.split(",")]
        
    def extract_fk_from_definition(self, definition: str):
        """
        Extract referenced table and columns from FK definition
        """
        pattern = re.compile(
            r"REFERENCES\s+`?(\w+)`?\s*\(([^)]+)\)",
            re.IGNORECASE
        )
        match = pattern.search(definition)
        if not match:
            return None, []

        table = match.group(1)
        cols = [c.strip(" `") for c in match.group(2).split(",")]
        return table, cols


    def build_column_sql(self, col):
        """
        Build full MySQL-safe column SQL from ReplicaDatabaseColumn
        """

        parts = [f"`{col.column_name}`"]
        dt = (col.data_type or "").upper()

        # -----------------------------
        # TYPE GROUPS
        # -----------------------------
        TEXT_TYPES = {
            "TINYTEXT", "TEXT", "MEDIUMTEXT", "LONGTEXT",
            "TINYBLOB", "BLOB", "MEDIUMBLOB", "LONGBLOB"
        }

        STRING_TYPES = {"CHAR", "VARCHAR", "BINARY", "VARBINARY"}

        NUMERIC_TYPES = {
            "TINYINT", "SMALLINT", "MEDIUMINT",
            "INT", "INTEGER", "BIGINT",
            "FLOAT", "DOUBLE", "REAL"
        }

        DATE_TYPES = {"DATE", "TIME", "DATETIME", "TIMESTAMP", "YEAR"}

        # -----------------------------
        # DATA TYPE HANDLING
        # -----------------------------
        if dt == "ENUM":
            if not col.enum_values:
                raise ValueError(f"ENUM requires enum_values for {col.column_name}")
            values = ", ".join(f"'{v}'" for v in col.enum_values)
            parts.append(f"ENUM({values})")

        elif dt in STRING_TYPES:
            length = col.length or 255
            parts.append(f"{dt}({length})")

        elif dt in ("DECIMAL", "NUMERIC"):
            precision = col.precision or 10
            scale = col.scale or 0
            parts.append(f"{dt}({precision},{scale})")

        elif dt in TEXT_TYPES:
            parts.append(dt)

        elif dt in NUMERIC_TYPES:
            parts.append(dt)

        elif dt == "BOOLEAN":
            parts.append("TINYINT(1)")

        elif dt == "JSON":
            parts.append("JSON")

        elif dt in DATE_TYPES:
            parts.append(dt)

        else:
            raise ValueError(f"Unsupported MySQL datatype: {dt}")

        # -----------------------------
        # UNSIGNED
        # -----------------------------
        if col.is_unsigned and dt in NUMERIC_TYPES:
            parts.append("UNSIGNED")

        # -----------------------------
        # NULL / NOT NULL
        # -----------------------------
        parts.append("NULL" if col.is_nullable else "NOT NULL")

        # -----------------------------
        # DEFAULT VALUE
        # -----------------------------
        if col.default_value is not None:
            default = col.default_value
            upper = str(default).upper()

            # TEXT / BLOB / JSON cannot have DEFAULT
            if dt in TEXT_TYPES or dt == "JSON":
                pass

            elif dt == "TIMESTAMP" and upper in ("CURRENT_TIMESTAMP", "NOW()"):
                parts.append("DEFAULT CURRENT_TIMESTAMP")

            elif dt == "DATE" and upper in ("CURRENT_DATE", "CURDATE()"):
                parts.append("DEFAULT (CURRENT_DATE)")

            elif dt == "TIME" and upper in ("CURRENT_TIME", "CURTIME()"):
                parts.append("DEFAULT (CURRENT_TIME)")

            elif isinstance(default, bool):
                parts.append(f"DEFAULT {1 if default else 0}")

            elif dt == "ENUM":
                if default not in col.enum_values:
                    raise ValueError(f"Invalid ENUM default {default}")
                parts.append(f"DEFAULT '{default}'")

            elif isinstance(default, str):
                parts.append(f"DEFAULT '{default}'")

            else:
                parts.append(f"DEFAULT {default}")

        # -----------------------------
        # AUTO_INCREMENT
        # -----------------------------
        # if col.is_auto_increment:
        #     if dt not in {"INT", "INTEGER", "BIGINT"}:
        #         raise ValueError("AUTO_INCREMENT only allowed on INT/BIGINT")
        #     parts.append("AUTO_INCREMENT")

        return " ".join(parts)

    def build_constraint_sql(self, table_name, constraint):
        """
        Build MySQL-safe constraint SQL from ReplicaDatabaseConstraint
        """
        try:
            def safe_name(name):
                return (
                    name.replace(" ", "_")
                        .replace("-", "_")
                        .replace(".", "_")
                        .lower()
                )
            base = constraint.constraint_name or f"{constraint.constraint_type}_{table_name}"
            cname = f"`{safe_name(self.db_name)}_{safe_name(table_name)}_{safe_name(base)}`"

            # cols = constraint.columns or []
            if constraint.columns:
                cols = constraint.columns 
            elif constraint.metadata_json and constraint.metadata_json.get("definition"): 
                cols = self.extract_columns_from_definition( constraint.metadata_json["definition"] ) 
            else: 
                cols = []
            cols_sql = ", ".join(f"`{c}`" for c in cols)

            ctype = constraint.constraint_type.upper()

            # -----------------------------
            # PRIMARY KEY
            # -----------------------------
            if ctype == "PRIMARY KEY":
                if not cols:
                    return ""
                return f"PRIMARY KEY ({cols_sql})"

            # -----------------------------
            # UNIQUE
            # -----------------------------
            if ctype == "UNIQUE":
                if not cols:
                    return ""
                return f"CONSTRAINT {cname} UNIQUE ({cols_sql})"

            # -----------------------------
            # FOREIGN KEY
            # -----------------------------
            if ctype == "FOREIGN KEY":
                ref_table, ref_columns = self.extract_fk_from_definition( constraint.metadata_json["definition"] )

                ref_cols = ", ".join(f"`{c}`" for c in ref_columns)

                sql = (
                    f"CONSTRAINT {cname} FOREIGN KEY ({cols_sql}) "
                    f"REFERENCES `{ref_table}` ({ref_cols})"
                )

                valid_actions = {"CASCADE", "SET NULL", "RESTRICT", "NO ACTION"}

                if constraint.on_delete and constraint.on_delete.upper() in valid_actions:
                    sql += f" ON DELETE {constraint.on_delete.upper()}"

                if constraint.on_update and constraint.on_update.upper() in valid_actions:
                    sql += f" ON UPDATE {constraint.on_update.upper()}"

                return sql

            # -----------------------------
            # CHECK
            # -----------------------------
            if ctype == "CHECK":
                if not constraint.check_expression:
                    return ""
                return f"CONSTRAINT {cname} CHECK ({constraint.check_expression})"

            return ""
        except Exception as e:
            print(e)
            return ''    


class ddl:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name
        self.db_helper = db_helper(db_name)

    def create_database(self,
        db_name,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci"
    ):
        """
        Create MySQL database if not exists and switch to it.
        """
        cursor = self.conn.cursor()
        try:
            # 1️⃣ Create database
            create_sql = f"""
            CREATE DATABASE IF NOT EXISTS `{db_name}`
            CHARACTER SET {charset}
            COLLATE {collation};
            """
            cursor.execute(create_sql)
            use_sql = f"USE `{db_name}`;"
            cursor.execute(use_sql)

            print(create_sql)
            # print(use_sql)
            self.conn.commit()
            return True, f"Database `{db_name}` created (if needed) and selected"

        except Exception as e:
            self.conn.rollback()
            return False, f"Error creating/using database `{db_name}`: {e}"

        finally:
            cursor.close()

    def create_table(self, table_name, columns):
        """
        Create MySQL table with ONLY columns (no constraints).
        Safe for dynamic creation.
        """
        cursor = self.conn.cursor()

        try:
            table_sql = [f"CREATE TABLE `{table_name}` ("]
            definitions = []

            # Columns only
            for col in columns:
                definitions.append(self.db_helper.build_column_sql(col))

            table_sql.append(",\n  ".join(definitions))
            table_sql.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")

            final_sql = "\n".join(table_sql)

            cursor.execute(final_sql)

            return True, "Table columns created successfully"

        except Exception as e:
            self.conn.rollback()
            return False, f"Error creating table columns: {e}"

        finally:
            cursor.close()
        
    def add_table_constraints(self, table_name, constraints):
        """
        Add MySQL constraints AFTER all tables exist.
        Handles PK, UNIQUE, CHECK first, then FK.
        """
        cursor = self.conn.cursor()

        try:
            # 1️⃣ First add NON–foreign key constraints
            for cons in constraints:

                if not cons.is_enabled:
                    continue

                if cons.constraint_type == "FOREIGN KEY":
                    continue  # FK added later

                table_name = cons.table_name
                if not table_name:
                    raise ValueError("Table name missing for constraint")

                cons_sql = self.db_helper.build_constraint_sql(table_name, cons)
                if not cons_sql:
                    continue

                alter_sql = f"""
                ALTER TABLE `{table_name}`
                ADD {cons_sql};
                """
                cursor.execute(alter_sql)

            # 2️⃣ Then add FOREIGN KEY constraints
            for cons in constraints:

                if not cons.is_enabled:
                    continue

                if cons.constraint_type != "FOREIGN KEY":
                    continue

                table_name = cons.table_name
                if not table_name:
                    raise ValueError("Table name missing for FK constraint")

                cons_sql = self.db_helper.build_constraint_sql(table_name, cons)
                if not cons_sql:
                    continue

                alter_sql = f"""
                ALTER TABLE `{table_name}`
                ADD {cons_sql};
                """
                # print(alter_sql)
                cursor.execute(alter_sql)

            self.conn.commit()
            # print(alter_sql)
            return True, "Constraints added successfully"

        except Exception as e:
            self.conn.rollback()
            return False, f"Error adding constraints: {e}"

        finally:
            cursor.close()



class dcl:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name

class dql(dql_utility):
    def __init__(self, conn, db_name=None):
        self.conn = conn
        self.db_name = db_name

    def extract_data(self, table_name, **kwargs):
        try:
            query = f'SELECT * FROM {table_name}'
            data = self.run_query(query=query)
            return True, data
        except Exception as e:
            return False, str(e)

















import pandas as pd

class dml:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name.lower()

    def load_data(self, table_name: str, df: pd.DataFrame):
        if df.empty:
            return
        
        use_sql = f"USE `{self.db_name}`;"

        print(self.db_name)
        # Replace NaN with None (DB-safe)
        df = df.where(pd.notnull(df), None)

        columns = list(df.columns)
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]


        placeholders = self._placeholders(len(columns))

        query = f"""
            INSERT INTO {table_name}
            ({", ".join(columns)})
            VALUES {placeholders}
        """

        cursor = self.conn.cursor()

        print(query, values)
        try:
            cursor.execute(use_sql)
            cursor.executemany(query, values)
            self.conn.commit()
        except Exception as e:
            print(e)
            self.conn.rollback()
            raise e
        finally:
            cursor.close()

    def _placeholders(self, count: int):
        return "(" + ", ".join(["%s"] * count) + ")"



class tcl:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name

