from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: str = Field(index=True, unique=True)
    is_premium: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    scans: List["Scan"] = Relationship(back_populates="user")

class Scan(SQLModel, table=True):
    __tablename__ = "scans"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    url: str = Field(index=True)
    result: dict = Field(default={}, sa_column=Column(JSONB))
    score: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    user: Optional[User] = Relationship(back_populates="scans")
