




class dql_utility:
    def __init__(self, conn, db_name=None):
        self.conn = conn
        self.db_name = db_name

    # ==================================================
    # CORE EXECUTION
    # ==================================================
    def run_query(self, query, params=None, fetch="all"):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params or ())
            if fetch == "one":
                return cursor.fetchone()
            return cursor.fetchall()
        finally:
            cursor.close()

    # ==================================================
    # WHERE / FILTERING
    # ==================================================
    def where(self, query, condition):
        if " where " in query.lower():
            return f"{query} AND {condition}"
        return f"{query} WHERE {condition}"

    def case_when(self, condition, true_val, false_val, alias=None):
        sql = f"CASE WHEN {condition} THEN {true_val} ELSE {false_val} END"
        return f"{sql} AS {alias}" if alias else sql

    # ==================================================
    # ORDER / SORT
    # ==================================================
    def order_by(self, query, columns):
        return f"{query} ORDER BY {columns}"

    # ==================================================
    # PAGINATION (MySQL)
    # ==================================================
    def pagination(self, query, limit, offset=None):
        if offset is not None:
            return f"{query} LIMIT {offset}, {limit}"
        return f"{query} LIMIT {limit}"

    # ==================================================
    # GROUPING
    # ==================================================
    def group_by(self, query, columns):
        return f"{query} GROUP BY {columns}"

    def having(self, query, condition):
        return f"{query} HAVING {condition}"

    # ==================================================
    # JOINS
    # ==================================================
    def join(self, query, join_type, table, condition):
        """
        join_type: INNER | LEFT | RIGHT | CROSS
        """
        return f"{query} {join_type} JOIN {table} ON {condition}"

    # ==================================================
    # SUB QUERY
    # ==================================================
    def sub_query(self, query, alias):
        return f"({query}) AS {alias}"

    def exists(self, sub_query):
        return f"EXISTS ({sub_query})"

    # ==================================================
    # DISTINCT & SET
    # ==================================================
    def distinct(self, columns="*"):
        return f"SELECT DISTINCT {columns}"

    def union(self, q1, q2, all=False):
        return f"{q1} UNION{' ALL' if all else ''} {q2}"

    # ==================================================
    # AGGREGATE (MULTI ROW)
    # ==================================================
    def multi_row_function(self, func, column="*", alias=None):
        sql = f"{func}({column})"
        return f"{sql} AS {alias}" if alias else sql

    # ==================================================
    # SINGLE ROW FUNCTIONS
    # ==================================================
    def single_row_function(self, func, *args, alias=None):
        sql = f"{func}({', '.join(args)})"
        return f"{sql} AS {alias}" if alias else sql

    # ==================================================
    # WINDOW FUNCTIONS (MySQL 8+)
    # ==================================================
    def rank(self, rank_type="RANK", partition_by=None, order_by=None):
        over = []
        if partition_by:
            over.append(f"PARTITION BY {partition_by}")
        if order_by:
            over.append(f"ORDER BY {order_by}")

        return f"{rank_type}() OVER ({' '.join(over)})"

    def window_function(self, func, column, partition_by=None, order_by=None, alias=None):
        over = []
        if partition_by:
            over.append(f"PARTITION BY {partition_by}")
        if order_by:
            over.append(f"ORDER BY {order_by}")

        sql = f"{func}({column}) OVER ({' '.join(over)})"
        return f"{sql} AS {alias}" if alias else sql

    # ==================================================
    # CTE (WITH)
    # ==================================================
    def cte(self, name, query, recursive=False):
        return f"WITH {'RECURSIVE ' if recursive else ''}{name} AS ({query})"

    # ==================================================
    # JSON FUNCTIONS
    # ==================================================
    def json_extract(self, column, path, alias=None):
        sql = f"JSON_EXTRACT({column}, '{path}')"
        return f"{sql} AS {alias}" if alias else sql

    def json_value(self, column, path, alias=None):
        sql = f"{column}->>'{path}'"
        return f"{sql} AS {alias}" if alias else sql

    # ==================================================
    # FULL TEXT SEARCH
    # ==================================================
    def full_text_search(self, columns, keyword, boolean=False):
        mode = "IN BOOLEAN MODE" if boolean else ""
        return f"MATCH({columns}) AGAINST ('{keyword}' {mode})"

    # ==================================================
    # METADATA
    # ==================================================
    def explain(self, query):
        return f"EXPLAIN {query}"

    def analyze(self, query):
        return f"ANALYZE {query}"

    # ==================================================
    # COUNT WRAPPER
    # ==================================================
    def count(self, base_query):
        return f"SELECT COUNT(*) FROM ({base_query}) AS _cnt"

    # ==================================================
    # SAFETY
    # ==================================================
    def validate_dql(self, query):
        allowed = ("select", "show", "describe", "explain", "with")
        if not query.strip().lower().startswith(allowed):
            raise ValueError("Only DQL queries are allowed")





