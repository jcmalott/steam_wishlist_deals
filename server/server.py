import uvicorn
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import TypeAdapter, ValidationError
from contextlib import asynccontextmanager

from src.types.steam import SteamPlayer, SteamGame, Wishlist, AppIdsRequest, DealsGG
from src.steam_api import Steam
from src.dealsgg_api import DealsGGAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv()
STEAM_API_KEY = os.getenv('STEAM_API_KEY')
DEALS_API_KEY = os.getenv('DEALS_API_KEY')

@asynccontextmanager
async def lifespan(app: FastAPI):
    global steam, dealsgg
    steam = Steam(STEAM_API_KEY)
    dealsgg = DealsGGAPI(DEALS_API_KEY)
    
    yield
    await steam.aclose()
    await dealsgg.aclose()
    
app = FastAPI(lifespan=lifespan)  

@app.get('/api/steam/user/{steam_id}')
async def get_steam_user(steam_id: str):
    return await fetch_and_validate(
        fetch_func=lambda: steam.get_user_account(steam_id),
        validator=SteamPlayer,
        not_found_message='Steam User not found.',
        validation_error_message='Invalid data structure from Steam player API.'
    )
    
@app.get('/api/steam/game/{appid}')
async def get_steam_game(appid: str):
    return await fetch_and_validate(
        fetch_func=lambda: steam.get_game_data(int(appid)),
        validator=SteamGame,
        not_found_message='Steam Game not found.',
        validation_error_message='Invalid data structure from Steam game API.'
    )

wishlist_adapter = TypeAdapter(list[Wishlist])    
@app.get('/api/steam/user/wishlist/{steam_id}')
async def get_user_wishlist(steam_id: str):
    return await fetch_and_validate(
        fetch_func=lambda: steam.get_wishlist(steam_id),
        validator=wishlist_adapter,
        not_found_message='Wishlist not found.',
        validation_error_message='Invalid data structure from Steam wishlist API.'
    )
    
games_adapter = TypeAdapter(list[SteamGame])     
@app.post('/api/steam/games')
async def get_steam_games(request: AppIdsRequest):
    return await fetch_and_validate(
        fetch_func=lambda: steam.get_games_data(request.appids),
        validator=games_adapter,
        not_found_message='Steam Games not found.',
        validation_error_message='Invalid data structure from Steam games API.'
    )
    
deals_adapter = TypeAdapter(list[DealsGG])     
@app.post('/api/dealsgg/games')
async def get_dealsgg_games(request: AppIdsRequest):
    return await fetch_and_validate(
        fetch_func=lambda: dealsgg.find_products_by_appid(request.appids, max_price=5.00),
        validator=deals_adapter,
        not_found_message='No deals found.',
        validation_error_message='Invalid data structure from DealsGG API.'
    )

async def fetch_and_validate(fetch_func, validator, not_found_message: str, validation_error_message: str):    
    try:
        data = await fetch_func()
        if not data:
            raise HTTPException(status_code=404, detail=not_found_message)

        if hasattr(validator, 'validate_python'):
            return validator.validate_python(data)
        else:
            return validator(**data)
    
    except ValidationError as e:
        logger.error(f'Validation Error: {e}')
        raise HTTPException(status_code=502, detail=validation_error_message)
    
    except Exception as error:
        logger.error(f'Steam API Error: {error}')
        raise HTTPException(status_code=500, detail='Error fetching data from Steam API')

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 5000))
    logger.info(f'Server at http://localhost:{PORT}')
    # uvicorn.run("server:app", host='0.0.0.0', port=PORT, reload=True)
    uvicorn.run("server:app", host='0.0.0.0', port=PORT)