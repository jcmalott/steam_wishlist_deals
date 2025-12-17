# GG Deals API Client
# This module provides functionality to interact with GG Deals Web API
# References:
# - https://gg.deals/api/prices/
import logging
import requests
import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class DealsGGAPI():
    """
        A client for interacting with the GG Deals API.
        Provides methods to fetch game product details.
    """
    GG_DEALS_BASE_URL = 'https://api.gg.deals/v1/prices/by-steam-app-id/'
    
    def __init__(self, api_key:str):
        self.api_key = api_key
        self.session = httpx.AsyncClient()
        
    async def find_products_by_appid(self, appids, max_price: float = 5.00) -> list[dict[str, any]] | None:      
        params = {
            'ids': ','.join(map(str, appids)),
            'key': self.api_key
        }
        
        response = await self._make_request(self.GG_DEALS_BASE_URL, params)
        game_deals = self._process_json(response, max_price)
        return game_deals
    
    # TODO: this can be in its own file
    async def _make_request(self, url, params={}) -> dict[str, any]:
        try:
            response = await self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to retrieve data from {url}!")
            raise e
    
    def _process_json(self, response, max_price) -> list[dict[str, any]] | None:
        """ 
            What to do with the game data returned by steam.
        """
        if response['success'] and response['data']:
            game_deals = response['data']
            
            return [
                game_data
                for appid, game in game_deals.items()
                if(game_data := self._filter_game_data(game, appid, max_price)) is not None
            ]
        else:
            return None
        
    def _filter_game_data(self, game: dict[str, any], appid:str, max_price: float = 5.00) -> dict[str, any] | None:
        prices = game.get("prices", {})
        if not prices:
            return None
        
        # Remove any game that is free
        retail_price = self._safe_float(prices.get("currentRetail"))
        if retail_price == 0.0:
            return None
        
        # Only allow games under a certain price point
        keyshop_price = self._safe_float(prices.get("currentKeyshops"))
        keyshop_above_max = (keyshop_price == 0.0 or keyshop_price > max_price)
        if retail_price > max_price and keyshop_above_max:
            return None
        
        return {
            "appid": int(appid),
            "name": game.get("title", "NA"),
            "url": game.get("url", "NA"),
            "image_url": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg",
            "prices": {
                "retail_price": retail_price,
                "retail_price_low": self._safe_float(prices.get("historicalRetail")),
                "keyshop_price": keyshop_price,
                "keyshop_price_low": self._safe_float(prices.get("historicalKeyshops")),
            },
            "currency": prices.get("currency", "USD")
        }
        
    def _safe_float(self, value):
        return float(value) if value else 0.00
    
    def get_base_url(self):
        return self.GG_DEALS_BASE_URL
    
    async def aclose(self):
        await self.session.aclose()