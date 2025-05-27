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
        self.exchange_rates = {}
        self._get_exchange_rates()
    
    # TODO: Throw error for incorrect exchange rate
    def get_price_dollar(self, price, currency):
        # if it is then make the conversion, or return the orginal price
        if price > 0 and currency != '':
            new_price = price/self.exchange_rates[currency] 
            return round(new_price, 2)
        
        return price
    
    
    def _get_exchange_rates(self):
        if not check_if_recent_save(self.FILENAME):
            response = requests.get(self.EXCHANGE_RATES_URL)
    
            if response.status_code == 200:
                results = response.json()
                self.exchange_rates =  results["rates"]
                save_to_json(self.FILENAME, self.exchange_rates)
            else:
                return None
        else:
            self.exchange_rates = load_from_json(self.FILENAME)['data']
            logger.info(f"Exchange Rates have been stored within last 24 hours.")