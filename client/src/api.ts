import axios from 'axios';

import type { SteamPlayer, SteamGame, WishlistItem, DealsGGItem } from './types/steam';

export const fetchSteamUser = async(steam_id: string): Promise<SteamPlayer> => {
    try {
        const res = await axios.get(`/api/steam/user/${steam_id}`);
        return res.data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            console.log('Status:', error.response?.status);
            console.log('Message:', error.response?.data.detail);
        }
        throw error;
    }
}

export const fetchSteamGame = async(appid: number): Promise<SteamGame> => {
    try {
        const res = await axios.get(`/api/steam/game/${appid}`);
        return res.data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            console.log('Status:', error.response?.status);
            console.log('Message:', error.response?.data.detail);
        }
        throw error;
    }
}

export const fetchSteamGames = async(appids: number[]): Promise<SteamGame[]> => {
    try {
        const res = await axios.post('/api/steam/games', { appids });
        return res.data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            console.log('Status:', error.response?.status);
            console.log('Message:', error.response?.data.detail);
        }
        throw error;
    }
}

export const fetchUserWishlist = async(steam_id: string): Promise<WishlistItem[]> => {
    try {
        const res = await axios.get(`/api/steam/user/wishlist/${steam_id}`);
        return res.data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            console.log('Status:', error.response?.status);
            console.log('Message:', error.response?.data.detail);
        }
        throw error;
    }
}

export const fetchDealsGG = async(appids: number[]): Promise<DealsGGItem[]> => {
    try {
        const res = await axios.post('/api/dealsgg/games', { appids });
        return res.data;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            console.log('Status:', error.response?.status);
            console.log('Message:', error.response?.data.detail);
        }
        throw error;
    }
}