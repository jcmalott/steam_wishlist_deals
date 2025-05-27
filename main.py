
"""
WishlistInterface - A Gradio UI for comparing Steam wishlist prices with other sites.
"""
import logging
from dotenv import load_dotenv
import os
import gradio as gr
from tqdm import tqdm
from typing import Dict, List, Any
import re
import webbrowser
from PIL import Image 

from src.cheap_wishlist import CheapWishlist

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# stop httpx logs from always showing
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class WishlistInterface():
    """
        A class that creates a Gradio interface to display and compare
        Steam wishlist prices with other sites.
    """
    CSS_PATH = "./css/styles.css"
    ACCOUNT_ID_LOCATION = "https://store.steampowered.com/account/"
    BATCH_SIZE = 30 # number of game rows to display
    
    def __init__(self, cheap_wishlist: CheapWishlist):
        """
            Initialize the WishlistInterface with game data.
            
            Args:
                steam_games: List of game data from Steam
                kinguin_games: List of game data from Kinguin
        """
        self.cheap_wishlist = cheap_wishlist
        self.steam_base_url = self.cheap_wishlist.get_steam_url()
        self.kinguin_base_url = self.cheap_wishlist.get_kinguin_url()
        self.css = self._load_css(self.CSS_PATH)
        self.ui = self._build_ui()
        
    def launch(self, inbrowser: bool = True) -> None:
        """
            Launch wishlist interface.
            
            Args:
                inbrowser: Whether to automatically open in browser
        """
        self.ui.launch(inbrowser=inbrowser, share=True)
        
    def _build_ui(self) -> gr.Blocks:
        """
            Build the Gradio UI for displaying games.
            
            Returns:
                Gradio Blocks interface
        """
        with gr.Blocks(theme='soft', css=self.css) as ui:
            gr.Markdown("# Steam Wishlist Prices", elem_classes='title')
            with gr.Row(elem_id='steam_id_row'):
                gr.Button('Steam User ID', elem_classes='label', interactive=False)
                with gr.Column():
                    steam_id_box = gr.Textbox(container=False, value=f"{self.cheap_wishlist.get_default_id()}", interactive=True)
                    gr.Markdown(self.ACCOUNT_ID_LOCATION, elem_id="info-text") 
            
            # when given a correct steam id display create wishlist interface
            @gr.render(inputs=[steam_id_box], triggers=[steam_id_box.submit])
            def update_games_container(id):
                progress=gr.Progress(track_tqdm=True)
                progress(0, desc="Starting")
        
                # Display warning for incorrect id
                error_message = self._check_id(id)
                if error_message != '':
                    gr.Markdown(error_message)
                    return None
                    
                # allow user to select a game from dropdown
                search_input = gr.Dropdown(choices=self.game_names, container=False)
                
                # create layout to display a select game
                with gr.Column(visible=False) as single_game_container:
                    boxes = self._create_game_row({},{})
                
                # create layout to display multiple games
                with gr.Column(visible=True) as all_games_container:
                    self._display_games()
                
                # display the game selected from dropdown to single game layout
                search_input.change(self._display_single_game, inputs=[search_input], outputs=[single_game_container, all_games_container, *boxes])
                # controls displaying multiple games to interface
                steam_id_box.submit(self._update_multi_display, inputs=[], outputs=[single_game_container, all_games_container])
                                
        return ui  
    
    def _check_id(self, id,) -> str:
        message_to_user = ""
        if not re.match(r"^\d+$",id):
            message_to_user += f"User Id: {id} must only contain numbers!"
        elif not self.cheap_wishlist.check_user_status(id):
            message_to_user += f"User Id: {id} doesn't exist!"
        elif not self._fetch_data(id):
            message_to_user += f"User Id: {id} has no wishlist!"
        
        return message_to_user
                
    def _update_multi_display(self):
        """ 
            Turns off the single game display.
            Turns on the multiple game display.
        """
        return gr.update(visible=False), gr.update(visible=True)
    
    def _display_single_game(self, term: str):
        """ 
            Turns on the single game display.
            Turns off the multiple game display.
        """
        if term:
            for game in self.matched_games:
                if game['steam']['name'].lower() == term.lower():
                    # namebox, steam_price_box, kinguin_price_box, steam_url, king_url  
                    name = game['steam']['name']
                    steam_url = self._create_site_url(self.steam_base_url, game['steam'], '-')
                    kinguin_url = self._create_site_url(self.kinguin_base_url, game['kinguin'], '_')
                    img = game['steam'].get("header", "")
                    
                    steam_price = float(game['steam'].get('price', 0))
                    king_price = float(game['kinguin'].get('price', 0))
                    kinguin_price = f"${king_price:.2f}" if king_price > 0 else "N/A"
                    
                    # Determine which price is better
                    steam_class = 'better_price'
                    king_class = 'price'
                    if king_price > 0 and king_price < steam_price:
                        king_class = 'better_price'
                        steam_class = 'price'
                    return  gr.update(visible=True), gr.update(visible=False), name, gr.update(value=f"${steam_price:.2f}", elem_classes=steam_class), gr.update(value=kinguin_price, elem_classes=king_class), steam_url, kinguin_url, img
            
        return gr.update(visible=False), gr.update(visible=True), '', '', '', '', '', ''
    
    def _fetch_data(self, steam_id):
        """ 
            Get steam games and matching kinguin products.
            {
                "steam": games
                "kinguin": products
            }
            
            Makes a list of all game names.
            Return True is and data was fetched.
        """
        self.matched_games = self.cheap_wishlist.initialize_data(str(steam_id)) 
        self.game_names = [game['game_name'] for game in self.matched_games]
        return len(self.matched_games) > 0
        
    def _display_games(self):
        iterations = len(self.matched_games)
        if iterations == 0:
            return gr.Markdown(f"No games have been found in your wishlist!")
        
        game_rows = []   
        with tqdm(total=iterations, desc="Creating UI", unit='row') as pbar:
            for i in range(0, iterations, self.BATCH_SIZE):
                batch = self.matched_games[i:i+self.BATCH_SIZE]
                for game in batch:
                    game_row = self._create_game_row(game['steam'],game['kinguin'])
                    game_rows.append(game_row)
                    pbar.update(1)
        
        return game_rows
        
    
    def _create_site_url(self, base_url: str, game: Dict[str, Any], replacer: str = '_') -> str:
        """
            Create a URL for the game on a given platform.
            
            Args:
                base_url: The base URL for the platform
                game: Game data dictionary
                replacer: Character to replace spaces in game name
                
            Returns:
                Complete URL for the game
        """
        if 'appid' in game:
            id = game['appid']
            name = game['name'].lower().replace(" ", replacer)
            name = re.sub(":",'', name)
            return f'{base_url}{id}/{name}'
        else:
            return base_url
    
    def _create_game_row(self, steam_game: Dict[str, Any], king_game: Dict[str, Any]) -> None:
        """
            Create a UI row for displaying a game with price comparison.
            
            Args:
                steam_game: Steam game data
                king_game: Kinguin game data
        """
        steam_link = self._create_site_url(self.steam_base_url , steam_game, '_')
        kinguin_link = self._create_site_url(self.kinguin_base_url, king_game, '-')
        
        default_image = Image.new('RGB', (150, 200), color=(200, 200, 200))
        
        # Get prices and determine if there's a deal
        steam_price = float(steam_game.get('price', 0))
        king_price = float(king_game.get('price', 0))
        
        # Determine which price is better
        steam_class = 'better_price'
        king_class = 'price'
        if king_price > 0 and king_price < steam_price:
            king_class = 'better_price'
            steam_class = 'price'
        
        with gr.Row(elem_classes='container game-row'):
            with gr.Column(scale=1):
                imagebox = gr.Image(steam_game.get("header", default_image), container=False, show_download_button=False, show_fullscreen_button=False)
            with gr.Column(scale=4):
                namebox = gr.Textbox(steam_game.get('name', ""), show_label=False, container=False)
            with gr.Column(scale=1):
                with gr.Row(elem_classes='gap'):
                    steam_price_box = gr.Textbox(f"${steam_price:.2f}", show_label=False, container=False, scale=2, elem_classes=steam_class)
                    steam_url = gr.Textbox(steam_link, visible=False)
                    steam_btn = gr.Button('Steam', scale=1,elem_classes='price_btn')
                with gr.Row(elem_classes='gap'):
                    price_display = f"${king_price:.2f}" if king_price > 0 else "N/A"
                    kinguin_price_box = gr.Textbox(f"{price_display}", show_label=False, container=False, scale=2, elem_classes=king_class)
                    king_url = gr.Textbox(kinguin_link, visible=False)
                    king_btn = gr.Button('Kinguin', scale=1, elem_classes='price_btn', interactive=king_price is not None)
        
        steam_btn.click(fn=self._open_url, inputs=[steam_url])
        king_btn.click(fn=self._open_url, inputs=[king_url])
        
        return namebox, steam_price_box, kinguin_price_box, steam_url, king_url, imagebox 
        
    @staticmethod
    def _open_url(url: str) -> None:
        """
            Open a URL in the web browser.
            
            Args:
                url: URL to open
        """
        webbrowser.open(url)
    
    def _load_css(self, file_path):
        """
            Load CSS from a file.
            
            Args:
                file_path: Path to the CSS file
                
            Returns:
                The CSS content or empty string if file not found
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return f.read()
                return 
        except Exception as e:
            logger.error(f"Error loading CSS: {str(e)}")
            return ""
        
def main():
    """Main entry point for the application."""
    load_dotenv()
    
    KINGUIN_API_KEY = os.getenv('KINGUIN_API_KEY')
    STEAM_KEY_API = os.getenv('STEAM_API_KEY')
    if not KINGUIN_API_KEY or not STEAM_KEY_API:
        raise ValueError("API keys must be set in environment variables")
    
    cheap_wishlist = CheapWishlist(STEAM_KEY_API, KINGUIN_API_KEY)
    ui = WishlistInterface(cheap_wishlist)
    ui.launch(True)
    
if __name__ == '__main__':
    main()