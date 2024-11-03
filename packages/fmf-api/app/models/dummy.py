from datetime import datetime
from pydantic import BaseModel


class Dummy(BaseModel):
    message: str
    date: datetime
    