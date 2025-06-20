from dotenv import load_dotenv
from typing import Dict, Optional, Any, List
from dataclasses import field
import os

class DealsConfig:
    """Configuration class for price comparison settings."""
    
    def __init__(self):
        load_dotenv()
        
        """Configuration searching for a deal under max price"""
        self.price_search: bool = True # FALSE, searches deals for all games, TRUE only games under max_price
        self.max_price: float = 5.0
        
        """Configuration class for API settings."""
        self.batch_size: int = 20
        self.sleep_time: float = 1.5
        self.batch_pause: float = 2.0
        self.cache_duration: int = 72  # hours
        self.rate_limit_status_codes: List[int] = field(default_factory=lambda: [429, 503])

        """Configuration Application settings."""
        self.wishlist_only: bool = False
        self.max_price_filter: float = 10.0
        self.min_playtime_minutes: int = 30
        self.data_dir: str = 'data'
        self.gg_deals_name: str = 'ggdeals'
        self.any_deal_name: str = 'anydeal'
        self.default_user_id: str = os.getenv('PERSONAL_STEAM_ID_ME')