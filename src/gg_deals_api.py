# GG Deals API Client
# This module provides functionality to interact with GG Deals Web API
# References:
# - https://gg.deals/api/prices/
from typing import Dict, Any, List
import logging

from helper import check_if_recent_save
from src.game_api import GameAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class GGDealsAPI(GameAPI):
    """
        A client for interacting with the GG Deals API.
        Provides methods to fetch game product details.
    """
    GG_DEALS_BASE_URL = 'http://api.gg.deals/v1/prices/by-steam-app-id/'
    GG_DEALS_FILENAME = 'gg_deals_games'
    
    def __init__(self, api_key:str, data_dir:str = 'data'):
        """
            Initialize connection with GG Deals client with an API key.
            
            Args:
                api_key (str): The GG Deals API key for authentication
                data_dir (str): Directory to store cached data
        """
        self.api_key = api_key
        super().__init__(self.GG_DEALS_BASE_URL, data_dir)
        
    def find_products_by_appid(self, appids, user_id):    
        """
            Retrieve details for multiple game products in bulk.
            
            Args:
                products (list): List of product dictionaries containing game names to search for
        """    
        logger.info("Retrieving mulitple game product details")
        super().set_file_name(self.GG_DEALS_FILENAME + "-" + user_id + ".json")
        params = {
            'ids': 0,
            'key': self.api_key
        }
        is_recent_save = check_if_recent_save(self.save_file, self.CACHE_DURATION)
        if not is_recent_save:
            # Download fresh data for each game appid
            super().download_data(self._process_json, params, appids)
        else:
            # check that all stored appids have been download correctly
            super().download_data(self._process_json, params)
            
    def get_base_url(self):
        return self.GG_DEALS_BASE_URL
    
    def _process_json(self, response, game_id):
        """ 
            What to do with the game data returned by steam.
        """
        id = str(game_id)
        if response['success'] and response['data'].get(id, None):
            data = response['data'][id]
            return self._filter_game_data(data, id)
        
        else:
            logger.warning(f"No valid data found for game {game_id}")
            return {}
        
    def _filter_game_data(self, game: Dict[str, Any], id:str) -> Dict[str, Any]:
        """
            Extract relevant information from the game details if game has a set price.
            
            Args:
                game (Dict[str, Any]): Raw game details from API
                id: appid of game
                
            Returns:
                Dict[str, Any]: Filtered game data
        """
        
        filtered_data = {}
        prices = game.get("prices", {})
        # check price has a value
        if "historicalRetail" in prices and prices["historicalRetail"]:
            price = prices.get("currentRetail", 0)
            if price:
                filtered_data = {
                    "appid": int(id),
                    "name": game.get("title",'NA'),
                    "url": game.get("url", 'NA')   
                }
                filtered_data["price"] = float(price) 
                filtered_data["price_lowest"] = float(prices.get("historicalRetail", 0.00) )
                filtered_data["currency"] = prices.get("currency", "USD") 
        
        return filtered_data