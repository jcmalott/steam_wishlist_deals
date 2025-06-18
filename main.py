
from dotenv import load_dotenv
import os

import json

from src.cheap_wishlist import CheapWishlist
from src.wishlist_interface import WishlistInterface
from src.deals_interface import DealsInterface
from src.steam_database import SteamDatabase
from src.steam_api import Steam

SHOW_WISHLIST = False  
def main():
    """Main entry point for the application."""
    load_dotenv()
    
    STEAM_ID = os.getenv('PERSONAL_STEAM_ID_ME')
    if not STEAM_ID:
        raise ValueError("Default Steam ID not set")
    
    GG_DEALS_KEY_API = os.getenv('GG_DEALS_API')
    if not GG_DEALS_KEY_API:
        raise ValueError("GG Deals API key must be set in environment variables")
    
    ANY_DEAL_KEY_API = os.getenv('ANY_DEAL_API_KEY')
    if not ANY_DEAL_KEY_API:
        raise ValueError("Any Deal API key must be set in environment variables")
    
    if SHOW_WISHLIST:
        STEAM_KEY_API = os.getenv('STEAM_API_KEY')
        if not STEAM_KEY_API:
            raise ValueError("Steam API key must be set in environment variables")

        # cheap_wishlist = CheapWishlist(STEAM_KEY_API, GG_DEALS_KEY_API, STEAM_ID)
        # ui = WishlistInterface(cheap_wishlist)
        name = "wl"
        steam = Steam(STEAM_KEY_API, "data/steam")
        steam.load_wishlist(STEAM_ID)
        game_data = steam.get_data()['games']
    else:
        DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
        if not DATABASE_PASSWORD:
            raise ValueError("Database password not set")
        
        name = "library"
        db = SteamDatabase('steam', 'postgres', DATABASE_PASSWORD)
        library = db.get_library(STEAM_ID)
        game_data = [
            entry for entry in library 
            if entry.get('playtime_minutes', 0) >= 30
        ]
        for game in game_data:
            game_appid = db.get_game(game['appid'])
            game['header'] = game_appid.get('header_image','')
            
    ui = DealsInterface(game_data, GG_DEALS_KEY_API, ANY_DEAL_KEY_API, STEAM_ID, name)
    ui.launch(True)
    
if __name__ == '__main__':
    main()