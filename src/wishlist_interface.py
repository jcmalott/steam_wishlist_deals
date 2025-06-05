
"""
WishlistInterface - A Gradio UI for comparing Steam wishlist prices with GG Deals site.
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
        Steam wishlist prices with GG Deals sites.
    """
    # Where user can find their account id
    ACCOUNT_ID_LOCATION = "https://store.steampowered.com/account/"
    BATCH_SIZE = 30 # number of game rows to display
    WISHLIST_ONLY = False # only download wishlist appids
    UNDER_TEN = True # only display games where lowest price is under $10
    
    def __init__(self, cheap_wishlist:CheapWishlist):
        """
            Initialize the WishlistInterface with game data.
            
            Args:
                steam_games: List of game data from Steam
                kinguin_games: List of game data from Kinguin
        """
        self.cheap_wishlist = cheap_wishlist
        self.steam_base_url = self.cheap_wishlist.get_steam_url()
        self.gg_deals_base_url = self.cheap_wishlist.get_gg_base_url()
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
        with gr.Blocks(theme='soft', css=self._load_css()) as ui:
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
        
                # Get steam and gg deals data
                check_for_error = self._fetch_data(id)
                if check_for_error != '':
                    gr.Markdown(check_for_error)
                    return None
                  
                # allow user to select a game from dropdown
                names = ['All Games'] + self.game_names
                search_input = gr.Dropdown(choices=names, container=False)
                
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
    
    def _fetch_data(self, id) -> str:
        message_to_user = ""
        if not re.match(r"^\d+$",id):
            message_to_user += f"User Id: {id} must only contain numbers!"
        # TODO add check user id back in
        # elif not self.cheap_wishlist.check_user_status(id):
        #     message_to_user += f"User Id: {id} doesn't exist!"
        else:
            self.matched_games = self.cheap_wishlist.initialize_data(str(id), self.WISHLIST_ONLY) 
            self.game_names = [game['game_name'] for game in self.matched_games]
            if len(self.matched_games) < 0:
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
        if term == "All Games":
            return gr.update(visible=False), gr.update(visible=True), '', gr.update(visible=False), '', gr.update(visible=False), gr.update(visible=False), '', Image.new('RGB', (150, 200), color=(200, 200, 200))
        for game in self.matched_games:
            if game['game_name'].lower() == term.lower():
    
                gg_deals = game['ggdeals']
                gg_deals_class = 'better_price'
                gg_deals_link = gg_deals.get('url',"")
                gg_deals_price = gg_deals.get('price', 0)
                gg_deals_historic_price = gg_deals.get('price_lowest', 0)
                
                # figure out if steam or gg deals has the better price
                steam_class = 'price'
                if game['steam']:
                    steam_link = self._create_site_url(self.steam_base_url, game['steam'], '-')
                    steam_price = game['steam'].get('price', 0)
                    if gg_deals_price < 0 and gg_deals_price > steam_price:
                        gg_deals_class = 'price'
                        steam_class = 'better_price'
            
                img = game['steam'].get("header", "")
    
                return gr.update(visible=True), gr.update(visible=False), game['game_name'], gr.update(value=f"${steam_price:.2f}", elem_classes=steam_class), steam_link, gr.update(value=f"${gg_deals_price:.2f}", elem_classes=gg_deals_class), gr.update(f"${gg_deals_historic_price:.2f}", elem_classes=gg_deals_class), gg_deals_link, img
        
    def _display_games(self):
        games_to_iterate = self.matched_games
        if self.UNDER_TEN:
            games_to_iterate = list(filter(lambda game: game['lowest_price'] <= 10, self.matched_games))
        iterations = len(games_to_iterate)
        if iterations == 0:
            return gr.Markdown(f"No games have been found in your wishlist!")
        
        game_rows = []   
        with tqdm(total=iterations, desc="Creating UI", unit='row') as pbar:
            for i in range(0, iterations, self.BATCH_SIZE):
                batch = games_to_iterate[i:i+self.BATCH_SIZE]
                for game in batch:
                    game_row = self._create_game_row(game['steam'], game['ggdeals'])
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
    
    def _create_game_row(self, steam_game: Dict[str, Any], gg_deals_game: Dict[str, Any]) -> None:
        """
            Create a UI row for displaying a game with price comparison.
            
            Args:
                steam_game: Steam game data
                gg_deals_game: GG Deals site game data
        """
        default_image = Image.new('RGB', (150, 200), color=(200, 200, 200))
        
        gg_deals_class = 'better_price'
        gg_deals_link = gg_deals_game.get('url',"")
        gg_deals_price = gg_deals_game.get('price', 0)
        gg_deals_historic_price = gg_deals_game.get('price_lowest', 0)
        
        # figure out if steam or gg deals has the better price
        steam_class = 'price'
        steam_link = self._create_site_url(self.steam_base_url , steam_game, '_') if steam_game else ''
        steam_price = steam_game.get('price', 0)
        if gg_deals_price < 0 and gg_deals_price > steam_price:
                gg_deals_class = 'price'
                steam_class = 'better_price'
        

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
                    gg_price_display = f"${gg_deals_price:.2f}" if gg_deals_price > 0 else "N/A"
                    gg_deals_price_box = gr.Textbox(f"{gg_price_display}", show_label=False, container=False, scale=2, elem_classes=gg_deals_class)
                    gg_deals_url = gr.Textbox(gg_deals_link, visible=False)
                    gg_deals_btn = gr.Button('GG Deals', scale=1, elem_classes='price_btn', interactive=gg_deals_price is not None)
                with gr.Row(elem_classes='gap'):
                    price_display = f"${gg_deals_historic_price:.2f}" if gg_deals_historic_price > 0 else "N/A"
                    lowest_btn = gr.Button('Lowest', scale=1, elem_classes='price_btn', interactive=False)
                    historic_price_box = gr.Textbox(f"{price_display}", show_label=False, container=False, scale=2)
        
        
        steam_btn.click(fn=self._open_url, inputs=[steam_url])
        gg_deals_btn.click(fn=self._open_url, inputs=[gg_deals_url])
        
        return namebox, steam_price_box, steam_url, gg_deals_price_box, historic_price_box, gg_deals_url, imagebox  
        
    @staticmethod
    def _open_url(url: str) -> None:
        """
            Open a URL in the web browser.
            
            Args:
                url: URL to open
        """
        webbrowser.open(url)
    
    def _load_css(self):
        """
            Load CSS from a file.
            
            Args:
                file_path: Path to the CSS file
                
            Returns:
                The CSS content or empty string if file not found
        """
        try:
            file_path = "./css/styles.css"
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return f.read()
                return 
        except Exception as e:
            logger.error(f"Error loading CSS: {str(e)}")
            return ""