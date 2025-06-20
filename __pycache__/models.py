from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    blocked: str = ""
    banned: bool = False

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender: str
    receiver: str
    content: str
    timestamp: str = datetime.now().isoformat()
