import psycopg2
import os
import re


ENTRIES = int(os.getenv('DATA_ENTRIES',50))

def escape_name(name):
    if not name:  # Handle empty or None names
        raise ValueError("The name to escape cannot be None or empty.")
    return f'"{name}"'


class connectsql:
    def __init__(self):
        self.conn = None
        self.connection_details = {}
    def setup_connection(self, host=None, port=5432, user=None, password=None, database=None):
        try:
            if not host or not user or not password:
                raise ValueError("Host, user, and password are required for postgres.")
            # Default to 'postgres' database if no database is provided
            default_database = database or 'postgres'
            self.connection_details = {
                'host': host,
                'user': user,
                'port': port,
                'password': password,
                'dbname': default_database
            }

            self.conn = psycopg2.connect(**self.connection_details)
            return True
        except Exception as e:
            return False
    
    def connectdb(self, db_name):
        try:
            if not self.conn:
                raise ValueError("Database connection is not established. Call setup_connection first.")
            self.conn.close()
            self.conn = psycopg2.connect(
                host=self.connection_details['host'],
                user=self.connection_details['user'],
                password=self.connection_details['password'],
                database=db_name
            )
            return True, f"Connected to PostgreSQL database: {db_name}"
        except Exception as e:
            return False, str(e)

    def get_postgres_version(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            return True, version
        except Exception as e:
            return False, str(e)

    def get_server_status(self):
        try:
            cursor = self.conn.cursor()

            # Background writer stats
            cursor.execute("SELECT * FROM pg_stat_bgwriter")
            row = cursor.fetchone()
            cols = [d[0] for d in cursor.description]
            bgwriter = dict(zip(cols, row))

            # All database stats
            cursor.execute("SELECT * FROM pg_stat_database")
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            databases = [dict(zip(cols, r)) for r in rows]

            return True, {
                "bgwriter": bgwriter,
                "databases": databases
            }

        except Exception as e:
            return False, str(e)
    
    def get_global_variables(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name, setting FROM pg_settings")
            variables = cursor.fetchall()
            return True, {k: v for k, v in variables}
        except Exception as e:
            return False, str(e)
    
    def get_storage_engines(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name, default_version, installed_version FROM pg_available_extensions")
            rows = cursor.fetchall()

            engines = []
            for r in rows:
                engines.append({
                    "name": r[0],
                    "default_version": r[1],
                    "installed_version": r[2]
                })

            return True, engines

        except Exception as e:
            return False, str(e)
    
    def get_database_metadata(self, db_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    datname,
                    pg_encoding_to_char(encoding),
                    datcollate,
                    datctype
                FROM pg_database
                WHERE datname = %s
            """, (db_name,))

            row = cursor.fetchone()
            if not row:
                return False, "Database not found."

            return True, {
                "schema": row[0],
                "encoding": row[1],
                "collation": row[2],
                "ctype": row[3]
            }

        except Exception as e:
            return False, str(e)
    
    def get_all_metadata(self, db_name):
        try:
            meta = {}

            # 1. Version
            status, version = self.get_postgres_version()
            meta["version"] = version if status else f"Error: {version}"

            # 2. Server Status
            status, status_data = self.get_server_status()
            meta["server_status"] = status_data if status else f"Error: {status_data}"

            # 3. Variables
            status, vars_data = self.get_global_variables()
            meta["global_variables"] = vars_data if status else f"Error: {vars_data}"

            # 4. Storage Engines (extensions)
            status, engines_data = self.get_storage_engines()
            meta["storage_engines"] = engines_data if status else f"Error: {engines_data}"

            # 5. Database metadata
            status, db_data = self.get_database_metadata(db_name)
            meta["database"] = db_data if status else f"Error: {db_data}"

            return True, meta

        except Exception as e:
            return False, str(e)

    def db_exists(self, db_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
            db_exit = cursor.fetchone() is not None  # Check if the result is not None
            return db_exit
        except Exception as e:
            return False

    def show_tables(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall() or []
            tables_list = [table[0] for table in tables]
            return tables_list
        except Exception as e:
            return False
        
    def create_db(self, db_name):
        try:
            self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = self.conn.cursor()
            cursor.execute(f"CREATE DATABASE {db_name}")
            cursor.close()
            self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)
            return True, f"Database {db_name} created."
        except Exception as e:
            # # print(f"Error creating database {db_name}: {e}")
            return False, f"Error creating database {db_name}: {e}"

    def deletedb(self, db_name):
        """
        Drop database safely (PostgreSQL).
        """
        if not self.conn:
            return False, "Database connection is not established"

        cursor = self.conn.cursor()
        try:
            db_name = db_name.lower()

            # PostgreSQL: DROP DATABASE must run outside transaction
            self.conn.autocommit = True

            # Terminate active connections to the database
            cursor.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                AND pid <> pg_backend_pid();
            """, (db_name,))

            # Drop database
            cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}";')

            return True, f'Database "{db_name}" deleted successfully'

        except Exception as e:
            return False, str(e)

        finally:
            try:
                cursor.close()
                self.conn.autocommit = False
            except Exception:
                pass


    def close_connection(self):
        """
        Closes the database connection.
        """
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
            
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
                n.nspname AS schema_name,
                c.relkind AS table_type,
                c.reltuples::BIGINT AS row_count,
                pg_total_relation_size(c.oid) AS total_size,
                pg_relation_size(c.oid) AS data_size,
                pg_indexes_size(c.oid) AS index_size,
                c.reloptions
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = %s;
            """

            cursor.execute(metadata_query, (table_name,))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            # Table type mapping
            table_type_map = {
                "r": "table",
                "v": "view",
                "m": "materialized_view",
                "f": "foreign_table"
            }
            columns_constraints = self.get_columns_and_constraints(table_name=table_name)

            return {
                "schema": row[0],
                "engine": None,  # ✅ PostgreSQL has no engine per table
                "row_count": int(row[2]),
                "data_size": row[4],
                "index_size": row[5],
                "table_type": table_type_map.get(row[1], "unknown"),
                "options": row[6],
                **columns_constraints
            }

        except Exception as e:
            return {"error": str(e)}


    # def get_columns_and_constraints(self, table_name):
    #     try:
    #         cursor = self.conn.cursor()

    #         # 1️⃣ Detect schema
    #         cursor.execute("""
    #             SELECT table_schema
    #             FROM information_schema.tables
    #             WHERE table_name = %s
    #             LIMIT 1;
    #         """, (table_name,))
    #         schema_result = cursor.fetchone()

    #         if not schema_result:
    #             return {"error": f"Table '{table_name}' not found"}

    #         schema = schema_result[0]

    #         # 2️⃣ Get PRIMARY KEY & UNIQUE columns
    #         cursor.execute("""
    #             SELECT
    #                 a.attname AS column_name,
    #                 c.contype
    #             FROM pg_constraint c
    #             JOIN pg_class t ON t.oid = c.conrelid
    #             JOIN pg_namespace n ON n.oid = t.relnamespace
    #             JOIN unnest(c.conkey) AS cols(attnum) ON TRUE
    #             JOIN pg_attribute a
    #                 ON a.attnum = cols.attnum
    #                 AND a.attrelid = t.oid
    #             WHERE t.relname = %s
    #             AND n.nspname = %s
    #             AND c.contype IN ('p', 'u');
    #         """, (table_name, schema))

    #         primary_keys = set()
    #         unique_keys = set()

    #         for col, ctype in cursor.fetchall():
    #             if ctype == "p":
    #                 primary_keys.add(col)
    #             elif ctype == "u":
    #                 unique_keys.add(col)

    #         # 3️⃣ Columns (now with PK & UNIQUE flags)
    #         cursor.execute("""
    #             SELECT 
    #                 column_name,
    #                 data_type,
    #                 is_nullable,
    #                 column_default
    #             FROM information_schema.columns
    #             WHERE table_schema = %s
    #             AND table_name = %s
    #             ORDER BY ordinal_position;
    #         """, (schema, table_name))

    #         columns = []
    #         for r in cursor.fetchall():
    #             col_name = r[0]
    #             columns.append({
    #                 "column_name": col_name,
    #                 "data_type": r[1],
    #                 "is_nullable": r[2],
    #                 "default": r[3],
    #                 "is_primary_key": col_name in primary_keys,
    #                 "is_unique": col_name in unique_keys,
    #             })

    #         # 4️⃣ FULL constraints (unchanged)
    #         cursor.execute("""
    #             SELECT
    #                 con.conname,
    #                 con.contype,
    #                 pg_get_constraintdef(con.oid) AS definition
    #             FROM pg_constraint con
    #             JOIN pg_class rel ON rel.oid = con.conrelid
    #             JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    #             WHERE rel.relname = %s
    #             AND nsp.nspname = %s;
    #         """, (table_name, schema))

    #         constraints = []
    #         for name, ctype, definition in cursor.fetchall():
    #             constraints.append({
    #                 "constraint_name": name,
    #                 "constraint_type": {
    #                     "p": "PRIMARY KEY",
    #                     "f": "FOREIGN KEY",
    #                     "u": "UNIQUE",
    #                     "c": "CHECK"
    #                 }.get(ctype, ctype),
    #                 "definition": definition
    #             })

    #         # 5️⃣ Indexes (unchanged)
    #         cursor.execute("""
    #             SELECT
    #                 indexname,
    #                 indexdef
    #             FROM pg_indexes
    #             WHERE schemaname = %s
    #             AND tablename = %s;
    #         """, (schema, table_name))

    #         indexes = [
    #             {"index_name": r[0], "definition": r[1]}
    #             for r in cursor.fetchall()
    #         ]

    #         cursor.close()

    #         return {
    #             "schema": schema,
    #             "columns": columns,
    #             "constraints": constraints,
    #             "indexes": indexes
    #         }

    #     except Exception as e:
    #         return {"error": str(e)}
    def get_columns_and_constraints(self, table_name):
        try:
            cursor = self.conn.cursor()

            # --------------------------------------------------
            # 1️⃣ Detect schema
            # --------------------------------------------------
            cursor.execute("""
                SELECT table_schema
                FROM information_schema.tables
                WHERE table_name = %s
                LIMIT 1;
            """, (table_name,))
            schema_row = cursor.fetchone()

            if not schema_row:
                return {"error": f"Table '{table_name}' not found"}

            schema = schema_row[0]

            # --------------------------------------------------
            # 2️⃣ PRIMARY KEY & UNIQUE columns
            # --------------------------------------------------
            cursor.execute("""
                SELECT
                    a.attname AS column_name,
                    c.contype
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN unnest(c.conkey) AS cols(attnum) ON TRUE
                JOIN pg_attribute a
                    ON a.attnum = cols.attnum
                    AND a.attrelid = t.oid
                WHERE t.relname = %s
                AND n.nspname = %s
                AND c.contype IN ('p', 'u');
            """, (table_name, schema))

            primary_keys = set()
            unique_keys = set()

            for col, ctype in cursor.fetchall():
                if ctype == "p":
                    primary_keys.add(col)
                elif ctype == "u":
                    unique_keys.add(col)

            # --------------------------------------------------
            # 3️⃣ ENUM values (Postgres enums are TYPES)
            # --------------------------------------------------
            cursor.execute("""
                SELECT
                    t.typname AS enum_name,
                    e.enumlabel AS enum_value
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = %s
                ORDER BY e.enumsortorder;
            """, (schema,))

            enum_map = {}
            for enum_name, enum_value in cursor.fetchall():
                enum_map.setdefault(enum_name, []).append(enum_value)

            # --------------------------------------------------
            # 4️⃣ Column details (FULL)
            # --------------------------------------------------
            cursor.execute("""
                SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    c.udt_name
                FROM information_schema.columns c
                WHERE c.table_schema = %s
                AND c.table_name = %s
                ORDER BY c.ordinal_position;
            """, (schema, table_name))

            formatted_columns = []

            for (
                col_name,
                data_type,
                is_nullable,
                default,
                char_length,
                numeric_precision,
                numeric_scale,
                udt_name
            ) in cursor.fetchall():

                # Auto increment detection
                is_auto_increment = (
                    default is not None and
                    (
                        "nextval(" in default or
                        "identity" in default.lower()
                    )
                )

                # ENUM detection
                enum_values = enum_map.get(udt_name)

                formatted_columns.append({
                    "column_name": col_name,
                    "data_type": data_type.upper(),
                    "udt_name": udt_name.upper(),
                    "is_nullable": is_nullable == "YES",
                    "default": default,

                    # 👇 MySQL-equivalent fields
                    "length": char_length,
                    "precision": numeric_precision,
                    "scale": numeric_scale,

                    "is_auto_increment": is_auto_increment,
                    "is_unsigned": False,  # ❌ PostgreSQL has no UNSIGNED

                    "is_primary_key": col_name in primary_keys,
                    "is_unique": col_name in unique_keys,

                    "enum_values": enum_values
                })

            # --------------------------------------------------
            # 5️⃣ Full constraints (PK, FK, UNIQUE, CHECK)
            # --------------------------------------------------
            cursor.execute("""
                SELECT
                    con.conname,
                    con.contype,
                    pg_get_constraintdef(con.oid) AS definition
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE rel.relname = %s
                AND nsp.nspname = %s
                ORDER BY con.conname;
            """, (table_name, schema))

            formatted_constraints = []
            for name, ctype, definition in cursor.fetchall():
                formatted_constraints.append({
                    "constraint_name": name,
                    "constraint_type": {
                        "p": "PRIMARY KEY",
                        "u": "UNIQUE",
                        "f": "FOREIGN KEY",
                        "c": "CHECK",
                        "x": "EXCLUDE"
                    }.get(ctype, ctype),
                    "definition": definition
                })

            cursor.close()

            return {
                "schema": schema,
                "columns": formatted_columns,
                "constraints": formatted_constraints
            }

        except Exception as e:
            return {"error": str(e)}


class db_helper:
    def __init__(self, db_name):
        self.db_name = db_name

    def generate_constraint_name(self, table_name, ctype, columns):
        import hashlib
        raw = f"{self.db_name}_{table_name}_{ctype}_{'_'.join(columns if columns else [])}"
        short = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"{table_name}_{ctype}_{short}".replace(' ', '').lower()

    # def build_column_sql(self, col):
    #     """
    #     Convert DatabaseColumn metadata into PostgreSQL column SQL.
    #     """
    #     data_type = col.data_type.upper()

    #     # SERIAL handling
    #     if data_type == "INT" and col.is_auto_increment:
    #         data_type = "SERIAL"
    #     elif data_type == "BIGINT" and col.is_auto_increment:
    #         data_type = "BIGSERIAL"

    #     parts = [f'"{col.column_name}"', data_type]

    #     # Length / precision
    #     if col.length and data_type not in ("TEXT", "SERIAL", "BIGSERIAL"):
    #         parts[-1] += f"({col.length})"
    #     elif col.precision and col.scale:
    #         parts[-1] += f"({col.precision},{col.scale})"

    #     # NULL / NOT NULL
    #     if not col.is_nullable:
    #         parts.append("NOT NULL")

    #     # DEFAULT
    #     if col.default_value is not None:
    #         default = col.default_value
    #         if isinstance(default, str) and not default.upper().startswith("CURRENT"):
    #             default = f"'{default}'"
    #         parts.append(f"DEFAULT {default}")

    #     return " ".join(parts)


    def extract_columns_from_definition(self, definition: str):
        match = re.search(r"\((.*?)\)", definition)
        if not match:
            return []
        cols = match.group(1)
        return [c.strip(' "') for c in cols.split(",")]

    def extract_fk_from_definition(self, definition: str):
        pattern = re.compile(
            r"REFERENCES\s+\"?(\w+)\"?\s*\(([^)]+)\)",
            re.IGNORECASE
        )
        match = pattern.search(definition)
        if not match:
            return None, []

        table = match.group(1)
        cols = [c.strip(' "') for c in match.group(2).split(",")]
        return table, cols

    # def build_constraint_sql(self, table_name, constraint):
    #     if constraint.columns:
    #         cols_list = constraint.columns
    #     elif constraint.metadata_json and constraint.metadata_json.get("definition"):
    #         cols_list = self.extract_columns_from_definition(
    #             constraint.metadata_json["definition"]
    #         )
    #     else:
    #         cols_list = []
    #     cname = self.generate_constraint_name(
    #         table_name,
    #         constraint.constraint_type,
    #         cols_list
    #     )



    #     ctype = constraint.constraint_type.upper()

    #     if not cols_list and ctype not in ("CHECK",):
    #         return ""

    #     cols = ", ".join(f'"{c}"' for c in cols_list)

    #     # PRIMARY KEY
    #     if ctype == "PRIMARY KEY":
    #         return f"PRIMARY KEY ({cols})"

    #     # UNIQUE
    #     if ctype == "UNIQUE":
    #         return f"CONSTRAINT {cname} UNIQUE ({cols})"

    #     # FOREIGN KEY
    #     if ctype == "FOREIGN KEY":
    #         ref_table = constraint.referenced_table
    #         ref_columns = constraint.referenced_columns or []

    #         if (
    #             (not ref_table or not ref_columns)
    #             and constraint.metadata_json
    #             and constraint.metadata_json.get("definition")
    #         ):
    #             ref_table, ref_columns = self.extract_fk_from_definition(
    #                 constraint.metadata_json["definition"]
    #             )

    #         if not ref_table or not ref_columns:
    #             return ""

    #         ref_cols = ", ".join(f'"{c}"' for c in ref_columns)

    #         sql = (
    #             f"CONSTRAINT {cname} FOREIGN KEY ({cols}) "
    #             f'REFERENCES "{ref_table}" ({ref_cols})'
    #         )

    #         if constraint.on_delete:
    #             sql += f" ON DELETE {constraint.on_delete}"
    #         if constraint.on_update:
    #             sql += f" ON UPDATE {constraint.on_update}"

    #         return sql

    #     # CHECK
    #     if ctype == "CHECK" and constraint.check_expression:
    #         return f"CONSTRAINT {cname} CHECK ({constraint.check_expression})"

    #     return ""

    def build_constraint_sql(self, table_name, constraint):
        """
        Build PostgreSQL-safe constraint SQL from ReplicaDatabaseConstraint
        """
        try:
            # ---------------------------------
            # Safe constraint name
            # ---------------------------------
            def safe_name(name):
                return (
                    name.replace(" ", "_")
                        .replace("-", "_")
                        .replace(".", "_")
                        .lower()
                )

            base = constraint.constraint_name or f"{constraint.constraint_type}_{table_name}"
            cname = f'"{safe_name(table_name)}_{safe_name(base)}"'

            # ---------------------------------
            # Columns (direct or extracted)
            # ---------------------------------
            if constraint.columns:
                cols_list = constraint.columns
            elif constraint.metadata_json and constraint.metadata_json.get("definition"):
                cols_list = self.extract_columns_from_definition(
                    constraint.metadata_json["definition"]
                )
            else:
                cols_list = []

            ctype = constraint.constraint_type.upper()

            # CHECK does not require columns
            if not cols_list and ctype not in ("CHECK",):
                return ""

            cols_sql = ", ".join(f'"{c}"' for c in cols_list)

            # ---------------------------------
            # PRIMARY KEY
            # ---------------------------------
            if ctype == "PRIMARY KEY":
                return f"PRIMARY KEY ({cols_sql})"

            # ---------------------------------
            # UNIQUE
            # ---------------------------------
            if ctype == "UNIQUE":
                return f"CONSTRAINT {cname} UNIQUE ({cols_sql})"

            # ---------------------------------
            # FOREIGN KEY
            # ---------------------------------
            if ctype == "FOREIGN KEY":

                ref_table = constraint.referenced_table
                ref_columns = constraint.referenced_columns or []

                # Fallback: parse from definition
                if (
                    (not ref_table or not ref_columns)
                    and constraint.metadata_json
                    and constraint.metadata_json.get("definition")
                ):
                    ref_table, ref_columns = self.extract_fk_from_definition(
                        constraint.metadata_json["definition"]
                    )

                if not ref_table or not ref_columns:
                    return ""

                ref_cols_sql = ", ".join(f'"{c}"' for c in ref_columns)

                sql = (
                    f"CONSTRAINT {cname} FOREIGN KEY ({cols_sql}) "
                    f'REFERENCES "{ref_table}" ({ref_cols_sql})'
                )

                valid_actions = {
                    "CASCADE", "SET NULL", "SET DEFAULT",
                    "RESTRICT", "NO ACTION"
                }

                if constraint.on_delete and constraint.on_delete.upper() in valid_actions:
                    sql += f" ON DELETE {constraint.on_delete.upper()}"

                if constraint.on_update and constraint.on_update.upper() in valid_actions:
                    sql += f" ON UPDATE {constraint.on_update.upper()}"

                return sql

            # ---------------------------------
            # CHECK
            # ---------------------------------
            if ctype == "CHECK":
                expr = None

                # Prefer explicit check expression
                if getattr(constraint, "check_expression", None):
                    expr = constraint.check_expression

                # Fallback to metadata JSON definition
                elif (
                    getattr(constraint, "metadata_json", None)
                    and constraint.metadata_json.get("definition")
                ):
                    defn = constraint.metadata_json["definition"]
                    # Remove leading 'CONSTRAINT <name> ' if present
                    if defn.upper().startswith(f"CONSTRAINT {cname.upper()} "):
                        expr = defn[len(f"CONSTRAINT {cname} "):]
                    else:
                        expr = defn

                # Skip if nothing found
                if not expr:
                    return ""

                # Remove duplicate CHECK if present
                expr = expr.strip()
                if expr.upper().startswith("CHECK (") and expr.endswith(")"):
                    expr = expr[6:-1].strip()  # remove outer 'CHECK (...)'

                # Fix common type issues
                expr = expr.replace("::money", "::numeric")

                # Build proper ALTER TABLE SQL
                return f'CONSTRAINT "{cname}" CHECK ({expr})'

            return ""

        except Exception as e:
            print(e)
            return ""

    def build_column_sql(self, col):
        """
        Build full PostgreSQL-safe column SQL from ReplicaDatabaseColumn
        """
        parts = [f'"{col.column_name}"']
        dt = (col.data_type or "").upper()
        udt = (getattr(col, "udt_name", "") or "").lower()

        # Normalize timestamp names
        dt = dt.replace(" WITHOUT TIME ZONE", "").replace(" WITH TIME ZONE", "")

        # -----------------------------
        # AUTO-INCREMENT (IDENTITY)
        # -----------------------------
        if col.is_auto_increment:
            if dt in {"INT", "INTEGER"}:
                parts.append("INTEGER GENERATED BY DEFAULT AS IDENTITY")
            elif dt == "BIGINT":
                parts.append("BIGINT GENERATED BY DEFAULT AS IDENTITY")
            else:
                raise ValueError("AUTO_INCREMENT only allowed on INT/BIGINT")

        # -----------------------------
        # ARRAY TYPES
        # -----------------------------
        elif dt == "ARRAY" and udt.startswith("_"):
            base = udt[1:]
            pg_array_map = {
                "text": "TEXT",
                "varchar": "VARCHAR",
                "int4": "INTEGER",
                "int8": "BIGINT",
                "uuid": "UUID",
                "bool": "BOOLEAN",
                "numeric": "NUMERIC"
            }
            parts.append(f"{pg_array_map.get(base, base.upper())}[]")

        # -----------------------------
        # USER-DEFINED (ENUM / DOMAIN)
        # -----------------------------
        elif dt == "USER-DEFINED":
            if not udt:
                raise ValueError(f"USER-DEFINED type without udt_name for {col.column_name}")
            parts.append(f'"{udt}"')

        # -----------------------------
        # MONEY → convert to NUMERIC(12,2)
        # -----------------------------
        elif dt == "MONEY":
            parts.append("NUMERIC(12,2)")
        
        elif dt == "INET":
            parts.append("INET")

        # -----------------------------
        # STRING TYPES
        # -----------------------------
        elif dt in {"CHAR", "CHARACTER", "VARCHAR", "CHARACTER VARYING"}:
            parts.append(f"{dt}({col.length or 255})")

        # -----------------------------
        # TEXT TYPES
        # -----------------------------
        elif dt in {"TEXT"} or udt == "text":
            parts.append("TEXT")

        # -----------------------------
        # NUMERIC
        # -----------------------------
        elif dt in {"DECIMAL", "NUMERIC"}:
            parts.append(f"{dt}({col.precision or 10},{col.scale or 0})")

        elif dt in {"SMALLINT", "INTEGER", "BIGINT", "REAL", "DOUBLE PRECISION"}:
            parts.append("INTEGER" if dt == "INT" else dt)

        # -----------------------------
        # BOOLEAN / JSON / UUID
        # -----------------------------
        elif dt == "BOOLEAN":
            parts.append("BOOLEAN")
        elif dt in {"JSON", "JSONB"}:
            parts.append(dt)
        elif dt == "UUID":
            parts.append("UUID")

        # -----------------------------
        # DATE / TIME
        # -----------------------------
        elif dt == "TIMESTAMP":
            parts.append("TIMESTAMP WITHOUT TIME ZONE")
        elif dt == "TIMESTAMPTZ":
            parts.append("TIMESTAMP WITH TIME ZONE")
        elif dt in {"DATE", "TIME"}:
            parts.append(dt)

        else:
            raise ValueError(f"Unsupported PostgreSQL datatype: {dt} (udt={udt})")

        # -----------------------------
        # NULL / NOT NULL
        # -----------------------------
        if not col.is_nullable:
            parts.append("NOT NULL")

        # -----------------------------
        # DEFAULT (SKIP for IDENTITY)
        # -----------------------------
        if col.default_value is not None and not col.is_auto_increment:
            default = col.default_value
            upper = str(default).upper()

            # BOOLEAN
            if isinstance(default, bool):
                parts.append(f"DEFAULT {'TRUE' if default else 'FALSE'}")
            # TIMESTAMP / DATE / TIME
            elif upper in {"CURRENT_TIMESTAMP", "NOW()"}:
                parts.append("DEFAULT CURRENT_TIMESTAMP")
            elif upper == "CURRENT_DATE":
                parts.append("DEFAULT CURRENT_DATE")
            elif upper == "CURRENT_TIME":
                parts.append("DEFAULT CURRENT_TIME")
            # STRING / ENUM
            elif isinstance(default, str):
                if dt == "USER-DEFINED":  # ENUM
                    parts.append(f"DEFAULT '{default}'::{udt}")
                else:
                    parts.append(f"DEFAULT '{default}'")

            # NUMERIC / MONEY
            else:
                parts.append(f"DEFAULT {default}")

        return " ".join(parts)

    def create_enum_if_not_exists(self, conn, col):
        """
        Create ENUM type in PostgreSQL if it doesn't exist.
        col: should have .table_name, .column_name, .enum_values
        """
        if not getattr(col, "enum_values", None):
            return  # nothing to do

        enum_type_name = f"{col.table_name}_{col.column_name}_enum"
        enum_values = col.enum_values

        # Build ENUM values SQL: 'pending','shipped','delivered'
        enum_values_sql = ", ".join(f"'{v}'" for v in enum_values)

        sql = f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = '{enum_type_name}'
            ) THEN
                CREATE TYPE "{enum_type_name}" AS ENUM ({enum_values_sql});
            END IF;
        END$$;
        """

        with conn.cursor() as cursor:
            cursor.execute(sql)
            conn.commit()


class ddl:
    def __init__(self, conn, db_name):
        self.conn = conn
        self.db_name = db_name
        self.db_helper = db_helper(db_name)

    def create_database(self, db_name, charset="utf8", collation=None):
        """
        PostgreSQL: CREATE DATABASE must be outside transaction.
        """
        self.conn.autocommit = True
        cursor = self.conn.cursor()
        try:
            create_db_sql =  f'CREATE DATABASE "{db_name}";'
            cursor.execute(create_db_sql)
            return True, f'Database "{db_name}" created'
        except Exception as e:
            return False, f"Error creating database `{db_name}`: {e}"
        finally:
            cursor.close()
            self.conn.autocommit = False

    def create_table(self, table_name, columns):
        """
        Create PostgreSQL table with columns only.
        """
        cursor = self.conn.cursor()
        try:
            table_sql = [f'CREATE TABLE "{table_name}" (']
            definitions = []
            self.db_helper.create_enum_if_not_exists(self.conn, columns)

            for col in columns:
                definitions.append(self.db_helper.build_column_sql(col))

            table_sql.append(",\n  ".join(definitions))
            table_sql.append(");")

            final_sql = "\n".join(table_sql)
            print(final_sql)
            cursor.execute(final_sql)
            self.conn.commit()

            return True, "Table columns created successfully"

        except Exception as e:
            print(e)
            self.conn.rollback()
            return False, f"Error creating table columns: {e}"

        finally:
            cursor.close()

    def add_table_constraints(self, table_name, constraints):
        """
        Add PostgreSQL constraints.
        Foreign keys are added last.
        """
        cursor = self.conn.cursor()
        try:
            # 1️⃣ First add NON–foreign key constraints
            for cons in constraints:
                if not cons.is_enabled:
                    continue

                if cons.constraint_type == "FOREIGN KEY":
                    continue  # skip FK for now

                table_name = cons.table_name
                cons_sql = self.db_helper.build_constraint_sql(table_name, cons)

                if not cons_sql:
                    continue

                alter_sql = f'ALTER TABLE "{table_name}" ADD {cons_sql};'
                print(alter_sql)
                cursor.execute(alter_sql)

            # 2️⃣ Then add FOREIGN KEY constraints
            for cons in constraints:
                if not cons.is_enabled:
                    continue

                if cons.constraint_type != "FOREIGN KEY":
                    continue

                table_name = cons.table_name
                cons_sql = self.db_helper.build_constraint_sql(table_name, cons)

                if not cons_sql:
                    continue

                alter_sql = f'ALTER TABLE "{table_name}" ADD {cons_sql};'
                cursor.execute(alter_sql)
                print(alter_sql)


            self.conn.commit()
            return True, "Constraints added successfully"

        except Exception as e:
            self.conn.rollback()
            return False, f"Error adding constraints: {e}"

        finally:
            cursor.close()



class dml():
    def __init__(self):
        pass

    def load_data(self, table_name: str, df):
        pass


    