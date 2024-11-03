from fastapi import FastAPI

from .routers import dummy

app = FastAPI()

app.include_router(dummy.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}