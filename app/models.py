from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class PermProcessingTime(Base):
    __tablename__ = "perm_processing_times"
    
    id = Column(Integer, primary_key=True, index=True)
    average_days = Column(Float, nullable=False)
    priority_date = Column(String, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
