import React from 'react'
import { useQuery } from "@tanstack/react-query"

import { fetchUserWishlist } from "../api"
import type { WishlistItem } from '../types/steam'
import DealsGG from "./DealsGG"

type WishlistProps = {
    steamId: string;
}

const Wishlist = ({steamId}: WishlistProps) => {
    const {data, isLoading, error} = useQuery<WishlistItem[]>({
            queryKey: ['steamUser', steamId],
            queryFn: () => fetchUserWishlist(steamId)
    })

    if (isLoading) return <div>Loading...</div>
    if (error) return <div>Error: {error.message}</div>

    // Use appid to get games from dealsgg

    const game_appids = data?.map(game => game.appid) || []
    return (
        <DealsGG appids={game_appids}/>
    )
}

export default Wishlist