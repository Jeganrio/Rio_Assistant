from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from cuby.database import Base

class CubyQueries(Base):
    __tablename__ = "AI_logic_app_cubyqueries"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text)
    answers = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    class Config:
        from_attributes = True
