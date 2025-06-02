
from dotenv import load_dotenv
import os

from src.cheap_wishlist import CheapWishlist
from src.wishlist_interface import WishlistInterface

    
def main():
    """Main entry point for the application."""
    load_dotenv()
    
    STEAM_KEY_API = os.getenv('STEAM_API_KEY')
    GG_DEALS_KEY_API = os.getenv('GG_DEALS_API')
    STEAM_ID = os.getenv('PERSONAL_STEAM_ID_ME')
    if not STEAM_KEY_API:
        raise ValueError("Steam API key must be set in environment variables")
    if not GG_DEALS_KEY_API:
        raise ValueError("GG Deals API key must be set in environment variables")
    if not STEAM_ID:
        raise ValueError("Default Steam ID not set")
    
    cheap_wishlist = CheapWishlist(STEAM_KEY_API, GG_DEALS_KEY_API, STEAM_ID)
    ui = WishlistInterface(cheap_wishlist)
    ui.launch(True)
    
if __name__ == '__main__':
    main()