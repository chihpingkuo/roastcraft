from fastapi import APIRouter

router = APIRouter(prefix="/settings")


@router.get("/hello")
async def hello():
    return {"message": "Hello World"}
