from pydantic import BaseModel
from typing import Optional
    
class SteamPlayer(BaseModel):
    steamid: str
    persona_name: str
    profile_url: str
    avatar_full: str
    real_name: str
    country_code: str
    state_code: str

class Category(BaseModel):
    id: int
    description: str

class Genre(BaseModel):
    id: str
    description: str

class PriceOverview(BaseModel):
    currency: str
    price_in_cents: int
    final_formatted: str
    discount_percentage: int

class Metacritic(BaseModel):
    score: int
    url: str

class SteamGame(BaseModel):
    appid: int
    game_type: str
    game_name: str
    is_free: Optional[bool]
    detailed_description: str
    header_image: str
    website: Optional[str] = None
    recommendations: Optional[int] = None
    release_date: Optional[str] = None
    esrb_rating: Optional[str] = None
    developers: list[str]
    publishers: list[str]
    categories: list[Category]
    genres: list[Genre]
    price_overview: Optional[PriceOverview] = None
    metacritic: Optional[Metacritic] = None
    screenshots: list[str]
    tags: list[str]

class Wishlist(BaseModel):
  steamid: int
  appid: int
  priority: int
  
class DealsGGPrices(BaseModel):
  retail_price: float
  retail_price_low: float
  keyshop_price: float
  keyshop_price_low: float
  
class DealsGG(BaseModel):
  appid: int
  name: str
  url: str
  image_url: str
  prices: DealsGGPrices
  currency: str
  
class AppIdsRequest(BaseModel):
    appids: list[int]

def correct_user_account_response() -> dict:
    return {
        "response": {
            "players": []
        }
    }
    
def correct_user_wishlist_response() -> dict:
    return {
        "response": {
            "items": []
        }
    }
    
def correct_game_data_response(appid: str) -> dict:
    return {
        appid: {
            "data": {}
        }
    }