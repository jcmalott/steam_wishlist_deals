""" 
Helpful Links:
https://api.steampowered.com/IWishlistService/GetWishlist/v1?steamid=76561198041511379
Wishlist

https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=09A19535C0064A3301527FD3AE352D7E&steamid=76561198041511379&format=json&include_played_free_games=True
In Library

https://store.steampowered.com/api/appdetails?appids=532790
Game Info
"""
import requests
from typing import Dict, Any, List
import logging
import re
import time
from bs4 import BeautifulSoup

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
    
    def __init__(self, steam_api_key: str, user_id: str):
        """ 
            Initialize Steam API client with API key and user ID
            
            Args:
                steam_api_key: Steam API key for authentication
                user_id: Steam user ID to retrieve data for
        """
        if not steam_api_key or not steam_api_key.strip():
            raise ValueError("API key cannot be empty or None")
        
        self.steam_api_key = steam_api_key
        self.user_id = user_id
        self.session = requests.Session()
        self._check_user_account()
        
    
    def _check_user_account(self) -> bool:
        """
            Check to see if user has a steam account.
                
            Returns: True if user was found
        """
        params = {
            'key': self.steam_api_key,
            'steamids': self.user_id
        }
        
        response = self._make_request(self.STEAM_USER_URL, params)
        data = self._check_response(response)
        if not data:
            logger.warning(f"Steam UserId: {self.user_id} doesn't exist!")
            return False
        
        players = data.get("players", [])
        user_exist = len(players) > 0
        return user_exist
    
    def _check_response(self, response) -> Dict[str, Any]:
        """ 
            Checks that response has correct response key word.
            Return: Data within response, empty is response doesn't exist.
        """
        if "response" not in response:
            logger.warning(f"Incorrect Response Returned")
            return {}
            
        return response["response"]
            
    def get_user_account_data(self) -> Dict[str, Any]:
        """
            Retrieves a user steam account information.
                
            Returns: user profile information or empty dict if user not found
        """
        params = {
            'key': self.steam_api_key,
            'steamids': self.user_id
        }
        
        response = self._make_request(self.STEAM_USER_URL, params)
        data = self._check_response(response)
        if not data:
            logger.warning("Failed to get user data.")
            
        processed_data = self._process_user_data(response)
        if not processed_data:
            logger.warning(f"Steam UserId: {self.user_id} doesn't exist!")
        
        return processed_data
        
    def _make_request(self, url, params={}) -> Dict[str, Any]:
        """
            Retrieves data from url if it exists.
                
            Returns: response from given url.
        """
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if not data:
                logger.warning(f"Incorrect Response Returned")
                return {}
            
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve data from {url}!")
            return {}
        
            
    def _process_user_data(self, response: Dict[str,Any]) -> Dict[str, Any]:
        """ 
            Process users Steam account data
            
            Args: response: JSON response containing Steam account data  
            Returns: Processed Steam user account data or empty dict if user not found
        """
        user = response.get("players", []) if "players" in response else []
        if not user:
            logger.warning(f"No User data was returned.")
            return {}
        
        # get the first and only user that was returned
        user_data = user[0]
        steamid = user_data.get("steamid", "")
        # check the user data is actually our user
        if not steamid or steamid != self.user_id:
            logger.warning(f"User Id doesn't Match")
            return {}
        
        # Extract relevant user account data
        process_data = {
            "steamid": steamid,
            "persona_name": user_data.get("personaname", ""),
            "profile_url": user_data.get("profileurl", ""),
            "avatar_full": user_data.get("avatarfull", ""),
            "real_name": user_data.get("realname", ""),
            "country_code": user_data.get("loccountrycode", ""),
            "state_code": user_data.get("locstatecode", ""),
        }
        
        return process_data
    
    def get_wishlist(self) -> List[Dict]:
        """ 
            List of games the user wants.
        """
        params = {
            'steamid': self.user_id,
            'key': self.steam_api_key
        }
        
        response = self._make_request(self.STEAM_WISHLIST_URL, params)
        data = self._check_response(response)
        if not data:
            logger.warning("Failed to get wishlist data.")
        
        processed_data = self._process_wishlist_data(data)
        if not processed_data:
            logger.warning(f"UserId: {self.user_id} has no wishlist items!")
        else:
            logger.info(f"Wishlist: UserId {self.user_id} wishlist retrieved from Server!")
            
        return processed_data
        
        
    def _process_wishlist_data(self, response: Dict[str,Any]) -> List[Dict]:
        """ 
            Get game appids from users wishlist.
            
            Return: list containing Dict with appid and priority.
            - appid: id of game
            - priority: How much user wants that game. 1 = Most Wanted
        """
        items = response.get("items", []) if "items" in response else []
        if not items:
            return []
        
        process_data = []
        for item in items:
            if "appid" in item:
                process_data.append({
                    "steamid": self.user_id,
                    "appid": item["appid"],
                    "priority": item.get("priority", 9999)
                })
            
        return process_data
    
    def get_library(self):
        """ 
            Get all game ids that are stored within the users library from steam server.
            This will be games that the user owns.
        """
        params = {
            'key': self.steam_api_key,
            'steamid': self.user_id,
            'format': 'json',
            'include_played_free_games': True
        }
        
        response = self._make_request(self.STEAM_LIBRARY_URL, params)
        data = self._check_response(response)
        if not data:
            logger.warning("Failed to get library data.")
        
        processed_data = self._process_library_data(data)
        if not processed_data:
            logger.warning(f"UserId: {self.user_id} has no library items!")
        else:
            logger.info(f"Library: UserId {self.user_id} library retrieved from Server!")
            
        return processed_data
    
    def _process_library_data(self, response: Dict[str,Any]) -> List[Dict]:
        """ 
            Get appid and playtime of all games found within user's library.
            
            Return: List of Dict containing appid and playtime mintues
            - appid: id of game
            - playtime_minutes: How long user has played the game.
        """
        games = response.get("games", []) if "games" in response else []
        if not games:
            logger.warning("No games in library.")
            return []
        
        process_data = []
        for game in games:
            if "appid" in game:
                process_data.append({
                    "steamid": self.user_id,
                    "appid": game["appid"],
                    "playtime_minutes": game["playtime_forever"]
                })
            
        return process_data
    
    def get_games_data(self, appids: List[int])-> List[Dict[str,Any]]:
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
                processed_game = self.get_game_data(appid)
                if processed_game:
                    processed_games.append(processed_game)
                time.sleep(wait_time)
                games_downloaded += 1
                logger.info(f"Games: {games_downloaded}/{games_to_download} games retrieved from Server!") 
            
            logger.info(f"Games: {len(processed_games)} games retrieved from Server!") 
            return processed_games
        except requests.RequestException as e:
            logger.error(f"Games: failed to retrieve!")
            raise requests.RequestException(f"Failed to retrieve games from server!")
    
    def get_game_data(self, appid: int)-> Dict[str, Any]:
        """
            Retrieves game data, in english, from steam server.
            Return: Dict containing all important game data
        """
        params = {
            'appids': appid,
            'l': 'english'
        }
        
        response = self._make_request(self.STEAM_GAME_URL, params)
        if not response:
            logger.warning(f"Failed to get game {appid} data.")
        
        processed_data = self._process_game_data(str(appid), response)
        if not processed_data:
            logger.warning(f"GameId: {appid} has no information!")
            
        return processed_data
    
    def get_all_steam_tags(self, html_content) -> List:
        """ 
        Gets a list of all steam approved tags.
        """
        try:
            res = self.session.get(self.STEAM_TAG_URL)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            main_doc = soup.find('div', class_='documentation_bbcode')
            
            all_tags_table = main_doc.find_all('h2', class_='bb_section')[-1]
            if not all_tags_table:
                print("Tag Table Not Found")
                return []
            
            current_element = all_tags_table.find_next_sibling()
            tags = []
            while current_element:
                if current_element.name == 'h2' and 'bb_section' in current_element.get('class'):
                    print(f"Reach end of Tags Section!")
                    break
                
                if current_element.name == 'h2' and 'bb_subsection' in current_element.get('class'):
                    cat_name = current_element.get_text().strip()
                    # clean up text
                    cat_name = cat_name.split('\n')[0].strip()
                    
                    table = current_element.find_next_sibling()
                    if not table.find('tbody'):
                        table = current_element.find_next_sibling()
                        
                    if table:
                        for row in table.find_all('tr'):
                            cell = row.find('td')
                            if cell:
                                tag_text = cell.get_text().strip()
                                if tag_text:
                                    tags.append(tag_text)
                    else:
                        print(f"Empty Table Found!")
                        
                current_element = current_element.find_next_sibling()
            
            unique_tags = list(dict.fromkeys(tags))
            return unique_tags
        except requests.RequestException as e:
            print(f"Error fetching Appid: {e}")
            return []
    
    
    def _process_game_data(self, appid: str, response: Dict[str,Any]) -> Dict[str,Any]:
        """ 
            Collect only the important game data from response.
            Return: Dict containing important game information.
        """
        is_correct = self._check_game_response(appid, response)
        if not is_correct:
            return {}
        
        data = response[appid].get("data", {})
        
        recommendations = data["recommendations"].get("total", 0) if "recommendations" in data else 0
        release_date = data["release_date"].get("date","") if "release_date" in data else ""
        
        rating = data["ratings"].get("esrb","rp") if "ratings" in data and data["ratings"] != None else "rp"
        if rating != "rp":
            rating = rating.get("rating", "rp")
            
        detailed_description = self._strip_for_text(data.get("detailed_description", ""))
        
        process_data = {
            "appid": data.get("steam_appid", 0),
            "game_type": data.get("type", ""),
            "game_name": data.get("name", "Unknown"),
            "is_free": data.get("is_free", False),
            "detailed_description": detailed_description,
            "header_image": data.get("header_image", ""),
            "website": data.get("website", ""),
            "recommendations": recommendations,
            "release_date": release_date,
            "esrb_rating": rating,
            "developers": data.get("developers", []),
            "publishers": data.get("publishers", []),
            "categories": data.get("categories", []),
            "genres": data.get("genres", [])
        }
        
        process_data["price_overview"] = self._get_game_price(data)  
        process_data["metacritic"] = self._get_game_metacritic(data)
        
        process_data["tags"] = self.get_steam_tags(appid)
        
        screenshots = data.get('screenshots', [])
        if screenshots and len(screenshots) > 4:
            screenshots = screenshots[0:4]
        process_data["screenshots"] = [image['path_full'] for image in screenshots]
        
        
        return process_data
    
    def get_steam_tags(self, appid) -> List:
        tags = []
        try:
            wait_time = 1.6
            res = self.session.get(f"{self.STEAM_BASE_URL}{appid}")
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
            time.sleep(wait_time)
                    
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to retrieve tags from {self.STEAM_BASE_URL}{appid}!")
                
        return tags
    
    def _check_game_response(self, appid: str, response: Dict[str,Any]) -> bool:
        """ 
        Return: True if response contains correct keys
        """
        json_response = response[appid] if appid in response else {}
        if not json_response:
            logger.warning(f"Failed to retrieve GameId: {appid}!")
            return False
        
        is_successful = json_response.get("success", False)
        if not is_successful:
            logger.warning(f"GameId: {appid} failed to get game data!")
            return False
        
        data = json_response.get("data", {})
        if not data:
            logger.warning(f"GameId: {appid} has no game data!")
            return False
        
        return True
    
    def _get_game_price(self, data: Dict[str, Any]) -> Dict[str,Any]:
        """ 
        Return: Dict containing game's price info. Sets default price info is none is found.
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
           price = {
                "currency": price.get("currency", ""),
                "price_in_cents": price.get("final", 0), # price is returned in cents
                "final_formatted": price.get("final_formatted", ''),
                "discount_percentage": price.get("discount_percent", 0),
            }  
        return price
    
    def _get_game_metacritic(self, data: Dict[str, Any]) -> Dict[str,Any]:
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
    
    def _strip_for_text(self, text):
        # Remove HTML tags
        clean_text = re.sub(r'<.*?>', '', text)
        # Replace double quotes with single quotes
        text = text.replace('"', "'");
        # Replace HTML entities
        clean_text = clean_text.replace('&nbsp;', ' ')
        # Remove extra spaces and newlines
        clean_text = re.sub(r'\s+', ' ', clean_text)
        # Remove leading/trailing whitespace
        clean_text = clean_text.strip()
        return clean_text
    
    def get_appid_from_link(self, link: str) -> int | None:
        """
        Retrieves appid from steam link if there is one.

        Args:
            link (str): link to game's steam page

        Returns:
            int: appid of game
        """
        # Extract number after /app/
        appid = None
        match = re.search(r'/app/(\d+)', link)
        if match:
            appid = int(match.group(1))
                
        return appid