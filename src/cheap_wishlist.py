"""
    CheapWishlist - A tool to compare Steam wishlist prices with other gaming sites.
"""
import logging
from typing import List, Dict, Any
import os

from src.steam_api import Steam
from src.gg_deals_api import GGDealsAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class CheapWishlist():
    """
        A class to compare Steam wishlist prices with other gaming sites.
        
        Attributes:
            STEAM_DIR (str): Directory for storing data files
    """
    STEAM_DIR = 'data'
    
    def __init__(self, steam_api_key:str, gg_deals_api_key:str, steam_id:int=0):
        """
            Initialize CheapWishlist with Steam user ID.
            
            Args:
                steam_api_key (str): API Key for Steam
                gg_deals_api_key (str): API Key for GG Deals
                steam_id: Steam user ID to fetch wishlist for, 0 = no user id
        """
        self.steam = Steam(steam_api_key, self.STEAM_DIR + "\steam")
        self.gg_deals = GGDealsAPI(gg_deals_api_key, "gg_deals_wl", os.path.join(self.STEAM_DIR, "ggdeals"))
        self.PERSONAL_STEAM_ID = steam_id
        
        # local storage of steam and gg deals game info
        self.stored_steam_data = {}
        self.stored_gg_deals_data = {}
        
    def initialize_data(self, steam_id:str, wishlist_only:bool=False) -> Dict[str, Any]:
        """ 
            Get users steam wishlist games.
            Find the matching games on gg deals.
            Get the steam games and gg deals products that were stored locally.
            Get rid of any games
            
            Args:
                user_id (str): The users steam id
                
            Returns:
                dict: JSON steam games with matching gg deals products
        """
        # load steam data
        self.steam.load_wishlist(steam_id, wishlist_only)
        self.stored_steam_data = self.steam.get_data()
        
        # load gg_deals data
        self.gg_deals.find_products_by_appid(self.stored_steam_data['unique'], steam_id)
        self.stored_gg_deals_data = self.gg_deals.get_data()
    
        return self._get_matched_games()
    
    def get_default_id(self):
        """ 
            Steam user Id for demostration purpose
        """
        return self.PERSONAL_STEAM_ID
    
    def get_steam_url(self):
        """ 
            Steam store API
        """
        return self.steam.get_base_url()
    
    def get_gg_base_url(self):
        """ 
            Base API url for gg deals or kinguin
        """
        return self.gg_deals.get_base_url()
    
    def check_user_status(self, steam_id: str) -> bool:
        """ 
            Check if id matches to a current steam user account.
        """
        return self.steam.check_user_status(steam_id)
    
    def _get_matched_games(self, sort_from_lowest:bool=True) -> List[Dict[str, Dict[str, Any]]]:
        """
            Match GG Deals with their Steam counterparts.
            The lowest price between the two games is stored and can be sorted by lowest price.
            
            Returns:
                List of dictionaries containing matched Steam and GG Deals game data
        """
        matched_games = []
        steam_games = self.stored_steam_data['games']
        gg_deals_games = self.stored_gg_deals_data['games']
        
        if gg_deals_games is None:
            logger.warning(f"Match Data: Missing GG Deals data!")
            return matched_games
        
        for gg_deals_game in gg_deals_games:
            gg_deals_price = gg_deals_game.get('price')
            
            if not steam_games:
                matched_games.append({
                    'game_name': gg_deals_game.get('name'),
                    'lowest_price': gg_deals_price,
                    'steam': None,
                    'ggdeals': gg_deals_game
                })
            else:
                # find steam game with matching appid
                appid = gg_deals_game['appid']
                steam_game = next((game for game in steam_games if game['appid'] == appid), {})
                if not steam_game:
                    continue
                # TODO: DELETE IF CORRECT PRICE IS WORKING
                # steam_index = steam_uniques.index(appid)
                # # get price of game from both sites
                # steam_game = steam_games[steam_index]
                steam_price = steam_game.get('price')
                
                # if both don't have a price skip to next game
                if steam_price is None and gg_deals_price is None:
                    continue
                
                # if only 1 game has a price then it's the lowest price
                if steam_price is None:
                    lower_price = gg_deals_price
                elif gg_deals_price is None:
                    lower_price = steam_price
                # both games have a price
                else:
                    lower_price = min(steam_price, gg_deals_price)
                
                matched_games.append({
                    'game_name': gg_deals_game['name'],
                    'lowest_price': lower_price,
                    'steam': steam_game,
                    'ggdeals': gg_deals_game
                })
        
        # ordering items so that the cheapest ones are first
        if sort_from_lowest:
            matched_games = sorted(matched_games, key=lambda x: x['lowest_price'], reverse=False)
        return matched_games
               