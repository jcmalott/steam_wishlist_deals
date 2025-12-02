from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

@dataclass
class GameData:
    """ Data Class for game information."""
    appid: int
    name: str
    playtime: int=0
    header_image: Optional[str]=None
    steam_price:float = 0.0
    current_price:float = 0.0
    regular_price:float = 0.0
    steam_lowest_price:float = 0.0
    key_lowest_price:float = 0.0
    gg_deals: Dict[str,Any] = field(default_factory=dict)
    url: str = ""
    
    @property
    def steam_url(self) -> str:
        """Generate Steam store URL"""
        return f"https://store.steampowered.com/app/{self.appid}"
    
    @property
    def best_gg_price(self) -> float:
        """Get the best price from GG Deals (retail or keyshop)."""
        if not self.gg_deals:
            return 0.0
        
        retail_price = self.gg_deals.get('retail_price', 0)
        keyshop_price = self.gg_deals.get('keyshop_price', 0)
        
        if retail_price == 0:
            return keyshop_price
        elif keyshop_price == 0:
            return retail_price
        else:
            return min(retail_price, keyshop_price)