from fastapi import APIRouter

router = APIRouter()

@router.post("/")
def run_sync():
    return {"status": "sync started"}

