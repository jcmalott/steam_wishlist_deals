import React from 'react'
import { useQuery } from "@tanstack/react-query"

import type { SteamGame } from '../types/steam'
import { fetchSteamGames } from "../api"

const SteamGames = ({appids}: {appids: number[]}) => {
    const {data, isLoading, error} = useQuery<SteamGame[]>({
        queryKey: ['steamGames', appids],
        queryFn: () => fetchSteamGames(appids)
    })

    if (isLoading) return <div>Loading...</div>
    if (error) return <div>Error: {error.message}</div>

    return (
        <div>GamesCard</div>
    )
}

export default SteamGames