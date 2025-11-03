from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ConnectionCreate(BaseModel):
    name: str
    db_type: str   # mysql/postgres
    host: str
    port: int
    username: str
    password: str
    database: str

@router.post("/")
def create_connection(payload: ConnectionCreate):
    # TODO: Save to DB (later)
    return {"msg": "Connection saved", "data": payload}
