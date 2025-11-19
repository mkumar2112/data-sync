from fastapi import FastAPI
from backend.src.api.v1.connections import ConnectionRouter as v1_ConnectionRouter
from backend.src.api.v1.connections import DB_ConnectionRouter

app = FastAPI(title="Data Sync Platform")

# v1 Router
connection_router = v1_ConnectionRouter()
app.include_router(connection_router.router)

db_connection_router = DB_ConnectionRouter()
app.include_router(db_connection_router.router)


# Register routes
# app.include_router(connection_router)

# @app.get("/")
# def root():
#     return {"message": "Data Sync Platform Running ✅"}
