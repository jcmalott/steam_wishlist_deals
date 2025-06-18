from typing import Dict, Optional, Any, List
import logging
import os
from pathlib import Path
import requests
from tqdm import tqdm
import time
import re

from helper import save_to_json, check_if_recent_save, load_from_json
from src.exchange_rates import ExchangeRates
from src.custom_errors import GameAPIError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
        
class GameAPI():
    BATCH_SIZE = 20 # items, How many resquests to make in one iteration
    SLEEP_TIME = 1 # Seconds, Pause between each item in batch
    BATCH_PAUSE = 2 # Seconds, Pause between each batch
    CACHE_DURATION = 72 # Hours, How long to wait before refreshing all downloaded data
    # There is a 200 request limit every 5 mins. (5*60)/200 = 1.5
    SLEEP_TIME = 1.5 # Seconds, time between calling each game
    
    def __init__(self, base_api_url: str, data_dir: str = ''):
        self.base_url_api = base_api_url
        self.session = requests.Session() # increase performance
        self.rates = ExchangeRates() # changing other currencies to dollars
        
        self.data_dir = data_dir # folder to store local data
        Path(self.data_dir).mkdir(exist_ok=True) # Make dir if doesn't exist
            
    def download_data(self, func_process, params, uniques: List[Any] = {}):
        """ 
            Data will be stored after each batch incase server disconnects.
            
            Args:
                func_process: Function that processes any data returned from base_url_api
                uniques: appids
                params: What to send when calling base_url_api to retrieve correct game data
            Note:
                params {
                    "first_key": <- what is being searched for
                }
        """
        if uniques: # each unique will be a primary key within games
            data = {'unique': uniques, 'games': []}
        else: # only download data that hasn't been store yet
            logger.info(f"Loading Stored Data: {self.save_file}")
            stored_data = load_from_json(self.save_file)['data']
            data = {'unique': stored_data['unique'], 'games': stored_data['games']}
        
        stored_games = data['games']
        store_uniques = data['unique']
        items_to_retrieve = self._items_left_to_download(stored_games, store_uniques)
        
        if not items_to_retrieve:
            logger.info("All game data already retrieved, nothing to fetch")
            return
        
        iterations = len(items_to_retrieve)
        # display progress bar for overall download
        with tqdm(total=iterations, desc="Downloading Game Data", unit='game') as pbar:  
            # download the games in batches to not overload the server  
            for i in range(0, iterations, self.BATCH_SIZE):
                batch = items_to_retrieve[i:i+self.BATCH_SIZE]
                
                for id in batch:
                    # item that is being searched
                    primary_key = next(iter(params))
                    params[primary_key] = id
                    
                    try:
                        # return any items found from search
                        response = self.session.get(self.base_url_api, params=params)
                        response.raise_for_status()
                        
                        # function to process any data that was recieved
                        # if Null don't store
                        processed_json = func_process(response.json(), id)
                        if processed_json:
                            stored_games.append(processed_json)
                        else:
                            # remove matching id keeping track of what items have been downloaded
                            store_uniques.remove(id)
                    except requests.RequestException as e:
                        logger.error(f"Failed to retrieve details for game {id}: {str(e)}")
                        if response.status_code == 429:
                            break
                        raise GameAPIError(f"Failed to retrieve game data: {str(e)}", response.status_code)
                    time.sleep(self.SLEEP_TIME)
                    pbar.update(1)
                # update and save data incase of disconnect
                data['unique'] = store_uniques
                data['games'] = stored_games
                save_to_json(self.save_file, data)
                
                # Pause between batches to avoid overwhelming the server
                if i + self.BATCH_SIZE < iterations:
                    time.sleep(self.BATCH_PAUSE)
                    
    def set_file_name(self, filename):
        self.save_file = os.path.join(self.data_dir, filename)
                    
    def get_data(self):
        """ 
            Retrieves any data that was stored using the download_data() function.
            
            Returns locally stored data and nothing if stored data wasn't found.
        """
        local_data = load_from_json(self.save_file)
        if not local_data:
            local_data = {}
        return local_data['data']
    
    def _change_price_to_dollar(self, og_price, currency, data):
        price = og_price
        if isinstance(price, str):
            number = re.search(r'(\d+\.\d+|\d+)', price)
            price = float(number.group(1)) if number else og_price
        
        if currency != '' and currency != 'USD':
            price = self.rates.get_price_dollar(price, currency)
            currency = "USD"
            
        data["currency"] = currency
        data["price"] = price
        
        return data
    
    def change_price_to_dollar(self, og_price, currency):
        if currency == '':
            return og_price
        
        return self.rates.get_price_dollar(og_price, currency)
    
    def _items_left_to_download(self, stored_games, stored_uniques):
        """ 
            Comparing uniques with game primary keys
            Whatever game key hasn't match to a unique hasn't been loaded yet
        """
        game_uniques = []
        primary_key = 0
        if stored_games:
            primary_key = next(iter(stored_games[0]))
            game_uniques = [item[primary_key] for item in stored_games]
        # games that haven't been loaded
        return [item for item in stored_uniques if item not in game_uniques]
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
    
    def close(self):
        """Close the session and cleanup resources."""
        if hasattr(self, 'session'):
            self.session.close()