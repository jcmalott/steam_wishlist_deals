from typing import Dict, Any, List
import logging
import requests
from tqdm import tqdm
import time

import json

from helper import check_if_recent_save, save_to_json
from src.game_api import GameAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class AnyDealAPI(GameAPI):
    """
        A client for interacting with the Is There Any Deals API.
        Provides methods to fetch game product details.
        
        API: https://docs.isthereanydeal.com/
    """
    ANY_DEAL_BASE_URL = 'https://api.isthereanydeal.com'
    
    def __init__(self, api_key:str, name:str='games', data_dir:str = 'data'):
        """
            Initialize connection with GG Deals client with an API key.
            
            Args:
                api_key (str): The GG Deals API key for authentication
                data_dir (str): Directory to store cached data
        """
        self.api_key = api_key
        self.filename = f"any_deals_{name}"
        self.steam_shop_id = 61
        super().__init__(self.ANY_DEAL_BASE_URL, data_dir)
        
    def find_products_by_appids(self, appids:List[int], user_id:str):
        """
            Retrieve details for multiple game products in bulk.
            
            Args:
                products (list): List of product dictionaries containing game names to search for
        """    
        logger.info("Retrieving mulitple game product details")
        super().set_file_name(self.filename + "-" + user_id + ".json")
        
        is_recent_save = check_if_recent_save(self.save_file, self.CACHE_DURATION)
        if not is_recent_save:
            # Download fresh data for each game appid
            result_ids = self._download_real_ids(appids)
            real_ids = [value for value in result_ids.values()]
            self._download_real_prices(appids, real_ids)
        
    def _download_real_ids(self, appids:List[int]):
        url_real_ids = f"{self.ANY_DEAL_BASE_URL}/lookup/id/shop/{self.steam_shop_id}/v1"
        data = [f"app/{appid}" for appid in appids]
        result = {}
        try:
            response = requests.post(url_real_ids, json=data)
            response.raise_for_status()
            
            result = response.json()
        except Exception as e:
            print(f"Error {e}")
            
        return result    
    
    def _download_real_prices(self, appids:List[int], real_ids:List[str]):
        url_real_prices = f"{self.ANY_DEAL_BASE_URL}/games/prices/v3"
        params = {
            "key": self.api_key,
            "shops": self.steam_shop_id
        }
        
        result_prices = {}
        iterations = len(real_ids)
        # display progress bar for overall download
        with tqdm(total=iterations, desc="Downloading Any Deals Data", unit='game') as pbar:  
            # download the games in batches to not overload the server  
            data = []
            for i in range(0, iterations, self.BATCH_SIZE):
                batch = real_ids[i:i+self.BATCH_SIZE]
                batch_appids = appids[i:i+self.BATCH_SIZE]
                
                try:
                    response = requests.post(url_real_prices, json=batch, params=params)
                    response.raise_for_status()
                    result_prices = response.json()  
                    
                    # ids don't come back in the same order they were sent
                    result_ids = [item['id'] for item in result_prices]
                    ids = []
                    for id in result_ids:
                        index = batch.index(id)
                        ids.append(batch_appids[index])
                                 
                    steam_prices = self._process_price_data(ids, result_prices)
                    data += steam_prices
                except Exception as e:
                    print(f"Error {e}")
                    
                time.sleep(self.SLEEP_TIME)
                pbar.update(iterations/self.BATCH_SIZE)
                # update and save data incase of disconnect
                save_to_json(self.save_file, data)
                
                # Pause between batches to avoid overwhelming the server
                if i + self.BATCH_SIZE < iterations:
                    time.sleep(self.BATCH_PAUSE)
    
    def _process_price_data(self, appids, prices):
        steam_prices = []
        for index, price in enumerate(prices):
            steam_prices.append(self.extract_price_data(price, appids[index])) 
            
        return steam_prices
    
    def extract_price_data(self, price, appid):
        first_deal = price['deals'][0]
        
        # Base structure
        steam_price = {
            'id': price["id"],
            'appid': appid
        }
        
        # Price fields to process
        price_fields = [
            ('current_price', 'price'),
            ('regular_price', 'regular'), 
            ('lowest_price', 'storeLow')
        ]
        
        # Process each price field
        for field_name, deal_key in price_fields:
            price_data = first_deal.get(deal_key)
            if price_data:
                steam_price[field_name] = {
                    "price_current": self.change_price_to_dollar(price_data['amount'], price_data['currency']),
                    "currency": "USD"
                }
            else:
                steam_price[field_name] = {"price_current": 0, "currency": "USD"}
        
        return steam_price