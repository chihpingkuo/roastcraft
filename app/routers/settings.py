from fastapi import APIRouter

router = APIRouter()


@router.get("/settings/hello")
async def hello():
    return {"message": "Hello World"}
