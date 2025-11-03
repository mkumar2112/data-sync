from fastapi import FastAPI
from api.v1 import connections, sync

app = FastAPI(title="Data Sync Platform", version="1.0.0")

# routers
app.include_router(connections.router, prefix="/api/v1/connections", tags=["Connections"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["Sync"])

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "FastAPI Working ✅"}
