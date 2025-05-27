"""
    CheapWishlist - A tool to compare Steam wishlist prices with other gaming sites.
"""
import logging
from typing import List, Dict, Any

from src.steam_api import Steam
from src.kinguin_products import KinguinProducts

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
    KINGUIN_BASE_URL = 'https://www.kinguin.net/category/'
    PERSONAL_STEAM_ID = 76561198041511379 # IdentityUnk logged into account
    # PERSONAL_STEAM_ID = 76561198405376787 # Thunderduck
    # PERSONAL_STEAM_ID = 76561197970751008 # Track not login to account
    # PERSONAL_STEAM_ID = 76561198088680891 # E-5 no wishlist
    
    def __init__(self, steam_api_key, kinguin_api_key):
        """
            Initialize CheapWishlist with Steam user ID.
            
            Args:
                steam_user_id (int): Steam user ID to fetch wishlist for
        """
        self.steam = Steam(steam_api_key, self.STEAM_DIR + "\steam")
        self.kinguin = KinguinProducts(kinguin_api_key, self.STEAM_DIR + "\kinguin")
        
        self.stored_steam_data = {}
        self.stored_king_data = {}
        
    def initialize_data(self, steam_id: str) -> Dict[str, Any]:
        """ 
            Get users steam wishlist games.
            Find the matching games on kinguin.
            Get the steam games and kinguin products that were stored locally.
            Get rid of any games
            
            Args:
                user_id (str): The users steam id
                
            Returns:
                dict: JSON steam games with match kinguin products
        """
        wishlist = self.steam.get_wishlist(steam_id)
        if len(wishlist) == 0:
            return {}
        
        self.kinguin.find_products_by_name(wishlist, steam_id)
        
        # get steam games and kinguin products from locally stored location
        self.stored_steam_data = self.steam.get_data()
        self.stored_king_data = self.kinguin.get_data()
        
        # only want steam games that have a price and kinguin products that match
        self._filter_for_priced_games()
    
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
    
    def get_kinguin_url(self):
        """ 
            Kinguin store API
        """
        return self.KINGUIN_BASE_URL
    
    def check_user_status(self, steam_id: str) -> bool:
        """ 
            Check if id matches to a current steam user account.
        """
        return self.steam.check_user_status(steam_id)
        
    def _get_matched_games(self, sort_from_lowest: bool= True) -> List[Dict[str, Dict[str, Any]]]:
        """
            Match Steam games with their Kinguin counterparts.
            The lowest price between the two games is also stored to be able to sort games by lowest price.
            
            Returns:
                List of dictionaries containing matched Steam and Kinguin game data
        """
        matched_games = []
        steam_games = self.stored_steam_data.get('games')
        kinguin_games = self.stored_king_data.get('games')
        
        if steam_games is None or kinguin_games is None:
            logger.warning(f"Steam and Kinguin have no game data!")
            return matched_games
        
        for index, steam_game in enumerate(steam_games):
            # the kinguin product that matches the steam game
            kinguin_game = kinguin_games[index]
            
            # get price of game from both sites
            steam_price = steam_game.get('price')
            kinguin_price = kinguin_game.get('price')
            
            # if both don't have a price skip to next game
            if steam_price is None and kinguin_price is None:
                continue
            
            # if only 1 game has a price then it's the lowest price
            if steam_price is None:
                lower_price = kinguin_price
            elif kinguin_price is None:
                lower_price = steam_price
            # both games have a price
            else:
                lower_price = min(steam_price, kinguin_price)
                
            matched_games.append({
                'game_name': steam_game['name'],
                'lowest_price': lower_price,
                'steam': steam_game,
                'kinguin': kinguin_game
            })
        
        # ordering items so that the cheapest ones are first
        if sort_from_lowest:
            matched_games = sorted(matched_games, key=lambda x: x['lowest_price'], reverse=False)
        return matched_games
        
    def _filter_for_priced_games(self) -> None:
        """
            Filter for games that have prices (released games) and get rid of kinguin games that
            match steam games with no price.
            
            Args:
                steam_games (List[Dict]): List of Steam games
                kinguin_games (List[Dict]): List of Kinguin games
        """
         # get all games that have a steam price
        for index, game in enumerate(self.stored_steam_data['games']):
           if 'price' not in game:
               self.stored_steam_data['unique'].pop(index)
               self.stored_steam_data['games'].pop(index)
               
               uniques = self.stored_king_data['unique']
               king_index = uniques.index(game['name'])
               self.stored_king_data['unique'].pop(king_index)
               self.stored_king_data['games'].pop(king_index)
               