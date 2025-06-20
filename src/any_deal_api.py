from typing import Dict, Any, List, Optional, Union
import logging
import requests
from tqdm import tqdm
import time
from dataclasses import dataclass
from pathlib import Path

from helper import check_if_recent_save, save_to_json, load_from_json
from src.game_api import GameAPI, GameAPIError
from src.deals_config import DealsConfig
from src.price_data import PriceData
from src.game_price_info import GamePriceInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class AnyDealAPI(GameAPI):
    """
    A client for interacting with the IsThereAnyDeal API.
    Provides methods to fetch game pricing and deal information.
    
    API Documentation: https://docs.isthereanydeal.com/
    """
    
    # API Configuration
    ANY_DEAL_BASE_URL = 'https://api.isthereanydeal.com'
    
    # API Endpoints
    LOOKUP_ENDPOINT = 'lookup/id/shop/{shop_id}/v1'
    PRICES_ENDPOINT = 'games/prices/v3'
    GAME_INFO_ENDPOINT = 'games/info/v2'
    
    # Shop IDs (Steam is 61)
    STEAM_SHOP_ID = 61
    
    # Default filename prefix
    DEFAULT_FILENAME_PREFIX = 'any_deals'
    
    def __init__(
        self, 
        api_key: str, 
        name: str = 'games', 
        data_dir: str = 'data',
        config: Optional[DealsConfig] = None
    ):
        """
        Initialize AnyDeal API client.
        
        Args:
            api_key: The IsThereAnyDeal API key for authentication
            name: Name identifier for cache files
            data_dir: Directory to store cached data
            config: API configuration settings
            
        Raises:
            ValueError: If api_key is empty or None
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty or None")
            
        self.api_key = api_key.strip()
        self.name = name.strip() if name else 'games'
        self.filename = f"any_deals_{self.name}"
        self.steam_shop_id = self.STEAM_SHOP_ID
        
        super().__init__(self.ANY_DEAL_BASE_URL, data_dir)
        
        # Update session headers for AnyDeal API
        self.session.headers.update({
            'User-Agent': 'AnyDeal-API-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def find_products_by_appids(
        self, 
        appids: List[Union[int, str]], 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve pricing details for multiple Steam games by App IDs.
        
        Args:
            appids: List of Steam App IDs to lookup
            user_id: User identifier for cache file naming
            
        Returns:
            List of game pricing information dictionaries
            
        Raises:
            ValueError: If appids is empty or user_id is invalid
        """
        if not appids:
            raise ValueError("App IDs list cannot be empty")
            
        if not user_id or not str(user_id).strip():
            raise ValueError("User ID cannot be empty")
        
        user_id = str(user_id).strip()
        
        logger.info(f"Retrieving price details for {len(appids)} games")
        
        # Set cache filename
        super().set_file_name(f"{self.filename}-{user_id}.json")
        
        # Check if we need fresh data
        is_cache_fresh = check_if_recent_save(self.save_file, self.config.cache_duration)
        
        if not is_cache_fresh:
            logger.info("Downloading fresh pricing data")
            return self._download_fresh_data(appids)
        else:
            logger.info("Using cached pricing data")
            return self._load_cached_pricing_data()
    
    def _download_fresh_data(self, appids: List[int]) -> List[Dict[str, Any]]:
        """
        Download fresh pricing data for given app IDs.
        
        Args:
            appids: List of Steam App IDs
            
        Returns:
            List of pricing data dictionaries
        """
        try:
            # Step 1: Get internal IDs from Steam App IDs
            logger.info("Looking up internal game IDs")
            id_mapping = self._lookup_internal_ids(appids)
            
            if not id_mapping:
                logger.warning("No valid internal IDs found")
                return []
            
            # Step 2: Get pricing data using internal IDs
            logger.info("Downloading pricing information")
            pricing_data = self._download_pricing_data(id_mapping)
            
            # Step 3: Save to cache
            self._save_pricing_data(pricing_data)
            
            return pricing_data
            
        except Exception as e:
            logger.error(f"Failed to download pricing data: {e}")
    
    def _lookup_internal_ids(self, appids: List[int]) -> Dict[str, int]:
        """
        Lookup internal game IDs from Steam App IDs.
        
        Args:
            appids: List of Steam App IDs
            
        Returns:
            Dictionary mapping internal IDs to Steam App IDs
        """
        url = f"{self.ANY_DEAL_BASE_URL}/{self.LOOKUP_ENDPOINT.format(shop_id=self.steam_shop_id)}"
        
        # Format app IDs for API request
        lookup_data = [f"app/{appid}" for appid in appids]
        
        try:
            result = self._post_request(url, lookup_data)
            
            # Create mapping from internal ID to Steam App ID
            id_mapping = {}
            for steam_app_key, internal_id in result.items():
                if internal_id:  # Only include successful lookups
                    try:
                        # Extract app ID from "app/12345" format
                        steam_appid = int(steam_app_key.replace('app/', ''))
                        id_mapping[steam_appid] = internal_id
                    except ValueError:
                        logger.warning(f"Invalid app key format: {steam_app_key}")
            
            logger.info(f"Successfully mapped {len(id_mapping)} out of {len(appids)} app IDs")
            return id_mapping
            
        except requests.RequestException as e:
            logger.error(f"ID lookup request failed: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON response in ID lookup: {e}")
    
    def _download_pricing_data(self, id_mapping: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Download pricing data for games using their internal IDs.
        
        Args:
            id_mapping: Dictionary mapping internal IDs to Steam App IDs
            
        Returns:
            List of processed pricing data
        """
        url = f"{self.ANY_DEAL_BASE_URL}/{self.PRICES_ENDPOINT}"
        params = {
            "key": self.api_key,
            "shops": self.steam_shop_id
        }
        
        internal_ids = list(id_mapping.keys())
        all_pricing_data = []
        
        # Process in batches
        iterations = len(internal_ids)
        with tqdm(total=iterations, desc="Downloading Pricing Data", unit='game') as pbar:
            for i in range(0, iterations, self.config.batch_size):
                batch_appids = internal_ids[i:i + self.config.batch_size]
                batch_deal_ids = [id_mapping[internal_id] for internal_id in batch_appids]
                
                try:
                    batch_data = self._download_pricing_batch(
                        url, params, batch_deal_ids, batch_appids
                    )
                    all_pricing_data.extend(batch_data)
                    
                except Exception as e:
                    logger.error(f"Batch download failed: {e}")
                    # Continue with other batches
                
                pbar.update(len(batch_deal_ids))
                
                # Rate limiting
                time.sleep(self.config.sleep_time)
                
                # Pause between batches
                if i + self.config.batch_size < len(internal_ids):
                    time.sleep(self.config.batch_pause)
        
        logger.info(f"Downloaded pricing data for {len(all_pricing_data)} games")
        return all_pricing_data
    
    def _download_pricing_batch(
        self, 
        url: str, 
        params: Dict[str, Any], 
        batch_deal_ids: List[str], 
        batch_appids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Download pricing data for a single batch.
        
        Args:
            url: API endpoint URL
            params: Request parameters
            batch_ids: Internal IDs for this batch
            batch_appids: Corresponding Steam App IDs
            
        Returns:
            Processed pricing data for the batch
        """
        try:
            response = self.session.post(
                url, 
                json=batch_deal_ids, 
                params=params
            )
            response.raise_for_status()
            
            pricing_response = response.json()
            
            # Process the response and match with app IDs
            return self._process_pricing_response(pricing_response, batch_deal_ids, batch_appids)
            
        except requests.RequestException as e:
            logger.error(f"Pricing batch request failed: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON in pricing response: {e}")
    
    def _process_pricing_response(
        self, 
        pricing_response: List[Dict[str, Any]], 
        batch_real_ids: List[str], 
        batch_appids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Process pricing API response and match with Steam App IDs.
        
        Args:
            pricing_response: Raw pricing data from API
            batch_ids: Internal IDs sent in request
            batch_appids: Corresponding Steam App IDs
            
        Returns:
            Processed pricing data with Steam App IDs
        """
        processed_data = []
        
        for price_data in pricing_response:
            internal_id = price_data.get('id')
            if not internal_id:
                continue
                
            try:
                # Find corresponding Steam App ID
                batch_index = batch_real_ids.index(internal_id)
                steam_appid = batch_appids[batch_index]
                
                # Process the pricing data
                game_price = self._extract_price_data(price_data, steam_appid)
                if game_price:
                    processed_data.append(game_price.to_dict())
                    
            except (ValueError, IndexError):
                logger.warning(f"Could not match internal ID {internal_id} to Steam App ID")
        
        return processed_data
    
    def _extract_price_data(self, price_data: Dict[str, Any], appid: int) -> Optional[GamePriceInfo]:
        """
        Extract and process price information from API response.
        
        Args:
            price_data: Raw price data from API
            appid: Steam App ID
            
        Returns:
            GamePriceInfo object or None if no valid data
        """
        if not price_data.get('deals'):
            logger.warning(f"No deals found for app {appid}")
            return None
        
        first_deal = price_data['deals'][0]
        internal_id = price_data.get('id', '')
        
        game_price = GamePriceInfo(id=internal_id, appid=appid)
        
        # Extract different price types
        price_mappings = [
            ('price', 'current_price'),
            ('regular', 'regular_price'),
            ('storeLow', 'lowest_price')
        ]
        
        for deal_key, price_attr in price_mappings:
            price_info = first_deal.get(deal_key)
            if price_info and isinstance(price_info, dict):
                amount = price_info.get('amount', 0)
                currency = price_info.get('currency', 'USD')
                
                # Convert to USD
                usd_amount = self._change_price_to_dollar(amount, currency)
                
                price_obj = PriceData(
                    amount=usd_amount,
                    currency='USD',
                    formatted=f"${usd_amount:.2f}"
                )
                setattr(game_price, price_attr, price_obj)
        
        # Calculate discount percentage
        if game_price.current_price and game_price.regular_price:
            if game_price.regular_price.amount > 0:
                discount = (
                    (game_price.regular_price.amount - game_price.current_price.amount) 
                    / game_price.regular_price.amount * 100
                )
                game_price.discount_percent = max(0, round(discount, 2))
        
        return game_price
    
    def _save_pricing_data(self, pricing_data: List[Dict[str, Any]]):
        """Save pricing data to cache file."""
        try:
            save_to_json(self.save_file, pricing_data)
            logger.info(f"Saved {len(pricing_data)} price records to cache")
        except Exception as e:
            logger.error(f"Failed to save pricing data: {e}")
    
    def _load_cached_pricing_data(self) -> List[Dict[str, Any]]:
        """Load pricing data from cache file."""
        try:
            if not Path(self.save_file).exists():
                logger.warning("No cache file found")
                return []
                
            cached_data = load_from_json(self.save_file)
            if cached_data and 'data' in cached_data:
                data = cached_data['data']
                logger.info(f"Loaded {len(data)} price records from cache")
                return data
            else:
                logger.warning("Invalid cache file format")
                return []
                
        except Exception as e:
            logger.warning(f"Failed to load cached data: {e}")
            return []
    
    def get_game_pricing(self, appid: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get pricing information for a single game.
        
        Args:
            appid: Steam App ID
            
        Returns:
            Pricing information dictionary or None if not found
        """
        try:
            appid_int = int(appid)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid App ID: {appid}")
        
        # Try to find in cached data first
        cached_data = self._load_cached_pricing_data()
        for game_data in cached_data:
            if game_data.get('appid') == appid_int:
                return game_data
        
        # If not found in cache, download fresh data for this game
        logger.info(f"Downloading fresh data for app {appid_int}")
        fresh_data = self._download_fresh_data([appid_int])
        
        return fresh_data[0] if fresh_data else None
    
    def clear_cache(self):
        """Clear cached pricing data."""
        super().clear_cache()
        logger.info("Cleared AnyDeal pricing cache")
    
    def get_base_url(self) -> str:
        """
        Get the base URL for the IsThereAnyDeal API.
        
        Returns:
            Base API URL
        """
        return self.ANY_DEAL_BASE_URL