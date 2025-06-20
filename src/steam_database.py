import psycopg2 as pg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Union
import logging
from contextlib import contextmanager
from psycopg2 import sql

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class SteamDatabase():
    """
        Database class to handle PostgreSQL connection and data operations for Steam Client
    """
    USERS_TABLE = 'users'
    WISHLIST_TABLE = 'wishlist'
    USER_LIBRARY_TABLE = 'user_library'
    GAMES_TABLE = 'games'
    DEVELOPERS_TABLE = 'developers'
    PUBLISHERS_TABLE = 'publishers'
    CATEGORIES_TABLE = 'categories'
    GENRES_TABLE = 'genres'
    PRICES_TABLE = 'prices'
    METACRITIC_TABLE = 'metacritic'
    SCHEDULE_TABLE = 'schedule_data_retrieval'
    
    def __init__(self, database: str, user: str, password: str):
        """
            Initialize database connection.
            All database data is pulled from steam api: https://api.steampowered.com
            
            Args:
                database: Name of the PostgreSQL database
                user: Database username
                password: Database password
        """
        if not all([database, user, password]):
            raise ValueError("Database name, user, and password are required")
        
        self.database = database
        self.user = user
        self.password = password
        self._connect()
            
    def _connect(self):
        try:
            self.conn = pg2.connect(database=self.database, user=self.user, password=self.password)
            # Allows enteraction with database
            self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        except pg2.Error as e:
            logger.error(f"Failed to connect database {self.database} for user {self.user}: {e}")
            
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if not self.conn or self.conn.closed:
            logger.warning("Database connection lost, reconnecting...")
            self._connect()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        self._ensure_connection()
        try:
            yield self.cur
            self.conn.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise

    def add_steam_user(self, user: Dict[str,Any]) -> bool:
        """
            Add Steam user to database if not already present
            
            Args:
                users: Dictionary containing Steam user account data   
            Returns: bool, False if user already exist
        """
        if not user or 'steamid' not in user:
            raise ValueError("User data must contain 'steamid'")
        
        # checking to see if user exist, if so exit
        is_user = self._check_table_item('steamid','users', user['steamid'])
        if is_user:
            # user is already in db
            return False
        
        # fields within the database to be populated
        fields = ['steamid', 'persona_name', 'profile_url', 'avatar_full', 'real_name', 'country_code', 'state_code']
        self._insert_new_row('users', fields, [user])
        return True
    
    def _insert_new_row(self, table: str, fields: List[str], rows: List[Dict[str, Any]]):
        """
        Insert new rows into a table using parameterized queries.
        
        Args:
            table: Table name
            fields: Field names
            rows: List of row data dictionaries
        """
        if not all([table, fields, rows]):
            return
        
        try:
            # Build parameterized insert query
            field_list = sql.SQL(', ').join(map(sql.Identifier, fields))
            placeholder_list = sql.SQL(', ').join(sql.Placeholder() * len(fields))
            
            query = sql.SQL("""
                INSERT INTO {table} ({fields}) VALUES ({placeholders})
            """).format(
                table=sql.Identifier(table),
                fields=field_list,
                placeholders=placeholder_list
            )
            
            # Execute for each row
            for row in rows:
                values = [row.get(field) for field in fields]
                self.cur.execute(query, values)
            
            logger.debug(f"Inserted {len(rows)} rows into {table}")
            
        except pg2.Error as e:
            logger.error(f"Failed to insert rows into {table}: {e}")
    
    def get_wishlist(self, user_id: str)-> List[Dict[str,Any]]:
        """
        Get user's steam wishlist from database.
        
        Args:
            user_id: Steam user ID
            
        Returns:
            List of wishlist items
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")
        fields = ['steamid', 'appid', 'priority']
        return self._search_db('steamid', user_id, fields, self.WISHLIST_TABLE)
        
    def get_library(self, user_id: str)-> List[Dict[str,Any]]:
        """
        Get user's steam game library from database.
        
        Args:
            user_id: Steam user ID
            
        Returns:
            List of library items
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")
        
        fields = ['steamid', 'appid', 'playtime_minutes','user_paid_price']
        return self._search_db('steamid', user_id, fields, self.USER_LIBRARY_TABLE)
    
    def get_game(self, appid: str)-> Dict[str,Any]:
        """
        Get games steam information from database.
        
        Args:
            appid: Steam app ID
            
        Returns:
            Game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        fields = ['game_type', 'game_name', 'is_free', 'detailed_description',
                  'header_image','website','recommendations','release_date','esrb_rating'
        ]
        item = self._search_db('appid', appid, fields, self.GAMES_TABLE)
        return item[0] if item else {}
    
    def get_developers(self, appid: str)-> List[Dict[str,Any]]:
        """
        Get game developers from database.
        
        Args:
            appid: Steam app ID
            
        Returns:
            Game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        fields = ['developer_name']
        return self._search_db('appid', appid, fields, self.DEVELOPERS_TABLE)
    
    def get_publishers(self, appid: str)-> List[Dict[str,Any]]:
        """
        Get game publishers from database.
        
        Args:
            appid: Steam app ID
            
        Returns:
            Game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        fields = ['publisher_name']
        return self._search_db('appid', appid, fields, self.PUBLISHERS_TABLE)
    
    def get_categories(self, appid: str)-> List[Dict[str, Any]]:
        """
        Get game categories from database.
        
        Args:
            appid: Steam app ID
            
        Returns:
            Game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        fields = ['category_name']
        return self._search_db('appid', appid, fields, self.CATEGORIES_TABLE)
    
    def get_genres(self, appid: str):
        """
        Get game genres from database.
        Args:
            appid: Steam app ID
            
        Returns:
            Game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        fields = ['genre_name']
        return self._search_db('appid', appid, fields, self.GENRES_TABLE)
    
    def get_prices(self, appid: str):
        """
        Get game pricing information from database.
        Args:
            appid: Steam app ID
            
        Returns:
            Game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        fields = ['currency','price_in_cents','final_formatted','discount_percentage']
        item = self._search_db('appid', appid, fields, self.PRICES_TABLE)
        return item[0] if item else {}
    
    def get_metacritics(self, appid: str):
        """
        Get metacritics information from database.
        Metacritic is a score, 0-100, given by reviewers of game.
        Args:
            appid: Steam app ID
            
        Returns:
            Game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        fields = ['score','url']
        item = self._search_db('appid', appid, fields, self.METACRITIC_TABLE)
        return item[0] if item else {}
    
    def get_complete_game_info(self, appid: Union[str, int]) -> Dict[str, Any]:
        """
        Get complete game information including all related data.
        
        Args:
            appid: Steam app ID
            
        Returns:
            Complete game information dictionary
        """
        if not appid:
            raise ValueError("App ID cannot be empty")
        
        game_info = self.get_game(appid)
        if not game_info:
            return {}
        
        # Add related information
        game_info['developers'] = self.get_developers(appid)
        game_info['publishers'] = self.get_publishers(appid)
        game_info['categories'] = self.get_categories(appid)
        game_info['genres'] = self.get_genres(appid)
        game_info['pricing'] = self.get_prices(appid)
        game_info['metacritic'] = self.get_metacritics(appid)
        
        return game_info
    
    def _search_db(self, column: str, value, fields: List[str], table: str)-> List[Dict[str,Any]]:
        """
        Search database with parameterized queries to prevent SQL injection.
        
        Args:
            column: Column to search in
            value: Value to search for
            fields: Fields to return
            table: Table to search in
            
        Returns:
            List of matching records
        """
        if not all([column, fields, table]):
            raise ValueError("Column, fields, and table are required")
        
        try:
            self._ensure_connection()
            
            field_list = sql.SQL(', ').join(map(sql.Identifier, fields))
            query = sql.SQL("""
                SELECT {fields} FROM {table}
                WHERE {column} = {value}
            """).format(
                fields=field_list,
                table=sql.Identifier(table),
                column=sql.Identifier(column),
                value=sql.Literal(value)
            )
            
            self.cur.execute(query)
            results = self.cur.fetchall()

            # Convert to list of dictionaries
            items_dict = [dict(row) for row in results]
            
            logger.debug(f"Found {len(items_dict)} records in {table}")
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
        if not user_id or not column:
            raise ValueError("User ID and column cannot be empty")
        
        try:
            # Check if user has scheduled data
            if not self._check_table_item('steamid', self.SCHEDULE_TABLE, user_id):
                logger.info(f"No schedule data found for user {user_id}, update needed")
                return True
            
            with self.transaction():
                # Use parameterized query to check if update is needed
                query = sql.SQL("""
                    SELECT needs_retrieval({column}) 
                    FROM {table} 
                    WHERE steamid = {steamid}
                """).format(
                    column=sql.Identifier(column),
                    table=sql.Identifier(self.SCHEDULE_TABLE),
                    steamid=sql.Placeholder()
                )
                
                self.cur.execute(query, (user_id,))
                result = self.cur.fetchone()
                
                if result:
                    needs_update = result[0] if isinstance(result, tuple) else result['needs_retrieval']
                    logger.info(f"Update status for user {user_id}: {needs_update}")
                    return bool(needs_update)
                
                return True
                
        except pg2.Error as e:
            logger.error(f"Failed to check update status for user {user_id}: {e}")
            # If we can't check, assume update is needed
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
        if not all([column, table]) or item is None:
            return False
        
        try:
            self._ensure_connection()
            
            query = sql.SQL("""
                SELECT 1 FROM {table} WHERE {column} = {item} LIMIT 1
            """).format(
                table=sql.Identifier(table),
                column=sql.Identifier(column),
                item=sql.Placeholder()
            )
            
            self.cur.execute(query, (item,))
            result = self.cur.fetchone()
            
            exists = result is not None
            logger.debug(f"Item {item} {'found' if exists else 'not found'} in {table}.{column}")
            return exists
            
        except pg2.Error as e:
            logger.error(f"Failed to check item existence: {e}")
            return False    
    
        # """
        #     Sets games_updated_at from table schedule_data_retrieval to current time and date.
            
        #     Note: This should be set after adding or updating multiple games from wishlist or library to DB.
        #           A single server call is needed for each game, so user is advised to wait a certain amount of time before making multiple calls again.
        #           reference function check_update_status 
            
        #     Args: user_id: Steam user ID   
        #     Returns: bool, True if data was updated, False if user_id doesn't exist in table or data wasn't set
        # """
        # # check if user has stored data already
        # is_user = self._check_table_item('steamid', 'schedule_data_retrieval', user_id)
        # # if no user than schedule update
        # if is_user:
        #     try:
        #         # checks if a week has passed since last update
        #         query = f"""
        #             UPDATE schedule_data_retrieval
        #             SET games_updated_at = NOW()
        #             WHERE steamid = '{user_id}'
        #         """
                
        #         self.cur.execute(query)
        #         return True
        #     except pg2.Error as e:
        #         logger.error(f"ERROR: Database setting games_updated_at failed: {e}")
        #         if self.conn:
        #             self.conn.rollback()
        # else:          
        #     return False
    
    def close(self):
        """Close database connection and cleanup resources."""
        try:
            if self.cur:
                self.cur.close()
                self.cur = None
            if self.conn:
                self.conn.close()
                self.conn = None
            logger.info("Database connection closed")
        except pg2.Error as e:
            logger.error(f"Error closing database connection: {e}")
               
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()