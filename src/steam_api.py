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
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import time

from helper import check_if_recent_save, save_to_json
from src.game_api import GameAPI, GameAPIError

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class Steam(GameAPI):
    """
    A client for interacting with the Steam API.
    Provides methods to fetch user wishlists and game details.
    """
    
    # API URLs
    STEAM_STORE_API_URL = 'https://store.steampowered.com/api/appdetails'
    STEAM_BASE_URL = 'https://store.steampowered.com/app/'
    STEAM_API_URL = 'https://api.steampowered.com'
    
    # API Endpoints
    WISHLIST_ENDPOINT = "IWishlistService/GetWishlist/v1"
    USER_SUMMARY_ENDPOINT = "ISteamUser/GetPlayerSummaries/v0002/"
    
    # Constants
    STEAM_FILENAME = 'steam_games'
    
    def __init__(self, api_key: str, data_dir: str = 'data'):
        """
        Initialize Steam client with an API key.
        
        Args:
            api_key: The Steam API key for authentication
            data_dir: Directory to store cached data
            
        Raises:
            ValueError: If api_key is empty or None
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty or None")
            
        self.api_key = api_key.strip()
        super().__init__(self.STEAM_STORE_API_URL, data_dir)
        
        # Create session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Steam-API-Client/1.0'
        })
    
    def load_wishlist(self, user_id: str, wishlist_only: bool = False) -> Dict[str, Any]:
        """
        Retrieve a user's wishlist from Steam and download corresponding game data.
        Caches data to avoid repeated API calls.
        
        Args:
            user_id: The Steam ID of the user
            wishlist_only: If True, only return app IDs without full game data
            
        Returns:
            Dictionary containing wishlist data
            
        Raises:
            ValueError: If user_id is invalid
            
        Note:
            Requires a lot of calls to steam server, games are stored locally to relieve server stress
        """
        if not user_id or not str(user_id).strip():
            raise ValueError("User ID cannot be empty or None")
            
        user_id = str(user_id).strip()
        logger.info(f"Getting wishlist for user {user_id}")
        
        # Set cache file name
        super().set_file_name(f"{self.STEAM_FILENAME}-{user_id}.json")
        
        # Check if we have recent cached data
        is_recent_save = check_if_recent_save(self.save_file, self.CACHE_DURATION)
        
        if not is_recent_save:
            logger.info("Fetching fresh wishlist data")
            app_ids = self._fetch_wishlist_app_ids(user_id)
            
            if wishlist_only:
                # Return only app IDs
                data = {'unique': app_ids, 'games': []}
                save_to_json(self.save_file, data)
            else:
                # Download full game data
                super().download_data(self._process_json, {'appids': ''}, app_ids)
        else:
            logger.info("Using cached wishlist data")
            # Verify cached data completeness
            super().download_data(self._process_json, {"appids": 0})
            
        return self._load_cached_data()
    
    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            url: The URL to make request to
            params: Query parameters
            
        Returns:
            JSON response data
        """
        try:
            response = self.session.get(
                url, 
                params=params
            )
            response.raise_for_status()
            return response.json()
                
        except requests.RequestException as e:
            logger.error(f"Request failed {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            
    def _check_valid_wishlist(self, data: Dict[str, Any]) -> List[Dict]: 
        """
        Checks if wishlist response returned value data.
        
        Args:
            data: What was returned from steam api
            
        Returns:
            List of wishlist items, return empty if not found
        """
        if "response" not in data:
            logger.warning("Wishlist: Invalid response returned.")
            return []
            
        response_data = data["response"]
        if "items" not in response_data:
            logger.warning("No items found in wishlist response")
            return []
            
        wishlist_items = response_data["items"]
        if not wishlist_items:
            logger.info("User has empty wishlist")
            return []
        
        return wishlist_items
    
    def _fetch_wishlist_app_ids(self, user_id: str) -> List[int]:
        """
        Fetch wishlist app IDs for a user.
        
        Args:
            user_id: Steam user ID
            
        Returns:
            List of app IDs
        """
        params = {
            'steamid': user_id,
            'key': self.api_key,
        }
        
        wishlist_url = f"{self.STEAM_API_URL}/{self.WISHLIST_ENDPOINT}"
        data = self._make_request(wishlist_url, params)
        
        wishlist_items = self._check_valid_wishlist(data)
        if not wishlist_items:
            return []
            
        app_ids = []
        for item in wishlist_items:
            if isinstance(item, dict) and 'appid' in item:
                try:
                    app_ids.append(int(item['appid']))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid app ID in wishlist item: {item}")
                    
        logger.info(f"Found {len(app_ids)} games in wishlist")
        return app_ids
    
    def _load_cached_data(self) -> Dict[str, Any]:
        """Load data from cache file."""
        try:
            if Path(self.save_file).exists():
                import json
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cached data: {e}")
        
        return {'unique': [], 'games': []}
    
    def get_game_data(self, game_id: Union[int, str]) -> Dict[str, Any]:
        """
        Retrieve detailed information for a specific game.
        
        Args:
            game_id: unquie id assigned to each steam game
            
        Returns:
            Dictionary containing game data
            
        Raises:
            ValueError: If game_id is invalid
        """
        try:
            game_id = int(game_id)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid app ID: {game_id}")
            
        if game_id <= 0:
            raise ValueError(f"App ID must be positive: {game_id}")
        
        params = {'appids': game_id}
        
        try:
            data = self._make_request(self.STEAM_STORE_API_URL, params)
            return self._process_json(data, game_id)
        except Exception as e:
            logger.error(f"Failed to retrieve data for app {game_id}")
            return {}
        
    def _process_json(self, response: Dict[str, Any], game_id: Union[int, str]) -> Dict[str, Any]:
        """
        Process JSON response to check correct response was given, then filter that data and return it.
        
        Args:
            response: JSON response from Steam API
            game_id: unquie id assigned to each steam game
            
        Returns:
            Incorrect response, empty Dict 
            Correct response, filtered game data
        """
        game_id_str = str(game_id)
        
        if game_id_str not in response:
            logger.warning(f"Game {game_id} not found in response")
            return {}
            
        game_data = response[game_id_str]
        
        if not game_data.get('success', False):
            logger.warning(f"API returned failure for game {game_id}")
            return {}
            
        raw_data = game_data.get('data', {})
        if not raw_data:
            logger.warning(f"No data found for game {game_id}")
            return {}
            
        return self._filter_game_data(raw_data)
    
    def _filter_game_data(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and filter relevant game information.
        Only processes games that have pricing information.
        
        Args:
            game: Raw game data from Steam API
            
        Returns:
            Incorrect response, empty Dict 
            Correct response, filtered game data
        """
        # Only process games with price information
        price_overview = game.get("price_overview", {})
        if not price_overview:
            return {}
        
        # Extract basic game information
        filtered_data = {
            "appid": game.get("steam_appid", 0),
            "name": game.get("name", "Unknown"),
            "header": game.get("header_image", ""),
            "is_free": game.get("is_free", False),
            "description": game.get("detailed_description", ""),
            "developers": game.get("developers", []),
            "publishers": game.get("publishers", []),
            "categories": [cat.get("description", "") for cat in game.get("categories", [])],
            "genres": [genre.get("description", "") for genre in game.get("genres", [])],
            "discount": price_overview.get("discount_percent", 0)
        }
        
        # Convert price to USD if possible
        price = price_overview.get("final_formatted", "")
        currency = price_overview.get("currency", "")
        filtered_data = self._change_price_to_dollar(price, currency, filtered_data)
        
        # Add optional metadata
        metacritic = game.get("metacritic", {})
        if metacritic and "score" in metacritic:
            filtered_data["metacritic"] = metacritic["score"]
            
        recommendations = game.get("recommendations", {})
        if recommendations and "total" in recommendations:
            filtered_data["recommendations"] = recommendations["total"]
        
        return filtered_data
    
    def check_user_status(self, steam_id: str) -> bool:
        """
        Check if a Steam user exists and is valid.
        
        Args:
            steam_id: Steam user ID
            
        Returns:
            True if user exists, False otherwise
            
        Raises:
            ValueError: If steam_id is invalid
        """
        if not steam_id or not str(steam_id).strip():
            raise ValueError("Steam ID cannot be empty or None")
            
        steam_id = str(steam_id).strip()
        
        params = {
            "key": self.api_key,
            "steamids": steam_id,
        }
        
        url = f"{self.STEAM_API_URL}/{self.USER_SUMMARY_ENDPOINT}"
        
        try:
            data = self._make_request(url, params)
            
            if "response" not in data:
                logger.warning("Invalid user status response format")
                return False
                
            players = data["response"].get("players", [])
            user_exist = len(players) > 0
            
            logger.info(f"Steam User {steam_id} exists: {user_exist}")
            return user_exist
            
        except Exception as e:
            logger.error(f"Failed to check user status for {steam_id}")
            return False
    
    def get_base_url(self) -> str:
        """
        Get the base URL for Steam store pages.
        
        Returns:
            Steam store base URL
        """
        return self.STEAM_BASE_URL