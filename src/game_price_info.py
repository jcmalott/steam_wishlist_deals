from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union

from src.price_data import PriceData

@dataclass
class GamePriceInfo:
    """Complete price information for a game."""
    id: str
    appid: int
    current_price: Optional[PriceData] = None
    regular_price: Optional[PriceData] = None
    lowest_price: Optional[PriceData] = None
    discount_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'id': self.id,
            'appid': self.appid,
            'discount_percent': self.discount_percent
        }
        
        if self.current_price:
            result['current_price'] = self.current_price.to_dict()
        if self.regular_price:
            result['regular_price'] = self.regular_price.to_dict()
        if self.lowest_price:
            result['lowest_price'] = self.lowest_price.to_dict()
            
        return result