# Kinguin API Client
# This module provides functionality to interact with Kinguin Web API
# References:
# - https://www.kinguin.net/
# - https://github.com/kinguinltdhk/Kinguin-eCommerce-API/blob/master/api/products/v1/README.md#search-products
# - https://www.kinguin.net/integration/dashboard/
from typing import Dict, Any, List
import logging

from helper import check_if_recent_save
from src.game_api import GameAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class KinguinProducts(GameAPI):
    """
        A client for interacting with the Kinguin API.
        Provides methods to fetch game product details.
    """
    KINGUIN_BASE_URL="https://gateway.kinguin.net/esa/api/v1/products" # Kinguin Store API
    KINGUIN_FILENAME = 'kinguin_games'
    
    def __init__(self, api_key: str, data_dir: str = 'data'):
        """
            Initialize connection with Kinguin client with an API key.
            
            Args:
                api_key (str): The Kinguin API key for authentication
                data_dir (str): Directory to store cached data
        """
        
        self.headers={
            "Accept": "application/json",
            "X-Api-Key": api_key
        }
        self.api_key = api_key
        super().__init__(self.KINGUIN_BASE_URL, data_dir)
        
    def find_products_by_name(self, products, user_id):    
        """
            Retrieve details for multiple game products in bulk.
            
            Args:
                products (list): List of product dictionaries containing game names to search for
        """    
        logger.info("Retrieving mulitple game product details")
        super().set_file_name(self.KINGUIN_FILENAME + "-" + user_id + ".json")
        params = {
            'name': '',
            'platform': 'Steam',
            'sortBy': 'price'
        }
        is_recent_save = check_if_recent_save(self.save_file, self.CACHE_DURATION)
        if not is_recent_save:
            # If cache is outdated, extract unique game names from products list
            uniques = [product["name"] for product in products]
            # uniques = products['unique']
            # Download fresh data for each unique game name
            super().download_data(self._process_json, params, uniques, headers=self.headers)
        else:
            # files have a record of which games should be downloaded
            # this is checking to make sure all games are downloaded
            super().download_data(self._process_json, params, headers=self.headers)
        
        
    # def find_product_by_name(self, game_name):
    #     # sortBy -> price
    #     params = {
    #         'name': game_name,
    #         'platform': 'Steam',
    #         'sortBy': 'relevancy'
    #     }
        
    #     try:
    #         response = requests_with_retries(self.session, self.KINGUIN_BASE_URL, params=params, headers=self.headers)
    #         response.raise_for_status()
    #         return self._process_json(response.json(), game_name)
                
    #     except requests.RequestException as e:
    #         logger.error(f"Failed to retrieve details for game {game_name}: {str(e)}")
    #         raise GameAPIError(f"Failed to retrieve game data: {str(e)}", response.status_code)
        
    def _find_steam_key(self, products, game_name: str, regionId: int = 2, dlc = False) -> Dict:
        """
            Find a Steam key product from a list of products that matches criteria.
            
            Args:
                products (list): List of product dictionaries from Kinguin API
                game_name (str): name of game on steam
                regionId (int): Region ID to filter by (default: 2 for United States)
                dlc (bool): Whether to include DLC products (default: False)
                
            Returns:
                dict: Filtered product data or empty dict if no match found
        """
        
        for item in products:
            keys = item.keys()
            # check that the game can be bought inside the US, REGION FREE = Global
            has_limitations = (item['regionalLimitations'] == "REGION FREE") if 'regionalLimitations' in keys else False
            # 2 = United States
            has_correct_id = (item['regionId'] == regionId) if 'regionId' in keys else False
            
            # keys words to filter product title by
            name = item.get("name", '').lower()
            has_key = 'key' in name
            has_dlc = 'dlc'in name if dlc else 'dlc'not in name
            has_filtered_words = 'season pass' in name
            has_correct_name = has_key and has_dlc and not has_filtered_words
            
            # just return the first listing that matched our requirements
            if has_correct_name and (has_limitations or has_correct_id):
                # steam name is primary key and needs to be stored first
                data = {
                    "name": game_name,
                    "appid": item['kinguinId'],
                    "display_name": item['name'],
                    "platform": item.get('platform', 'NA')
                }
                
                # Convert price to dollar if needed
                data = self._change_price_to_dollar(item['price'], 'EUR', data)
                return data
        
        # return empty dict if nothing matched
        return {"name": ''}
    
    def _process_json(self, response, game_name):
        """ 
            What to do with the game data returned by kinguin.
        """
        if 'results' in response and response['results']:
            results = response['results']  
            filtered_results = self._find_steam_key(results, game_name)
            filtered_results["name"] = game_name
            return filtered_results
        
        else:
            logger.warning(f"No valid data found for game {game_name}")
            return {"name": game_name}