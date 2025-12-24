from fastapi import FastAPI
from backend.src.api.v1.connections import ConnectionRouter as v1_ConnectionRouter, DB_ConnectionRouter
from backend.src.api.v1.sync import Database_Operations as v1_Database_operations
from .core.status import DBStatus, APIStatus

app = FastAPI(title="Data Sync Platform")

# v1 Router
connection_router = v1_ConnectionRouter()
app.include_router(connection_router.router)

db_connection_router = DB_ConnectionRouter()
app.include_router(db_connection_router.router)

v1_databaseOperation = v1_Database_operations()
app.include_router(v1_databaseOperation.router)

@app.on_event("startup")
async def startup_event():
    # Insert all DB statuses
    DBStatus.insert()
    
    # Insert all API statuses
    APIStatus.insert()
    
    print("Statuses initialized")

# Register routes
# app.include_router(connection_router)

# @app.get("/")
# def root():
#     return {"message": "Data Sync Platform Running ✅"}
