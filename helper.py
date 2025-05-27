import json
import datetime
import logging
import os
import dateutil.parser
import re
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
        
def save_to_json(filename, variable_data, check_recent = False):
    """
    Saves the current time and variable data to a JSON file
    
    Args:
        filename (str): Path to the JSON file
        variable_data: Any JSON-serializable data to save
    """
    # if check_recent and not check_if_recent_save(filename):
    #     logger.info(f"{filename} was saved recently!")
    #     return 
        
    # Get current time
    current_time = datetime.datetime.now().isoformat()
    
    # Create a dictionary with time and data
    data_to_save = {
        "timestamp": current_time,
        "data": variable_data
    }
    
    # Write to JSON file
    with open(filename, 'w') as json_file:
        json.dump(data_to_save, json_file, indent=4)
    
    logger.info(f"Data saved to {filename}")

def load_from_json(filename):
    """
        Loads data from a JSON file
        
        Args:
            filename (str): Path to the JSON file
            
        Returns:
            dict: The loaded data or None if file doesn't exist
    """
    try:
        with open(filename, 'r') as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        logger.error(f"File {filename} not found")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {filename}")
        return None
    
def check_if_recent_save(filename, elapse_time=24):
    current_time = datetime.datetime.now()
    
    if os.path.exists(filename):
        save_data = load_from_json(filename)
        if save_data and 'timestamp' in save_data.keys():
            last_save_time = dateutil.parser.parse(save_data['timestamp'])
            return (last_save_time + datetime.timedelta(hours=elapse_time)) > current_time
   
    return False
    
def read_file(filepath):
    if not os.path.exists(filepath):
        return ''
    
    with open(filepath, 'r') as f:
        return f.read()