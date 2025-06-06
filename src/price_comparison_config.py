from dotenv import load_dotenv
import os

class PriceComparisonConfig:
    """Configuration class for price comparison settings."""
    
    def __init__(self):
        load_dotenv()
        
        self.batch_size: int = 30
        self.wishlist_only: bool = False
        self.max_price_filter: float = 10.0
        self.min_playtime_minutes: int = 30
        self.steam_data_dir: str = 'data'
        self.gg_deals_filename: str = 'gg_deals_library'
        self.any_deal_filename: str = 'real_deal_library'
        self.default_user_id: str = os.getenv('PERSONAL_STEAM_ID_ME')