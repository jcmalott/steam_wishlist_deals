
"""
EDITED

WishlistInterface - A Gradio UI for comparing Steam wishlist prices with GG Deals site.

TODO:
    Add caching for API responses
    Implement async API calls for better performance
    Add user preferences (sort order, filters, etc.)
    Add export functionality for price comparisons
    Consider adding unit tests
"""
import logging
import os
import gradio as gr
from tqdm import tqdm
from typing import Dict, List, Any, Optional, Tuple
import webbrowser
from PIL import Image 
import threading
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from src.gg_deals_api import GGDealsAPI
from src.any_deal_api import AnyDealAPI
from src.price_comparison_config import PriceComparisonConfig
from src.data_class import GameData

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# TODO: Try to use dataclass
class DealsInterface:
    """
    A class that creates a Gradio interface to display and compare
    Game prices with deal aggregation sites.
    """
    
    def __init__(self, 
                 game_data: List[Dict[str, Any]], 
                 gg_deals_api_key: str, 
                 any_deal_api_key: str, 
                 steam_id: Optional[int] = None,
                 filename: Optional[str] = None,
                 config: Optional[PriceComparisonConfig] = None):
        """
        Initialize the LibraryInterface with game data and API keys.
        
        Args:
            game_data: List of game data
            gg_deals_api_key: API key for GG Deals
            any_deal_api_key: API key for Any Deal
            steam_id: Steam user ID
            filename: file to store game data prices locally
            config: Configuration object
        """
        self.game_data = game_data
        self.steam_id = steam_id
        self.config = config or PriceComparisonConfig()
        self.games: List[GameData] = []
        self._lock = threading.Lock()
        
        # Initialize API clients
        self.gg_deals = GGDealsAPI(
            gg_deals_api_key, 
            filename, 
            os.path.join(self.config.steam_data_dir, self.config.gg_deals_name)
        )
        self.any_deal = AnyDealAPI(
            any_deal_api_key, 
            filename, 
            os.path.join(self.config.steam_data_dir, self.config.any_deal_name)
        )
        
        self.ui = self._build_ui()
        
    def launch(self, inbrowser:bool = True, share:bool = True) -> None:
        """
            Launch the interface.
            
            Args:
                inbrowser: Whether to automatically open in browser
                share: Whether to create a public link
        """
        try:
            self.ui.launch(inbrowser=inbrowser, share=share)
        except Exception as e:
            logger.error(f"Failed to launch interface: {e}")
            raise
        
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
                    steam_id_box = gr.Textbox(
                        container=False, 
                        value=str(self.steam_id), 
                        interactive=True,
                        placeholder="Enter your Steam ID"
                    )
            
            # Status display for loading feedback
            status_display = gr.Markdown("", visible=False)
            
            @gr.render(inputs=[steam_id_box], triggers=[steam_id_box.submit])
            def update_games_container(steam_id: str):
                self.steam_id = steam_id.strip()
                if not steam_id:
                    gr.Markdown("Please enter a valid Steam ID")
                    return
                
                progress = gr.Progress(track_tqdm=True)
                progress(0, desc="Starting data fetch...")
                
                try:
                    self.games = self._fetch_data(progress)
                    
                    if not self.games:
                        gr.Markdown("No games found matching the criteria!")
                        return
                    
                    # Game search dropdown
                    game_names = ['All Games'] + [game.name for game in self.games]
                    search_input = gr.Dropdown(
                        choices=game_names, 
                        container=False,
                        label="Search for specific game"
                    )
                    
                    # Single game display container
                    with gr.Column(visible=False) as single_game_container:
                        single_game_components = self._create_single_game_display()
                    
                    # Multiple games display container
                    with gr.Column(visible=True) as all_games_container:
                        self._display_games()
                    
                    # Event handlers
                    search_input.change(
                        self._display_single_game, 
                        inputs=[search_input], 
                        outputs=[single_game_container, all_games_container, *single_game_components]
                    )
                    
                    steam_id_box.submit(
                        self._update_multi_display, 
                        inputs=[], 
                        outputs=[single_game_container, all_games_container]
                    )
                    
                except Exception as e:
                    logger.error(f"Error updating games container: {e}")
                    gr.Markdown(f"Error loading games: {str(e)}")
                                
        return ui  
    
    def _fetch_data(self, progress: Optional[gr.Progress] = None) -> List[GameData]:
        """ 
        Get games from user library that meet the criteria.
        
        Args:
            progress: Progress tracker for UI feedback
            
        Returns:
            List of GameData objects with price information
        """
        try:
            # Filter games by playtime
            progress(0.1, desc="Filtering library games...")
            
            appids = [item['appid'] for item in self.game_data]
            logger.info(f"Processing {len(appids)} games")
            
            # Fetch GG Deals data
            progress(0.3, desc="Fetching GG Deals data...")
            
            self.gg_deals.find_products_by_appid(appids, self.steam_id)
            gg_data = self.gg_deals.get_data()
            games_data = gg_data.get('games', [])
            
            if not games_data:
                logger.warning("No games found in GG Deals data")
                return []
            
            # Fetch AnyDeal data
            progress(0.6, desc="Fetching AnyDeal data...")
            
            search_ids = [item['appid'] for item in games_data]
            self.any_deal.find_products_by_appids(search_ids, self.steam_id)
            any_deal_data = self.any_deal.get_data()
            
            # Create lookup dictionaries for efficient data merging
            progress(0.8, desc="Processing game data...")
            
            steam_lookup = {
                item['appid']: {
                    'mins': item.get('playtime_minutes', 0), 
                    'img': item.get('header')
                } 
                for item in self.game_data
            }
            
            any_deal_lookup = {
                item['appid']: {
                    'current_price': item.get('current_price', {}).get('price_current', 0),
                    'regular_price': item.get('regular_price', {}).get('price_current', 0),
                    'lowest_price': item.get('lowest_price', {}).get('price_current', 0)
                }
                for item in any_deal_data
            }
            
            # Convert to GameData objects
            game_objects = []
            for game in games_data:
                appid = game['appid']
                steam_info = steam_lookup.get(appid, {})
                any_deal_info = any_deal_lookup.get(appid, {})
                
                game_obj = GameData(
                    appid=appid,
                    name=game.get('name', ''),
                    playtime=steam_info.get('mins', 0),
                    header_image=steam_info.get('img'),
                    current_price=any_deal_info.get('current_price', 0),
                    regular_price=any_deal_info.get('regular_price', 0),
                    lowest_price=any_deal_info.get('lowest_price', 0),
                    # TODO: this may not being access
                    gg_deals=game.get('gg_deals', {}),
                    url=game.get('url', '')
                )
                
                # Filter out free games
                if game_obj.regular_price > 0:
                    game_objects.append(game_obj)
            
            # Sort by GG Deals retail price
            sorted_games = sorted(
                game_objects, 
                key=lambda x: x.gg_deals.get('retail_price', float('inf'))
            )
            
            progress(1.0, desc=f"Loaded {len(sorted_games)} games")
            
            logger.info(f"Successfully processed {len(sorted_games)} games")
            return sorted_games
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            if progress:
                progress(1.0, desc="Error loading data")
            return []
        
    def _update_multi_display(self) -> Tuple[gr.update, gr.update]:
        """Toggle to multiple games display."""
        return gr.update(visible=False), gr.update(visible=True)
    
    def _create_single_game_display(self) -> List[gr.components.Component]:
        """Create components for single game display."""
        default_image = Image.new('RGB', (150, 200), color=(200, 200, 200))
        
        with gr.Row():
            with gr.Column(scale=1):
                game_image = gr.Image(
                    default_image, 
                    container=False, 
                    show_download_button=False, 
                    show_fullscreen_button=False
                )
            with gr.Column(scale=2):
                game_name = gr.Textbox("", show_label=False, container=False)
                
                with gr.Row():
                    gg_price_box = gr.Textbox("", label="GG Deals Price", container=False)
                    gg_historic_box = gr.Textbox("", label="GG Historic Low", container=False)
                
                with gr.Row():
                    steam_price_box = gr.Textbox("", label="Steam Price", container=False)
                    steam_low_box = gr.Textbox("", label="Steam Historic Low", container=False)
                
                with gr.Row():
                    gg_deals_btn = gr.Button("View on GG Deals", elem_classes='price_btn')
                    steam_btn = gr.Button("View on Steam", elem_classes='price_btn')
        
        # Hidden components for URLs
        gg_deals_url = gr.State("")
        steam_url = gr.State("")
        
        # Button click handlers
        gg_deals_btn.click(fn=self._open_url, inputs=[gg_deals_url])
        steam_btn.click(fn=self._open_url, inputs=[steam_url])
        
        return [
            game_name, gg_price_box, gg_historic_box, 
            gg_deals_url, game_image, steam_price_box, 
            steam_url, steam_low_box
        ]
    
    def _display_single_game(self, term: str) -> Tuple:
        """Display a single selected game."""
        default_image = Image.new('RGB', (150, 200), color=(200, 200, 200))
        
        if term == "All Games":
            return (
                gr.update(visible=False), gr.update(visible=True), 
                '', gr.update(visible=True), gr.update(visible=True), 
                '', default_image,
                gr.update(visible=True),
                '',
                gr.update(visible=True)
            )
        
        # Find the selected game
        selected_game = None
        for game in self.games:
            if game.name.lower() == term.lower():
                selected_game = game
                break
        
        if not selected_game:
            return (
                gr.update(visible=True), gr.update(visible=False),
                "Game not found", gr.update(), gr.update(),
                "", default_image
            )
        
        # Prepare display data
        gg_price = selected_game.best_gg_price
        gg_historic = selected_game.gg_deals.get('retail_price_low', 0)
        
        return (
            gr.update(visible=True), gr.update(visible=False),
            selected_game.name,
            gr.update(value=f"${gg_price:.2f}" if gg_price > 0 else "N/A"),
            gr.update(value=f"${gg_historic:.2f}" if gg_historic > 0 else "N/A"),
            selected_game.url,
            selected_game.header_image or default_image,
            gr.update(value=f"${selected_game.current_price:.2f}" if selected_game.current_price > 0 else "N/A"),
            selected_game.steam_url,
            gr.update(value=f"${selected_game.lowest_price:.2f}" if selected_game.lowest_price > 0 else "N/A")
        )
        
    def _display_games(self) -> None:
        """Display multiple games in the interface."""
        # Apply price filter if enabled
        games_to_display = self.games
        if hasattr(self.config, 'max_price_filter') and self.config.max_price_filter > 0:
            games_to_display = self._filter_games_by_price(self.games)
        
        if not games_to_display:
            gr.Markdown("No games match the current filters!")
            return
        
        # Display games in batches
        with tqdm(total=len(games_to_display), desc="Creating UI", unit='game') as pbar:
            for i in range(0, len(games_to_display), self.config.batch_size):
                batch = games_to_display[i:i + self.config.batch_size]
                for game in batch:
                    self._create_game_row(game)
                    pbar.update(1)
                    
    def _filter_games_by_price(self, games: List[GameData]) -> List[GameData]:
        """Filter games by maximum price threshold."""
        filtered = []
        max_price = self.config.max_price_filter
        
        for game in games:
            gg_deals = game.gg_deals
            retail_price = gg_deals.get('retail_price', 0)
            keyshop_price = gg_deals.get('keyshop_price', 0)
            
            has_qualifying_retail = 0 < retail_price <= max_price
            has_qualifying_keyshop = 0 < keyshop_price <= max_price
            
            if has_qualifying_retail or has_qualifying_keyshop:
                filtered.append(game)
        
        return filtered
    
    def _create_game_row(self, game: GameData) -> None:
        """
        Create a UI row for displaying a game with price comparison.
        
        Args:
            game: GameData object containing game information
        """
        default_image = Image.new('RGB', (150, 200), color=(200, 200, 200))
        
        # Calculate best GG Deals price
        best_gg_price = game.best_gg_price
        historic_low = game.gg_deals.get('retail_price_low', 0)
        
        with gr.Row(elem_classes='container game-row'):
            # Game image
            with gr.Column(scale=1):
                gr.Image(
                    game.header_image or default_image, 
                    container=False, 
                    show_download_button=False, 
                    show_fullscreen_button=False
                )
            
            # Game name
            with gr.Column(scale=4):
                gr.Textbox(game.name, show_label=False, container=False)
            
            # Price information
            with gr.Column(scale=1):
                # Current GG Deals price
                with gr.Row(elem_classes='gap'):
                    price_display = f"${best_gg_price:.2f}" if best_gg_price > 0 else "N/A"
                    gr.Textbox(
                        price_display, 
                        show_label=False, 
                        container=False, 
                        scale=2, 
                        elem_classes='better_price'
                    )
                    gg_deals_btn = gr.Button(
                        'GG Deals', 
                        scale=1, 
                        elem_classes='price_btn', 
                        interactive=bool(game.url)
                    )
                
                # Historic low GG Deals
                with gr.Row(elem_classes='gap'):
                    gr.Button('GG Low', scale=1, elem_classes='price_btn', interactive=False)
                    historic_display = f"${historic_low:.2f}" if historic_low > 0 else "N/A"
                    gr.Textbox(historic_display, show_label=False, container=False, scale=2)
                
                # Current Steam price
                with gr.Row(elem_classes='gap'):
                    steam_btn = gr.Button('Steam', scale=1, elem_classes='price_btn')
                    steam_price_display = f"${game.current_price:.2f}" if game.current_price > 0 else "N/A"
                    gr.Textbox(steam_price_display, show_label=False, container=False, scale=2)
                
                # Steam historic low
                with gr.Row(elem_classes='gap'):
                    gr.Button('Steam Low', scale=1, elem_classes='price_btn', interactive=False)
                    steam_low_display = f"${game.lowest_price:.2f}" if game.lowest_price > 0 else "N/A"
                    gr.Textbox(steam_low_display, show_label=False, container=False, scale=2)
        
        # Button click handlers
        if game.url:
            gg_deals_btn.click(lambda: self._open_url(game.url))
        steam_btn.click(lambda: self._open_url(game.steam_url))
        
    @staticmethod
    def _open_url(url: str) -> None:
        """
        Open a URL in the web browser.
        
        Args:
            url: URL to open
        """
        if url:
            try:
                webbrowser.open(url)
            except Exception as e:
                logger.error(f"Failed to open URL {url}: {e}")
    
    def _load_css(self) -> str:
        """
        Load CSS from a file.
        
        Returns:
            The CSS content or empty string if file not found
        """
        try:
            file_path = "./css/styles.css"
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"CSS file not found: {file_path}")
                return ""
        except Exception as e:
            logger.error(f"Error loading CSS: {e}")
            return ""