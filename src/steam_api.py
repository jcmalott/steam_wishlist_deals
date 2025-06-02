# Steam API Client
# This module provides functionality to interact with Steam's Web API
# References:
# - https://developer.valvesoftware.com/wiki/Steam_Web_API
# - https://steamwebapi.azurewebsites.net/
# - https://steamcommunity.com/dev
# - https://steamcommunity.com/dev/apikey
# - https://store.steampowered.com/api/appdetails?appids=34010
import requests
import logging
from typing import Dict, Any

from helper import check_if_recent_save, save_to_json
from src.game_api import GameAPI, GameAPIError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class Steam(GameAPI):
    """
        A client for interacting with the Steam API.
        Provides methods to fetch user wishlists and game details.
    """
    STEAM_API_URL = 'https://store.steampowered.com/api/appdetails' # Store API (Game Details)
    STEAM_BASE_URL = 'https://store.steampowered.com/app/'
    STEAM_SUPPORT_API_URL='https://api.steampowered.com' # Service API (wishlist)
    WISHLIST_ENDPOINT = "IWishlistService/GetWishlist/v1" # Wishlist game Ids
    STEAM_FILENAME = 'steam_games'
    
    def __init__(self, api_key:str, data_dir:str = 'data'):
        """
            Initialize connection with Steam client with an API key.
            
            Args:
                api_key (str): The Steam API key for authentication
                data_dir (str): Directory to store cached data
        """
        self.api_key = api_key
        super().__init__(self.STEAM_API_URL, data_dir)
        
    def load_wishlist(self, user_id: str, wishlist_only:bool=False):
        """
            Retrieve a user's wishlist from Steam and downloads all corresponding games.
            Caches data to avoid repeating API calls.
            
            Args:
                user_id (str): The Steam ID of the user to get wishlist from
                
            Returns: -> JSON response containing the user's wishlist game data.  
            Raises: -> SteamAPIError: If the API request fails or returns an error
        """
        logger.info(f"Getting wishlist for user {user_id}")
        # where data will be stored
        super().set_file_name(self.STEAM_FILENAME + "-" + user_id + ".json")
        # getting steam games requires a lot of calls to steam server so instead these games are stored locally
        # and only called after a certain time period (self.CACHE_DURATION).
        is_recent_save = check_if_recent_save(self.save_file, self.CACHE_DURATION)
        if not is_recent_save:
            logger.info("Fetching fresh wishlist app ids")
            params = {
                'steamid': user_id,
                'key': self.api_key,
            }
            
            try:
                wishlist_endpoint = f"{self.STEAM_SUPPORT_API_URL}/{self.WISHLIST_ENDPOINT}"
                # get all game ids from users wishlist
                response = requests.get(wishlist_endpoint, params=params)
                response.raise_for_status()
                data = response.json()
                
                if "response" in data and "items" in data["response"]:
                    wishlist_items = data["response"]["items"]
                    app_ids = [item['appid'] for item in wishlist_items] if wishlist_items else []
                
                    if wishlist_only:
                        # only return game appids
                        data = {'unique': app_ids, 'games': []}
                        save_to_json(self.save_file, data)
                    else:
                        # retrieve all game information
                        super().download_data(self._process_json, {'appids': ''}, app_ids)
            except requests.RequestException as e:
                logger.error(f"Failed to retrieve wishlist for user {user_id}: {str(e)}")
                raise GameAPIError(f"Failed to retrieve wishlist: {str(e)}", response.status_code)
        else:
            # doesn't call server for new data, but checks that all previous data was downloaded
            super().download_data(self._process_json, { "appids": 0})
            
    def get_game_data(self, appid:int):
        params = {
            'appids': appid,
        }
        
        game_data = {}    
        try:
            response = requests.get(self.STEAM_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            appid_key = str(appid)
            # check that correct response was received
            if appid_key in data and data[appid_key]['success']:
                game_data = self._filter_game_data(data[appid_key]['data'])
            else:
                logger.warning(f"Failed to retrieve data for {appid}")
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve data for {appid}: {str(e)}")
            raise GameAPIError(f"Failed to retrieve wishlist: {str(e)}", response.status_code)
        
        return game_data
     
    def check_user_status(self, steam_id: str) -> bool:  
        url = self.STEAM_SUPPORT_API_URL + "/ISteamUser/GetPlayerSummaries/v0002/"
        params = {
            "key": self.api_key,
            "steamids": steam_id,
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()['response']
            
            is_current_user = len(data['players']) > 0
            logger.info(f"Steam User {steam_id}, Current Status: {is_current_user}")    
            return is_current_user
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve user status for {steam_id}: {str(e)}")
            raise GameAPIError(f"Failed to retrieve user status: {str(e)}", response.status_code)
        
    def get_base_url(self):
        """ 
            Steam store API
        """
        return self.STEAM_BASE_URL
    
    def _process_json(self, response, game_id):
        """ 
            What to do with the game data returned by steam.
        """
        id = str(game_id)
        if id in response and response[id]['success']:
            data = response[id]['data']
            return self._filter_game_data(data)
        
        else:
            logger.warning(f"No valid data found for game {game_id}")
            return {}
        
    def _filter_game_data(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """
            Extract relevant game information if game has a set price.
            
            Args:
                game (Dict[str, Any]): Raw game details from API
                
            Returns:
                Dict[str, Any]: Filtered game data
        """
        filtered_data = {}
        
        # only get data for a game that has a price
        price_overview = game.get("price_overview", {})
        if price_overview:
            filtered_data = {
                "appid": game.get("steam_appid", 0),
                "name": game.get("name",'NA'),
                "header": game.get("header_image", 'NA'),
                "is_free": game.get("is_free", 'NA'),
                "description": game.get("detailed_description", 'NA'),
                "developers": game.get("developers", []),
                "publishers": game.get("publishers", []),
                "categories": game.get("categories", []),
                "genres": game.get("genres", [])     
            }
            
            filtered_data["discount"] = price_overview.get("discount_percent", "NA")
            price = price_overview.get("final_formatted", "NA")
            currency = price_overview.get("currency", '')
            filtered_data = self._change_price_to_dollar(price, currency, filtered_data)
        
            metacritic = game.get("metacritic", {})
            if metacritic:
                filtered_data["metacritic"] = metacritic.get("score", "NA")
                
            recommendations = game.get("recommendations", {})
            if recommendations:
                filtered_data["recommendations"] = recommendations.get("total", "NA")
        
        return filtered_data
        