# https://www.exchangerate-api.com/docs/free
import requests
from helper import save_to_json, check_if_recent_save
import logging

from helper import load_from_json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# check time and if longer than a day, get new exchange rate and set new time
class ExchangeRates():
    EXCHANGE_RATES_URL = 'https://open.er-api.com/v6/latest/USD'
    FILENAME = 'data/exchange_rates.json'
    
    def __init__(self):
        """
        Retrieves daily exchanges rates for most common currencies compared to US dollar.
        """
        self.exchange_rates = {}
        self._get_exchange_rates()
        
        # Initialize session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ExchangeRates-Client/1.0',
            'Accept': 'application/json'
        })
    
    def get_price_dollar(self, price, currency):
        """ 
        Converts price to US dollar.
        
        Args:
            price: money value that is being converted
            currency: what exchange rate 
        """
        if price > 0 and currency != '':
            new_price = price/self.exchange_rates[currency] 
            return round(new_price, 2)
        
        return price
    
    
    def _get_exchange_rates(self):
        """ 
        Store most common exchange rates stored locally.
        """
        if not check_if_recent_save(self.FILENAME):
            response = self.session.get(self.EXCHANGE_RATES_URL)
    
            if response.status_code == 200:
                results = response.json()
                self.exchange_rates =  results["rates"]
                save_to_json(self.FILENAME, self.exchange_rates)
            else:
                return None
        else:
            self.exchange_rates = load_from_json(self.FILENAME)['data']
            logger.info(f"Exchange Rates have been stored within last 24 hours.")
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
    
    def close(self):
        """Close the session and cleanup resources."""
        if hasattr(self, 'session') and self.session:
            self.session.close()