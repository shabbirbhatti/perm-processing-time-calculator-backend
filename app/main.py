from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from . import models, database, utils, scraper
from .database import SessionLocal, engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="PERM Processing Time Calculator API",
    description="API for calculating PERM processing times based on data from the U.S. Department of Labor",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Scheduler for automated data updates
scheduler = BackgroundScheduler()

def scheduled_data_update():
    """Function to be called by the scheduler to update data"""
    logger.info("Starting scheduled data update")
    db = SessionLocal()
    try:
        url = os.getenv("SCRAPER_URL", "https://flag.dol.gov/processingtimes")
        success = scraper.update_perm_data(db, url)
        if success:
            logger.info("Scheduled data update completed successfully")
        else:
            logger.error("Scheduled data update failed")
    except Exception as e:
        logger.error(f"Error during scheduled data update: {e}")
    finally:
        db.close()

# Schedule the job to run daily
scheduler.add_job(scheduled_data_update, 'interval', days=1)
scheduler.start()

# API endpoint to calculate PERM processing time
@app.post("/calculate")
def calculate_perm_processing_time(filing_date: str, db: Session = Depends(get_db)):
    """
    Calculate estimated PERM approval date based on filing date.
    """
    if not utils.validate_date_format(filing_date):
        raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD.")
    
    result = utils.calculate_approval_date(filing_date, db)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

# New endpoint to get current processing data without calculation
@app.get("/current-data")
def get_current_processing_data(db: Session = Depends(get_db)):
    """
    Get current PERM processing time data without calculating an approval date.
    """
    result = utils.get_current_processing_data(db)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

# API endpoint to manually trigger data update (admin only)
@app.post("/update-data")
def update_data(db: Session = Depends(get_db)):
    """
    Manually trigger an update of the PERM processing time data.
    """
    url = os.getenv("SCRAPER_URL", "https://flag.dol.gov/processingtimes")
    success = scraper.update_perm_data(db, url)
    
    if success:
        return {"status": "success", "message": "Data updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update data")

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Shutdown event to stop the scheduler
@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
