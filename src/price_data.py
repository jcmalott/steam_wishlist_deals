from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union

@dataclass
class PriceData:
    """Data structure for price information."""
    amount: float
    currency: str
    formatted: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "price_current": self.amount,
            "currency": self.currency,
            "formatted": self.formatted
        }