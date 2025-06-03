
from dotenv import load_dotenv
import os

from src.cheap_wishlist import CheapWishlist
from src.wishlist_interface import WishlistInterface
from src.library_interface import LibraryInterface
from src.steam_database import SteamDatabase

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
    
    if SHOW_WISHLIST:
        STEAM_KEY_API = os.getenv('STEAM_API_KEY')
        if not STEAM_KEY_API:
            raise ValueError("Steam API key must be set in environment variables")

        cheap_wishlist = CheapWishlist(STEAM_KEY_API, GG_DEALS_KEY_API, STEAM_ID)
        ui = WishlistInterface(cheap_wishlist)
        ui.launch(True)
    else:
        DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
        if not DATABASE_PASSWORD:
            raise ValueError("Database password not set")
    
        db = SteamDatabase('steam', 'postgres', DATABASE_PASSWORD)
        library = db.get_library(STEAM_ID)
        for game in library:
            game_data = db.get_game(game['appid'])
            game['header_image'] = game_data.get('header_image','')
            
        ui = LibraryInterface(library, GG_DEALS_KEY_API, STEAM_ID)
        ui.launch(True)
    
if __name__ == '__main__':
    main()