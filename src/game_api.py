from typing import Dict, Optional, Any, List, Callable, Union
import logging
import requests
from tqdm import tqdm
import time
import re
from abc import ABC, abstractmethod
import os

from helper import save_to_json, check_if_recent_save, load_from_json
from src.exchange_rates import ExchangeRates
from src.custom_errors import GameAPIError
from src.deals_config import DealsConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class GameAPI(ABC):
    """
    Abstract base class for game API clients.
    Provides common functionality for downloading and caching game data.
    """
    
    def __init__(self, base_api_url: str, data_dir: str, config: Optional[DealsConfig] = None):
        """
        Initialize the GameAPI client.
        
        Args:
            base_api_url: Base URL for the API
            data_dir: Directory to store cached data
            config: API configuration settings
            
        Raises:
            ValueError: If base_api_url is empty or invalid
        """
        if not base_api_url or not base_api_url.strip():
            raise ValueError("Base API URL cannot be empty")
            
        self.base_url_api = base_api_url.strip()
        self.config = config or DealsConfig()
        self.save_dir = data_dir or self.config.data_dir
        self.save_file: Optional[str] = None
        
        # Initialize session with better defaults
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GameAPI-Client/1.0',
            'Accept': 'application/json'
        })
        
        # Initialize exchange rates for currency conversion
        self.rates = None
        try:
            self.rates = ExchangeRates()
        except Exception as e:
            logger.warning(f"Failed to initialize exchange rates: {e}")
    
    def set_file_name(self, filename: str):
        """
        Set the filename for local data storage.
        
        Args:
            filename: Name of the file to store data
            
        Raises:
            ValueError: If filename is empty or contains invalid characters
        """
        if not filename or not filename.strip():
            raise ValueError("Filename cannot be empty")
            
        # Sanitize filename
        sanitized_filename = re.sub(r'[<>:"/\\|?*]', '_', filename.strip())
        self.save_file = os.path.join(self.save_dir, sanitized_filename)
    
    def download_data(
        self, 
        process_func: Callable, 
        params: Dict[str, Any], 
        unique_ids: Optional[List[Any]] = None):
        """
        Download and process game data with progress tracking and error handling.
        
        Args:
            process_func: Function to process API responses
            params: Parameters for API requests
            unique_ids: List of unique identifiers to download
            
        Returns:
            DownloadStats object with operation statistics
            
        Raises:
            ValueError: If required parameters are missing
            GameAPIError: If download fails critically
        """
        if not self.save_file:
            raise ValueError("Save file not set. Call set_file_name() first.")
            
        if not callable(process_func):
            raise ValueError("process_func must be callable")
            
        if not params:
            raise ValueError("params cannot be empty")
        
        try:
            # Load or initialize data
            data = self._initialize_data(unique_ids)
            
            # Determine what items need to be downloaded
            items_to_retrieve = self._get_items_to_download(data['games'], data['unique'])
            
            if not items_to_retrieve:
                logger.info("All game data already retrieved, nothing to fetch")
                return
            
            logger.info(f"Downloading {len(items_to_retrieve)} items")
            # Download items with progress tracking
            self._download_items(items_to_retrieve, params, process_func, data)
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    def _initialize_data(self, unique_ids: Optional[List[Any]]) -> Dict[str, Any]:
        """Initialize game data or load data from local file."""
        if unique_ids:
            return {'unique': unique_ids, 'games': []}
        else:
            logger.info(f"Loading stored data from: {self.save_file}")
            stored_data = load_from_json(self.save_file)
            if stored_data and 'data' in stored_data:
                return stored_data['data']
            else:
                logger.warning("No valid stored data found, starting fresh")
                return {'unique': [], 'games': []}
    
    def _get_items_to_download(self, stored_games: List[Dict], stored_uniques: List[Any]) -> List[Any]:
        """
        Determine which items still need to be downloaded.
        Find all the game ids that are in stored_uniques but not stored_games.
        
        Note:
            Local file stores all game ids that need to be downloaded (unquies)
            All games that are currently downloaded (stored_games)
        """
        if not stored_games:
            return stored_uniques
            
        # Get the primary key from the first game
        primary_key = self._get_primary_key(stored_games[0])
        if not primary_key:
            logger.warning("Could not determine primary key from stored games")
            return stored_uniques
            
        # Extract IDs of already downloaded games
        downloaded_ids = {game.get(primary_key) for game in stored_games if primary_key in game}
        
        # Return items that haven't been downloaded yet
        return [item for item in stored_uniques if item not in downloaded_ids]
    
    def _get_primary_key(self, game_data: Dict[str, Any]) -> Optional[str]:
        """
        Determine the unquie id from game data.
        Common primary keys: 'appid'
        """
        common_keys = ['appid']
        for key in common_keys:
            if key in game_data:
                return key
        
        # If no common key found, return the first key
        return next(iter(game_data.keys())) if game_data else None
    
    def _download_items(
        self, 
        items_to_retrieve: List[Any], 
        params: Dict[str, Any], 
        process_func: Callable,
        data: Dict[str, Any]
    ):
        """Download items with batching and progress tracking."""
        stored_games = data['games']
        stored_uniques = data['unique']
        
        iterations = len(items_to_retrieve)
        # Progress bar for overall download
        with tqdm(total=iterations, desc="Downloading Game Data", unit='item') as pbar:
            # Process items in batches
            for i in range(0, iterations, self.config.batch_size):
                batch = items_to_retrieve[i:i + self.config.batch_size]
                
                # Process each item in the batch
                for item_id in batch:
                    try:
                        result = self._download_single_item(item_id, params, process_func)
                        
                        if result:
                            stored_games.append(result)
                        else:
                            # Remove ID from uniques if processing failed
                            if item_id in stored_uniques:
                                stored_uniques.remove(item_id)
                            
                    except GameAPIError as e:
                        logger.error(f"Failed to download item {item_id}: {e}")
                    
                    except Exception as e:
                        logger.error(f"Unexpected error downloading item {item_id}: {e}")
                    
                    finally:
                        pbar.update(1)
                        time.sleep(self.config.sleep_time)
                
                # Save progress after each batch
                data['unique'] = stored_uniques
                data['games'] = stored_games
                self._save_data(data)
                
                # Pause between batches
                if i + self.config.batch_size < len(items_to_retrieve):
                    time.sleep(self.config.batch_pause)
    
    def _download_single_item(
        self, 
        item_id: Any, 
        param_key: str, 
        params: Dict[str, Any], 
        process_func: Callable
    ) -> Optional[Dict[str, Any]]:
        """Download game data for single item and filter it."""
        # Update parameters with current item ID
        # Get the parameter key for item ID
        current_params = params.copy()
        param_key = next(iter(current_params.keys()))
        current_params[param_key] = item_id
        
        try:
            json_data = self._make_request(self.base_url_api, current_params)
            return process_func(json_data, item_id)
                
        except requests.RequestException as e:
                status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                raise GameAPIError(f"Failed to download item {item_id}: {e}", status_code)
    
    def _save_data(self, data: Dict[str, Any]):
        """Save data to file with error handling."""
        try:
            save_to_json(self.save_file, data)
        except Exception as e:
            logger.error(f"Failed to save data to {self.save_file}: {e}")
            raise GameAPIError(f"Failed to save data: {e}")
    
    def get_data(self) -> Dict[str, Any]:
        """
        Retrieve locally stored data.
        
        Returns:
            Dictionary containing stored data, empty dict if no data found
        """
        if not self.save_file:
            logger.warning("Save file not set, returning empty data")
            return {}
            
        try:
            local_data = load_from_json(self.save_file)
            if local_data and 'data' in local_data:
                return local_data['data']
        except Exception as e:
            logger.warning(f"Failed to load data from {self.save_file}: {e}")
            
        return {'unique': [], 'games': []}
    
    def _change_price_to_dollar(self, og_price: Union[str, float], currency: str) -> float:
        """
        Convert price to USD.
        
        Args:
            og_price: Original price
            currency: Currency code
            
        Returns:
            Converted price
        """
        numeric_price = self._extract_numeric_price(og_price) if isinstance(og_price, str) else og_price
        
        if currency and currency != 'USD' and self.rates:
            try:
                numeric_price = self.rates.get_price_dollar(numeric_price, currency)
                currency = "USD"
            except Exception as e:
                logger.warning(f"Failed to convert price: {e}")
        
        return numeric_price
    
    def _extract_numeric_price(self, price_str: str) -> float:
        """
        Extract numeric value from price string.
        
        Args:
            price_str: Price as string (e.g., "$19.99", "19,99 €")
            
        Returns:
            Numeric price value
        """
        if not isinstance(price_str, str):
            return float(price_str) if price_str else 0.0
            
        # Remove common currency symbols and normalize decimal separators
        cleaned = re.sub(r'[^\d.,]', '', price_str)
        
        # Handle different decimal separators
        if ',' in cleaned and '.' in cleaned:
            # Assume last separator is decimal (e.g., "1,234.56")
            if cleaned.rfind(',') > cleaned.rfind('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Could be thousands separator or decimal separator
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Likely decimal separator (e.g., "19,99")
                cleaned = cleaned.replace(',', '.')
            else:
                # Likely thousands separator (e.g., "1,234")
                cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            logger.warning(f"Could not parse price: {price_str}")
            return 0.0
        
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
    
    @abstractmethod
    def get_base_url(self) -> str:
        """
        Get the base URL for the service.
        Must be implemented by subclasses.
        """
        pass
    
    def _process_json(self, response: Dict[str, Any], game_id: Union[int, str]) -> Dict[str, Any]:
        """
        Process game data retrieved by session request.
        Must be implemented by subclasses.
        """
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
    
    def close(self):
        """Close the session and cleanup resources."""
        if hasattr(self, 'session') and self.session:
            self.session.close()