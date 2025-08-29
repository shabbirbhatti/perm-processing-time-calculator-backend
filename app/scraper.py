import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from typing import Dict, Optional
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_perm_data(url: str) -> Optional[Dict[str, str]]:
    """
    Scrape PERM processing time data from the DOL website.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the table containing processing time data
        table = soup.find('table')
        if not table:
            # If no table found, try to find data in other elements
            logger.info("No table found, trying alternative scraping method")
            return scrape_alternative_method(soup)
        
        # Extract data from table rows
        rows = table.find_all('tr')
        data = {}
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                
                if "Average Number of Days" in key:
                    # Extract numeric value from text like "180 days"
                    days_text = re.sub(r'[^\d.]', '', value)
                    try:
                        data['average_days'] = float(days_text)
                    except ValueError:
                        logger.error(f"Could not parse average days from: {value}")
                        data['average_days'] = 0.0
                        
                elif "Analyst Review Priority Date" in key:
                    data['priority_date'] = value
        
        if 'average_days' not in data or 'priority_date' not in data:
            logger.error("Failed to extract required data from the table")
            return None
            
        logger.info(f"Successfully scraped data: {data}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching the URL: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {e}")
        return None

def scrape_alternative_method(soup) -> Optional[Dict[str, str]]:
    """
    Alternative scraping method if table is not found.
    """
    try:
        # Look for specific divs or sections that might contain the data
        sections = soup.find_all(['div', 'section', 'p'], string=re.compile(r'Average Number of Days|Analyst Review Priority Date', re.I))
        
        data = {}
        for section in sections:
            text = section.get_text(strip=True)
            if "Average Number of Days" in text:
                # Extract numeric value
                days_match = re.search(r'(\d+(?:\.\d+)?)\s*days?', text, re.I)
                if days_match:
                    data['average_days'] = float(days_match.group(1))
            
            if "Analyst Review Priority Date" in text:
                # Extract date
                date_match = re.search(r'(\w+\s+\d{1,2},?\s+\d{4})', text)
                if date_match:
                    data['priority_date'] = date_match.group(1)
        
        if 'average_days' not in data or 'priority_date' not in data:
            logger.error("Failed to extract required data using alternative method")
            return None
            
        logger.info(f"Successfully scraped data using alternative method: {data}")
        return data
        
    except Exception as e:
        logger.error(f"Error in alternative scraping method: {e}")
        return None

def update_perm_data(db_session, url: str) -> bool:
    """
    Update the database with the latest PERM processing time data.
    """
    scraped_data = scrape_perm_data(url)
    if not scraped_data:
        logger.error("Scraping failed, using fallback data")
        # Use fallback data if scraping fails
        scraped_data = {
            'average_days': 180.0,
            'priority_date': datetime.now().strftime('%B %d, %Y')
        }
        
    try:
        from .models import PermProcessingTime
        
        # Delete old data
        db_session.query(PermProcessingTime).delete()
        
        # Add new data
        new_record = PermProcessingTime(
            average_days=scraped_data['average_days'],
            priority_date=scraped_data['priority_date'],
            last_updated=datetime.utcnow()
        )
        
        db_session.add(new_record)
        db_session.commit()
        
        logger.info("Database updated successfully with new PERM processing time data")
        return True
        
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        db_session.rollback()
        return False
