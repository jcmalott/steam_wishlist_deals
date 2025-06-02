import psycopg2 as pg2
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class SteamDatabase():
    """
        Database class to handle PostgreSQL connection and data operations for Steam Client
    """
    
    def __init__(self, database: str, user: str, password: str):
        """
            Initialize database connection
            
            Args:
                database: Name of the PostgreSQL database
                user: Database username
                password: Database password
        """
        self.conn = pg2.connect(database=database, user=user, password=password)
        # Allows enteraction with database
        self.cur = self.conn.cursor()

    def add_steam_user(self, user: Dict[str,Any]) -> bool:
        """
            Add Steam user to database if not already present
            
            Args:
                users: Dictionary containing Steam user account data   
            Returns: bool, False if user already exist
        """
        # checking to see if user exist, if so exit
        is_user = self._check_table_item('steamid','users', user['steamid'])
        if is_user:
            # user is already in db
            return False
        
        # fields within the database to be populated
        fields = ['steamid', 'persona_name', 'profile_url', 'avatar_full', 'real_name', 'country_code', 'state_code']
        self._insert_new_row('users', fields, [user])
        return True
    
    def get_wishlist(self, user_id: str)-> List[Dict[str,Any]]:
        fields = ['steamid', 'appid', 'priority']
        return self._search_db('steamid', user_id, fields, 'wishlist')
        
    def get_library(self, user_id: str)-> List[Dict[str,Any]]:
        fields = ['steamid', 'appid', 'playtime_minutes','user_paid_price']
        return self._search_db('steamid', user_id, fields, 'user_library')
    
    def get_game(self, appid: str)-> Dict[str,Any]:
        fields = ['game_type', 'game_name', 'is_free', 'detailed_description','header_image','website','recommendations','release_date','esrb_rating']
        item = self._search_db('appid', appid, fields, 'games')
        return item[0] if item else {}
    
    def get_developers(self, appid: str)-> List[Dict[str,Any]]:
        fields = ['developer_name']
        return self._search_db('appid', appid, fields, 'developers')
    
    def get_publishers(self, appid: str)-> List[Dict[str,Any]]:
        fields = ['publisher_name']
        return self._search_db('appid', appid, fields, 'publishers')
    
    def get_categories(self, appid: str)-> List[Dict[str, Any]]:
        fields = ['category_name']
        return self._search_db('appid', appid, fields, 'categories')
    
    def get_genres(self, appid: str):
        fields = ['genre_name']
        return self._search_db('appid', appid, fields, 'genres')
    
    def get_prices(self, appid: str):
        fields = ['currency','price_in_cents','final_formatted','discount_percentage']
        item = self._search_db('appid', appid, fields, 'prices')
        return item[0] if item else {}
    
    def get_metacritics(self, appid: str):
        fields = ['score','url']
        item = self._search_db('appid', appid, fields, 'metacritic')
        return item[0] if item else {}
    
    def _search_db(self, column: str, value, fields: List[str], table: str)-> List[Dict[str,Any]]:
        try:
            columns = ', '.join(fields)
            query = f"""
                SELECT {columns} FROM {table}
                WHERE {column} = '{value}';
            """
            
            self.cur.execute(query)
            items = self.cur.fetchall()
            
            # need to return in json format just like the server would
            items_dict = []
            for item in items:
                item_json = {}
                for index,field in enumerate(fields):
                    item_json[field] = item[index]
                
                items_dict.append(item_json) 
            
            logger.info(f"Database {table} {len(items_dict)} Fetched")
            return items_dict
        except pg2.Error as e:
            logger.error(f"ERROR: Database Fetching {table}: {e}")
            if self.conn:
                self.conn.rollback()
                
        return []  

    def check_update_status(self, user_id: str, column: str) -> bool:
        """
            Check if data needs to be called down from server or retrieved from database.
            A lot of calls to the server are needed to download wishlist and library game data.
            For this a week interval is set between download new data
            
            Args:
                user_id: Steam user ID
                column: Name of the column to check when last updated
                
            Returns: bool, True if data needs to be updated
        """
        # check if user has stored data already
        is_user = self._check_table_item('steamid', 'schedule_data_retrieval', user_id)
        # if no user than schedule update
        if is_user:
            try:
                # checks if a week has passed since last update
                query = f"""
                    SELECT needs_retrieval({column}) 
                    FROM schedule_data_retrieval 
                    WHERE steamid = '{user_id}';
                """
                
                self.cur.execute(query)
                first_item = self.cur.fetchone()
                # sometimes it gets return as a single item or tuple, even when its just one item
                first_item = first_item[0] if isinstance(first_item, tuple) else first_item
                return first_item
            except pg2.Error as e:
                logger.error(f"ERROR: Database Fetching Schedule: {e}")
                if self.conn:
                    self.conn.rollback()
                    
        return True
            
    def _check_table_item(self, column: str, table: str, item) -> bool:
        """
            Check if an item exists in a specific column of a table
            
            Args:
                column: Column name to check
                table: Table name to check
                item: Value to search for
                
            Returns: bool, indicating if item exists
        """
        try:
            self.cur.execute(f"SELECT {column} FROM {table} WHERE {column} = '{item}'")
            if self.cur.fetchone() is not None:
                logger.info(f"Found - Item: {item}, From Table: {table} Column {column}!")
                return True
            else:
                logger.warning(f"Doesn't Exist - Item: {item}, From Table: {table} Column {column}!")
        except pg2.Error as e:
            logger.error(f"ERROR - Database Selection: {e}")
            
        return False
        """
            Sets games_updated_at from table schedule_data_retrieval to current time and date.
            
            Note: This should be set after adding or updating multiple games from wishlist or library to DB.
                  A single server call is needed for each game, so user is advised to wait a certain amount of time before making multiple calls again.
                  reference function check_update_status 
            
            Args: user_id: Steam user ID   
            Returns: bool, True if data was updated, False if user_id doesn't exist in table or data wasn't set
        """
        # check if user has stored data already
        is_user = self._check_table_item('steamid', 'schedule_data_retrieval', user_id)
        # if no user than schedule update
        if is_user:
            try:
                # checks if a week has passed since last update
                query = f"""
                    UPDATE schedule_data_retrieval
                    SET games_updated_at = NOW()
                    WHERE steamid = '{user_id}'
                """
                
                self.cur.execute(query)
                return True
            except pg2.Error as e:
                logger.error(f"ERROR: Database setting games_updated_at failed: {e}")
                if self.conn:
                    self.conn.rollback()
        else:          
            return False