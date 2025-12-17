import { useQuery } from "@tanstack/react-query"

// import { fetchSteamUser, fetchSteamGame, fetchUserWishlist } from "./api"
// import type { SteamPlayer, SteamGame, Wishlist } from './types/steam'
// import GameCard from "./components/GameCard";
import { useState } from "react";
import Wishlist from "./components/Wishlist";

const STEAM_ID = import.meta.env.VITE_STEAM_USER_ID

function App() {
  // const {data, isLoading, error} = useQuery<SteamPlayer>({
  //   queryKey: ['steamUser', STEAM_ID],
  //   queryFn: () => fetchSteamUser(STEAM_ID)
  // })

    const [steamId, setSteamId] = useState(STEAM_ID)
    const [displayWishlist, setDisplayWishlist] = useState(false)

    const handleEnterKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && steamId.trim()) {
            setDisplayWishlist(true)
        }
    }
  
    return (
        <div className="py-12 w-full max-w-5xl mx-auto">
            <input 
                type="number" 
                placeholder="Steam ID"
                value={steamId}
                onChange={e => setSteamId(e.target.value)}
                onKeyDown={handleEnterKey}
                className="ml-auto block w-1/4 p-2 text-right border-white border"/>
            {displayWishlist && (
                <Wishlist
                    steamId={steamId}
                />
            )}
        </div>
    )
}

export default App
