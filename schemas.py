from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CubyQueryBase(BaseModel):
    query: str
    answers: Optional[str] = None

class CubyQueryCreate(CubyQueryBase):
    pass

class CubyQueryUpdate(BaseModel):
    query: Optional[str] = None
    answers: Optional[str] = None

class CubyQueryResponse(CubyQueryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AIStartResponse(BaseModel):
    status: str
    message: str

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
