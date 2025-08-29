from datetime import datetime, timedelta
from typing import Dict, Optional
from .models import PermProcessingTime
from sqlalchemy.orm import Session

def calculate_approval_date(filing_date: str, db: Session) -> Dict[str, str]:
    """
    Calculate the estimated approval date based on the filing date and current processing times.
    """
    try:
        # Parse the filing date
        filing_dt = datetime.strptime(filing_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Please use YYYY-MM-DD."}
    
    # Get the latest processing time data
    latest_data = db.query(PermProcessingTime).order_by(PermProcessingTime.last_updated.desc()).first()
    
    if not latest_data:
        return {"error": "No processing time data available. Please try again later."}
    
    # Calculate estimated approval date
    average_days = latest_data.average_days
    estimated_approval_dt = filing_dt + timedelta(days=average_days)
    estimated_approval_date = estimated_approval_dt.strftime("%Y-%m-%d")
    
    # Format last updated date
    last_updated = latest_data.last_updated.strftime("%Y-%m-%d")
    
    return {
        "estimated_approval_date": estimated_approval_date,
        "average_processing_days": str(average_days),
        "last_updated": last_updated,
        "priority_date": latest_data.priority_date
    }

def validate_date_format(date_string: str) -> bool:
    """
    Validate if the date string is in YYYY-MM-DD format.
    """
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_current_processing_data(db: Session) -> Dict[str, str]:
    """
    Get the current processing time data without calculating an approval date.
    """
    latest_data = db.query(PermProcessingTime).order_by(PermProcessingTime.last_updated.desc()).first()
    
    if not latest_data:
        return {"error": "No processing time data available. Please try again later."}
    
    return {
        "average_processing_days": str(latest_data.average_days),
        "priority_date": latest_data.priority_date,
        "last_updated": latest_data.last_updated.strftime("%Y-%m-%d")
    }
