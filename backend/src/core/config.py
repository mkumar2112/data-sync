
available_db_in_sql = ['mysql', 'postgres']
available_db_in_nosql = ['mongo']

db_status_code = {
    1: {
        "status_code": 201,
        "status_message": "Record created successfully",
        "color": "#2e7d32",        # dark green
        "bg-color": "#e8f5e9"       # light green
    },
    2: {
        "status_code": 200,
        "status_message": "Record updated successfully",
        "color": "#1565c0",         # dark blue
        "bg-color": "#e3f2fd"       # light blue
    },
    3: {
        "status_code": 200,
        "status_message": "Record deleted successfully",
        "color": "#c62828",         # dark red
        "bg-color": "#ffebee"       # light red
    },
    4: {
        "status_code": 409,
        "status_message": "Record already exists",
        "color": "#ef6c00",         # dark orange
        "bg-color": "#fff3e0"       # light orange/yellow
    },
    5: {
        "status_code": 404,
        "status_message": "Record not found",
        "color": "#616161",         # dark grey
        "bg-color": "#f5f5f5"       # light grey
    },
    6: {
        "status_code": 500,
        "status_message": "Database transaction failed",
        "color": "#b71c1c",         # deep red
        "bg-color": "#ffebee"       # soft red
    },
    7: {
        "status_code": 500,
        "status_message": "Transaction rollback executed",
        "color": "#880e4f",         # dark pink/red
        "bg-color": "#fce4ec"       # light pink
    },
    8: {
        "status_code": 200,
        "status_message": "Transaction committed successfully",
        "color": "#2e7d32",         # green
        "bg-color": "#e8f5e9"       # light green
    }
}
