
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
from itertools import takewhile

from src.gg_deals_api import GGDealsAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# stop httpx logs from always showing
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class LibraryInterface():
    """
        A class that creates a Gradio interface to display and compare
        Steam wishlist prices with GG Deals sites.
    """
    # Where user can find their account id
    BATCH_SIZE = 30 # number of game rows to display
    WISHLIST_ONLY = False # only download wishlist appids
    UNDER_TEN = True # only display games where lowest price is under $10
    STEAM_DIR = 'data'
    FILENAME = 'gg_deals_library'
    USER_ID = '76561198041511379'
    TOTAL_PLAY_TIME = 30 # how long game needs to be played to show up on list
    
    def __init__(self, library: List[Dict[str,Any]], gg_deals_api_key:str, steam_id:int=None):
        """
            Initialize the WishlistInterface with game data.
            
            Args:
                steam_games: List of game data from Steam
                kinguin_games: List of game data from Kinguin
        """
        self.library = library
        self.steam_id = steam_id
        self.gg_deals = GGDealsAPI(gg_deals_api_key, self.FILENAME, self.STEAM_DIR + "\ggdeals")
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
            gr.Markdown("# Best Games Prices", elem_classes='title')
            with gr.Row(elem_id='steam_id_row'):
                gr.Button('Steam User ID', elem_classes='label', interactive=False)
                with gr.Column():
                    steam_id_box = gr.Textbox(container=False, value=f"{self.steam_id}", interactive=True)
            
            # when given a correct steam id display create wishlist interface
            @gr.render(inputs=[steam_id_box], triggers=[steam_id_box.submit])
            def update_games_container(id):
                progress=gr.Progress(track_tqdm=True)
                progress(0, desc="Starting")
                
                self.library_games = self._fetch_data()
                
                # allow user to select a game from dropdown
                names = ['All Games'] + [game['name'] for game in self.library_games]
                search_input = gr.Dropdown(choices=names, container=False)
                
                # create layout to display a select game
                with gr.Column(visible=False) as single_game_container:
                    boxes = self._create_game_row({})
                
                # create layout to display multiple games
                with gr.Column(visible=True) as all_games_container:
                    self._display_games()
                
                # display the game selected from dropdown to single game layout
                search_input.change(self._display_single_game, inputs=[search_input], outputs=[single_game_container, all_games_container, *boxes])
                # controls displaying multiple games to interface
                steam_id_box.submit(self._update_multi_display, inputs=[], outputs=[single_game_container, all_games_container])
                                
        return ui  
    
    def _fetch_data(self) -> str:
        """ 
            Get games from user library that have been played and paid for.
            
            Return: List[Dict[str, Any]], best deals for games that have beed played and paid for.
        """
        # only select games that have been played
        filtered_library = [entry for entry in self.library if entry['playtime_minutes'] >= self.TOTAL_PLAY_TIME]
        appids = [item['appid'] for item in filtered_library]
        
        # find deals for above items
        self.gg_deals.find_products_by_appid(appids, self.USER_ID)
        data = self.gg_deals.get_data()
        
        games = data['games']
        # only select games that have been paid for
        games_with_price = [item for item in games if item['price'] > 0]
        sort_games = sorted(games_with_price, key=lambda x: x['price'], reverse=False)
        
        # add playtime to game data
        library_lookup = {item['appid']: {'mins': item['playtime_minutes'], "img": item['header_image']} for item in filtered_library}
        for game in sort_games:
            appid = game['appid']
            if appid in library_lookup:
                game['playtime'] = library_lookup[appid]['mins']
                game['header_image'] = library_lookup[appid]['img']
                
        return sort_games
                
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
        default_image = Image.new('RGB', (150, 200), color=(200, 200, 200))
        if term == "All Games":
            return gr.update(visible=False), gr.update(visible=True), '', gr.update(visible=False), gr.update(visible=False), '', default_image
        for game in self.library_games:
            if game['name'].lower() == term.lower():
    
                gg_deals_class = 'better_price'
                gg_deals_link = game.get('url',"")
                gg_deals_price = game.get('price', 0)
                gg_deals_historic_price = game.get('price_lowest', 0)
                gg_img = game.get('header_image', default_image)
                
                return gr.update(visible=True), gr.update(visible=False), game['name'], gr.update(value=f"${gg_deals_price:.2f}", elem_classes=gg_deals_class), gr.update(f"${gg_deals_historic_price:.2f}", elem_classes=gg_deals_class), gg_deals_link, gg_img
        
    def _display_games(self):
        games_to_iterate = self.library_games
        if self.UNDER_TEN:
            games_to_iterate = list(takewhile(lambda game: game['price'] <= 10, self.library_games))
        iterations = len(games_to_iterate)
        if iterations == 0:
            return gr.Markdown(f"No games have been found in your wishlist!")
        
        game_rows = []   
        with tqdm(total=iterations, desc="Creating UI", unit='row') as pbar:
            for i in range(0, iterations, self.BATCH_SIZE):
                batch = games_to_iterate[i:i+self.BATCH_SIZE]
                for game in batch:
                    game_row = self._create_game_row(game)
                    game_rows.append(game_row)
                    pbar.update(1)
        
        return game_rows
    
    def _create_game_row(self, gg_deals_game: Dict[str, Any]) -> None:
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
        gg_img = gg_deals_game.get('header_image', default_image)

        with gr.Row(elem_classes='container game-row'):
            with gr.Column(scale=1):
                imagebox = gr.Image(gg_img, container=False, show_download_button=False, show_fullscreen_button=False)
            with gr.Column(scale=4):
                namebox = gr.Textbox(gg_deals_game.get('name', ""), show_label=False, container=False)
            with gr.Column(scale=1):
                with gr.Row(elem_classes='gap'):
                    gg_price_display = f"${gg_deals_price:.2f}" if gg_deals_price > 0 else "N/A"
                    gg_deals_price_box = gr.Textbox(f"{gg_price_display}", show_label=False, container=False, scale=2, elem_classes=gg_deals_class)
                    gg_deals_url = gr.Textbox(gg_deals_link, visible=False)
                    gg_deals_btn = gr.Button('GG Deals', scale=1, elem_classes='price_btn', interactive=gg_deals_price is not None)
                with gr.Row(elem_classes='gap'):
                    price_display = f"${gg_deals_historic_price:.2f}" if gg_deals_historic_price > 0 else "N/A"
                    lowest_btn = gr.Button('Lowest', scale=1, elem_classes='price_btn', interactive=False)
                    historic_price_box = gr.Textbox(f"{price_display}", show_label=False, container=False, scale=2)
        
        gg_deals_btn.click(fn=self._open_url, inputs=[gg_deals_url])
        return namebox, gg_deals_price_box, historic_price_box, gg_deals_url, imagebox  
        
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