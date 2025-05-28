"""
    CheapWishlist - A tool to compare Steam wishlist prices with other gaming sites.
"""
import logging
from typing import List, Dict, Any

from src.steam_api import Steam
from src.gg_deals_api import GGDealsAPI

import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class CheapWishlist():
    """
        A class to compare Steam wishlist prices with other gaming sites.
        Sites compared so far
        - Kinguin
        
        Attributes:
            STEAM_DIR (str): Directory for storing data files
            STEAM_FILENAME (str): Filename for Steam games data
            KINGUIN_FILENAME (str): Filename for Kinguin games data
    """
    STEAM_DIR = 'data'
    STEAM_BASE_URL = 'https://store.steampowered.com/app/'
    PERSONAL_STEAM_ID = 76561198041511379 # IdentityUnk logged into account
    # PERSONAL_STEAM_ID = 76561198405376787 # Thunderduck
    # PERSONAL_STEAM_ID = 76561197970751008 # Track not login to account
    # PERSONAL_STEAM_ID = 76561198088680891 # E-5 no wishlist
    
    def __init__(self, steam_api_key:str, gg_deals_api_key:str):
        """
            Initialize CheapWishlist with Steam user ID.
            
            Args:
                steam_user_id (int): Steam user ID to fetch wishlist for
                site (str): Name of other site to check deals ('kinguin' or 'gg deals')
                other_api_key (str): API Key of other site to check against
        """
        self.steam = Steam(steam_api_key, self.STEAM_DIR + "\steam")
        self.gg_deals = GGDealsAPI(gg_deals_api_key, self.STEAM_DIR + "\ggdeals")
        
        self.stored_steam_data = {}
        self.stored_gg_deals_data = {}
        
    def initialize_data(self, steam_id: str) -> Dict[str, Any]:
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
        wishlist = self.steam.get_wishlist(steam_id)
        if len(wishlist) == 0:
            return {}
        
        # get game products from locally stored location
        # remove those without a price
        self.stored_steam_data = self.steam.get_data()
        self._filter_for_priced_games()
        
        self.gg_deals.find_products_by_name(self.stored_steam_data['games'], steam_id)
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
        return self.STEAM_BASE_URL
    
    # TODO: kinguin is going to need a get_url method
    def get_gg_base_url(self):
        """ 
            Base API url for gg deals or kinguin
        """
        return self.gg_deals.get_url()
    
    def check_user_status(self, steam_id: str) -> bool:
        """ 
            Check if id matches to a current steam user account.
        """
        return self.steam.check_user_status(steam_id)
    
    # TODO: Update so that steam does this before reaching this point
    def _filter_for_priced_games(self) -> None:
        """
            Filter for games that have prices (released games).
        """
         # get all games that have a steam price
        for index, game in enumerate(self.stored_steam_data['games']):
           if 'price' not in game:
                self.stored_steam_data['unique'].pop(index)
                self.stored_steam_data['games'].pop(index)
    
    # TODO: Update so that only steam will show if no other site is passed   
    def _get_matched_games(self, sort_from_lowest: bool= True) -> List[Dict[str, Dict[str, Any]]]:
        """
            Match Steam games with their Kinguin counterparts.
            The lowest price between the two games is also stored to be able to sort games by lowest price.
            
            Returns:
                List of dictionaries containing matched Steam and Kinguin game data
        """
        matched_games = []
        steam_games = self.stored_steam_data['games']
        steam_uniques = self.stored_steam_data['unique']
        gg_deals_games = self.stored_gg_deals_data['games']
        
        if steam_games is None:
            logger.warning(f"Match Data: Missing Steam data!")
            return matched_games
        if gg_deals_games is None:
            logger.warning(f"Match Data: Missing GG Deals data!")
            return matched_games
        
        for gg_deals_game in gg_deals_games:
            # find steam game with matching appid
            appid = gg_deals_game['appid']
            steam_index = steam_uniques.index(appid)
            
            # get price of game from both sites
            steam_game = steam_games[steam_index]
            steam_price = steam_game.get('price')
            gg_deals_price = gg_deals_game.get('price')
            
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
                'game_name': steam_game.get('name'),
                'lowest_price': lower_price,
                'steam': steam_game,
                'ggdeals': gg_deals_game
            })
        
        # ordering items so that the cheapest ones are first
        if sort_from_lowest:
            matched_games = sorted(matched_games, key=lambda x: x['lowest_price'], reverse=False)
        return matched_games
               