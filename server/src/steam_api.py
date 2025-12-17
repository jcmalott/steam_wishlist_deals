""" 
Helpful Links:
    https://api.steampowered.com/IWishlistService/GetWishlist/v1?steamid=76561198041511379
    Wishlist

    https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=09A19535C0064A3301527FD3AE352D7E&steamid=76561198041511379&format=json&include_played_free_games=True
    In Library

    https://store.steampowered.com/api/appdetails?appids=532790
    Game Info
"""
import httpx
import logging
import re
import asyncio
from datetime import datetime
import time
from bs4 import BeautifulSoup

from src.types.steam import correct_user_account_response, correct_game_data_response, correct_user_wishlist_response

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class Steam():
    """ 
     Steam API client class to access data.
     - User wishlist and library
     - Game data
     - Steam user accounts
    """
    # URL endpoints for different Steam API services
    STEAM_WISHLIST_URL = 'https://api.steampowered.com/IWishlistService/GetWishlist/v1'
    STEAM_LIBRARY_URL = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
    STEAM_GAME_URL = 'https://store.steampowered.com/api/appdetails'
    STEAM_USER_URL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
    STEAM_TAG_URL = "https://partner.steamgames.com/doc/store/tags"
    STEAM_BASE_URL = "https://store.steampowered.com/app/"
    
    def __init__(self, steam_api_key: str):
        """ 
            Initialize Steam API client.
            
            Args:
                steam_api_key: Steam API key for authentication
        """
        if not steam_api_key:
            raise ValueError("API key cannot be empty or None")
        
        self.steam_api_key = steam_api_key
        self.session = httpx.AsyncClient()
    
    async def get_user_account(self, user_id: str) -> dict[str, any]:
        """
            Retrieves a user steam account information.
                
            Returns: user profile information or empty dict if user not found
            Raises: 
                ValidationError if player data structure is invalid
                ValueError if player response is invalid
                httpx.HTTPError if request fails
        """
        params = {
            'key': self.steam_api_key,
            'steamids': user_id
        }
        
        response = await self._make_request(self.STEAM_USER_URL, params)
        player = self._check_response(response, correct_user_account_response())
        if len(player) == 0:
            raise ValueError(f'No Player found in Steam API response')
        
        processed_data = self._process_user_data(player[0])
        if not processed_data:
            logger.warning(f"Steam UserId: {user_id} doesn't exist!")
        
        return processed_data
    
    async def _make_request(self, url, params={}) -> dict[str, any]:
        """
            Retrieves data from url if it exists.
                
            Returns: response from given url.
            Raises: 
                httpx.HTTPError if request fails
        """
        try:
            response = await self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to retrieve data from {url}!")
            raise e
        
    # TODO: This can be in its own file, nothing to do with steam_api   
    def _check_response(self, response: dict[str, any], correct_structure: dict[str, any]) -> dict[str, any]:
        """ 
            Checks that response has correct response key word.
            Return: Data within response, empty is response doesn't exist.
            Raises: 
                ValueError if player response is invalid
        """
        for key, value in correct_structure.items():
            if key not in response:
                raise ValueError(f'No {key} field in Steam API response')  
            
            for sub_key in value.keys():
                if not isinstance(response[key], dict) and sub_key not in response[key]:
                    raise ValueError(f'No {sub_key} field in Steam API response') 
            
                return response[key][sub_key]
        
            
    def _process_user_data(self, user_data: dict[str,any]) -> dict[str, any]:
        """ 
            Process users Steam account data
            
            Args: user_data: JSON response containing Steam account data  
            Returns: Processed Steam user account data or empty dict if user not found
        """
        process_data = {
            "steamid": user_data.get("steamid", ""),
            "persona_name": user_data.get("personaname", ""),
            "profile_url": user_data.get("profileurl", ""),
            "avatar_full": user_data.get("avatarfull", ""),
            "real_name": user_data.get("realname", ""),
            "country_code": user_data.get("loccountrycode", ""),
            "state_code": user_data.get("locstatecode", ""),
        }
        
        return process_data
          
    async def get_games_data(self, appids: list[int])-> list[dict[str,any]]:
        """ 
        Note: Steam only allows 200 calls per 5 minutes
        - (5*60) / 200 = 1.5
        """
        wait_time = 1.6
        try:
            games_downloaded = 0
            games_to_download = len(appids)
            processed_games = []
            
            for appid in appids:
                processed_game = await self.get_game_data(appid)
                if processed_game:
                    processed_games.append(processed_game)
                await asyncio.sleep(wait_time)
                games_downloaded += 1
                logger.info(f"Games: {games_downloaded}/{games_to_download} games retrieved from Server!") 
            
            logger.info(f"Games: {len(processed_games)} games retrieved from Server!") 
            return processed_games
        except httpx.HTTPError as e:
            raise httpx.HTTPError(f"Games Retrieval Error: {e}")
    
    # TODO: test success sending back false
    async def get_game_data(self, appid: int)-> dict[str, any]:
        """
            Retrieves game data, in english, from steam server.
            Return: dict containing all important game data
        """
        params = {
            'appids': appid,
            'l': 'english'
        }
        
        response = await self._make_request(self.STEAM_GAME_URL, params)
        game = self._check_response(response, correct_game_data_response(str(appid)))
        
        processed_data = self._process_game_data(appid, game)
        if not processed_data:
            logger.warning(f"GameId: {appid} has no information!")
            
        processed_data["tags"] = await self.get_steam_tags(appid)
        return processed_data     
        
    def _process_game_data(self, appid: int, game: dict[str,any]) -> dict[str,any]:
        """ 
        Collect only the important game data from response.
        Return: dict containing important game information.
        """
        recommendations = game["recommendations"].get("total", 0) if "recommendations" in game else 0
        
        rating = game["ratings"].get("esrb","rp") if "ratings" in game and game["ratings"] != None else "rp"
        if rating != "rp":
            rating = rating.get("rating", "rp")
            
        detailed_description = self._strip_for_text(game.get("detailed_description", ""))
        
        process_data = {
            "appid": appid,
            "game_type": game.get("type", ""),
            "game_name": game.get("name", "Unknown"),
            "is_free": game.get("is_free", False),
            "detailed_description": detailed_description,
            "header_image": game.get("header_image", ""),
            "website": game.get("website", ""),
            "recommendations": recommendations,
            "release_date": self._parse_release_date(game.get("release_date", '')),
            "esrb_rating": rating,
            "developers": game.get("developers", []),
            "publishers": game.get("publishers", []),
            "categories": game.get("categories", []),
            "genres": game.get("genres", [])
        }
        
        process_data["price_overview"] = self._get_game_price(game)  
        process_data["metacritic"] = self._get_game_metacritic(game)
        
        screenshots = game.get('screenshots', [])
        if screenshots and len(screenshots) > 4:
            screenshots = screenshots[0:4]
        process_data["screenshots"] = [image['path_full'] for image in screenshots]
        
        return process_data
    
    def _get_game_price(self, data: dict[str, any]) -> dict[str,any]:
        """ 
        Return: dict containing game's price info. Sets default price info is none is found.
        """
        price = data.get("price_overview",{})
        if not price:
            price = {
                "currency": "",
                "price_in_cents":  0,
                "final_formatted": '',
                "discount_percentage": 0,
            }
        else:
           price: dict[str, any] = {
                "currency": price.get("currency", ""),
                "price_in_cents": price.get("final", 0), # price is returned in cents
                "final_formatted": price.get("final_formatted", ''),
                "discount_percentage": price.get("discount_percent", 0),
            }  
        return price
    
    def _get_game_metacritic(self, data: dict[str, any]) -> dict[str,any]:
        """ 
        Return: Game's user rating. Sets default user rating if none is found.
        """
        metacritic = data.get("metacritic", {})
        if not metacritic:
            metacritic = {
                "score": 0,
                "url":  ""
            }
        else:
           metacritic = {
                "score": metacritic.get("score", 0),
                "url": metacritic.get("url", ""),
            }
           
        return metacritic
    
    async def get_steam_tags(self, appid) -> list:
        tags = []
        try:
            wait_time = 1.6
            res = await self.session.get(f"{self.STEAM_BASE_URL}{appid}")
            
            if res.status_code == 302:
                res = await self._handle_age_gate(res)
                
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            tags_container = soup.find('div', class_='glance_tags popular_tags')
            if not tags_container:
                return []
            
            tags_links = tags_container.find_all('a', class_='app_tag')
            
            for link in tags_links:
                tag_text = link.get_text().strip()
                if tag_text:
                    tags.append(tag_text)
            await asyncio.sleep(wait_time)
                    
        except httpx.HTTPError as e:
            logger.error(f"Games Retrieval Error: {e}")
            raise httpx.RequestError(f"Failed to retrieve tags from {self.STEAM_BASE_URL}{appid}!")
                
        return tags
            
    async def _handle_age_gate(self, res: httpx.Response) -> httpx.Response:
        age_data = {
            'ageDay': '1',
            'ageMonth': 'January',
            'ageYear': '2000'
        }
        
        redirect_location = res.headers.get('location', '')
        if 'agecheck' in redirect_location:
            res = await self.session.post(redirect_location, data=age_data)
            
        return res
    
    def _parse_release_date(self, date_string: str) -> str | str:
        """Convert release date to valid format or empty str if invalid"""
        if not date_string:
            return ''
        
        release_date = date_string.get("date","")
        if not release_date:
            return ''
        
        try:
            parsed_date = datetime.strptime(release_date, '%b %d, %Y')
            return parsed_date.date().isoformat()
        except (ValueError, AttributeError):
            return ''
     
    async def get_wishlist(self, steam_id) -> list[dict]:
        """ 
            list of games the user wants.
        """
        params = {
            'steamid': steam_id,
            'key': self.steam_api_key
        }
        
        response = await self._make_request(self.STEAM_WISHLIST_URL, params)
        wishlist = self._check_response(response, correct_user_wishlist_response())
        if len(wishlist) == 0:
            raise ValueError(f'SteamId: {steam_id}, no wishlist found.')
        
        processed_data = self._process_wishlist_data(wishlist, steam_id)
        if not processed_data:
            logger.warning(f"SteamId: {steam_id} has no wishlist items!")
        else:
            logger.info(f"SteamId {steam_id}, {len(processed_data)} wishlist items retrieved from Server!")
            
        return processed_data
    
    def _process_wishlist_data(self, wishlist: dict[str,any], user_id: str) -> list[dict]:
        """ 
            Get game appids from users wishlist.
            
            Return: list containing dict with appid and priority.
            - appid: id of game
            - priority: How much user wants that game. 1 = Most Wanted
        """
        process_data = []
        for item in wishlist:
            if "appid" in item:
                process_data.append({
                    "steamid": user_id,
                    "appid": item["appid"],
                    "priority": item.get("priority", 9999)
                })
            
        return process_data
    
    
    
    
        
    # def get_all_steam_tags(self) -> list:
    #     """ 
    #     Gets a list of all steam approved tags.
    #     """
    #     try:
    #         res = self.session.get(self.STEAM_TAG_URL)
    #         res.raise_for_status()
            
    #         soup = BeautifulSoup(res.text, 'html.parser')
    #         main_doc = soup.find('div', class_='documentation_bbcode')
            
    #         all_tags_table = main_doc.find_all('h2', class_='bb_section')[-1]
    #         if not all_tags_table:
    #             print("Tag Table Not Found")
    #             return []
            
    #         current_element = all_tags_table.find_next_sibling()
    #         tags = []
    #         while current_element:
    #             if current_element.name == 'h2' and 'bb_section' in current_element.get('class'):
    #                 print(f"Reach end of Tags Section!")
    #                 break
                
    #             if current_element.name == 'h2' and 'bb_subsection' in current_element.get('class'):
    #                 cat_name = current_element.get_text().strip()
    #                 # clean up text
    #                 cat_name = cat_name.split('\n')[0].strip()
                    
    #                 table = current_element.find_next_sibling()
    #                 if not table.find('tbody'):
    #                     table = current_element.find_next_sibling()
                        
    #                 if table:
    #                     for row in table.find_all('tr'):
    #                         cell = row.find('td')
    #                         if cell:
    #                             tag_text = cell.get_text().strip()
    #                             if tag_text:
    #                                 tags.append(tag_text)
    #                 else:
    #                     print(f"Empty Table Found!")
                        
    #             current_element = current_element.find_next_sibling()
            
    #         unique_tags = list(dict.fromkeys(tags))
    #         return unique_tags
    #     except requests.RequestException as e:
    #         print(f"Error fetching Appid: {e}")
    #         return []    
    
    # def get_library(self, user_id):
    #     """ 
    #         Get all game ids that are stored within the users library from steam server.
    #         This will be games that the user owns.
    #     """
    #     params = {
    #         'key': self.steam_api_key,
    #         'steamid': user_id,
    #         'format': 'json',
    #         'include_played_free_games': True
    #     }
        
    #     response = self._make_request(self.STEAM_LIBRARY_URL, params)
    #     data = self._check_response(response, 'games')
    #     if not data:
    #         logger.warning("Failed to get library data.")
        
    #     processed_data = self._process_library_data(data, user_id)
    #     if not processed_data:
    #         logger.warning(f"UserId: {user_id} has no library items!")
    #     else:
    #         logger.info(f"Library: UserId {user_id} library retrieved from Server!")
            
    #     return processed_data
    
    # def get_appid_from_link(self, link: str) -> int | None:
    #     """
    #     Retrieves appid from steam link if there is one.

    #     Args:
    #         link (str): link to game's steam page

    #     Returns:
    #         int: appid of game
    #     """
    #     # Extract number after /app/
    #     appid = None
    #     match = re.search(r'/app/(\d+)', link)
    #     if match:
    #         appid = int(match.group(1))
        
    #     return appid
    
    
    # def _process_library_data(self, response: dict[str,any], user_id: str) -> list[dict]:
    #     """ 
    #         Get appid and playtime of all games found within user's library.
            
    #         Return: list of dict containing appid and playtime mintues
    #         - appid: id of game
    #         - playtime_minutes: How long user has played the game.
    #     """
    #     games = response.get("games", []) if "games" in response else []
    #     if not games:
    #         logger.warning("No games in library.")
    #         return []
        
    #     process_data = []
    #     for game in games:
    #         if "appid" in game:
    #             process_data.append({
    #                 "steamid": user_id,
    #                 "appid": game["appid"],
    #                 "playtime_minutes": game["playtime_forever"]
    #             })
            
    #     return process_data
    
    def _strip_for_text(self, text):
        # Remove HTML tags
        clean_text = re.sub(r'<.*?>', '', text)
        text = text.replace('"', "'")
        # Replace HTML entities
        clean_text = clean_text.replace('&nbsp;', ' ')
        # Remove extra spaces and newlines
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        clean_text = clean_text.strip()
        return clean_text
    
    async def aclose(self):
        await self.session.aclose()