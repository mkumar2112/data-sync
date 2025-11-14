from fastapi import FastAPI
from backend.src.api.v1.connections import router as connection_router

app = FastAPI(title="Data Sync Platform")

# Register routes
app.include_router(connection_router)

@app.get("/")
def root():
    return {"message": "Data Sync Platform Running ✅"}
