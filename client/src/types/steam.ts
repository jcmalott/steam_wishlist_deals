export interface SteamPlayer {
  steamid: string;
  communityvisibilitystate: number;
  profilestate: number;
  personaname: string;
  profileurl: string;
  avatar: string;
  avatarmedium: string;
  avatarfull: string;
  avatarhash: string;
  lastlogoff: number;
  personastate: number;
  realname?: string;
  primaryclanid?: string;
  timecreated?: number;
  personastateflags?: number;
  loccountrycode?: string;
  locstatecode?: string;
}

export interface Category {
  id: number;
  description: string;
}

export interface Genre {
  id: string;
  description: string;
}

export interface PriceOverview {
  currency: string;
  price_in_cents: number;
  final_formatted: string;
  discount_percentage: number;
}

export interface Metacritic {
  score: number;
  url: string;
}

export interface SteamGame {
  appid: number;
  game_type: string;
  game_name: string;
  is_free: boolean;
  detailed_description: string;
  header_image: string;
  website?: string;
  recommendations: number;
  release_date: string;
  esrb_rating: string;
  developers: string[];
  publishers: string[];
  categories: Category[];
  genres: Genre[];
  price_overview: PriceOverview;
  metacritic?: Metacritic;
  screenshots: string[];
  tags: string[];
}

export interface WishlistItem {
  steamid: number
  appid: number
  priority: number
}

export interface DealsGGPrices{
  retail_price: number;
  retail_price_low: number;
  keyshop_price: number;
  keyshop_price_low: number;
}
  
export interface DealsGGItem{
  appid: number;
  name: string;
  url: string;
  image_url: string;
  prices: DealsGGPrices;
  currency: string;
}