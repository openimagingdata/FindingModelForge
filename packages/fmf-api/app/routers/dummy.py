from datetime import datetime

from fastapi import APIRouter
from findingmodelforge import hello

from ..models.dummy import Dummy

router = APIRouter(
    prefix="/dummy",
    tags=["dummy"],
)


@router.get("/fmf", response_model=Dummy)
async def read_dummy() -> Dummy:
    return Dummy(message=hello(), date=datetime.now())
