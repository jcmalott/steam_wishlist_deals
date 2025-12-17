import React, { useMemo } from 'react'
import { useQueries, useQuery } from "@tanstack/react-query"

import { fetchDealsGG } from "../api"
import type { DealsGGItem } from '../types/steam'
import GameCard from './GameCard'

const DealsGG = ({appids}: {appids: number[]}) => {
    const BATCH_SIZE = 50;

    const chunks = useMemo(() => {
        const results = [];
        for (let i = 0; i < appids.length; i += BATCH_SIZE) {
            results.push(appids.slice(i, i + BATCH_SIZE));
        }
        return results;
    }, [appids]);

    const queries = useQueries({
        queries: chunks.map((chunk, index) => ({
            queryKey: ['appids', chunk],
            queryFn: () => fetchDealsGG(chunk),
            staleTime: 5 * 60 * 1000, // Cache for 5 minutes
        }))
    })
    
    const isLoading = queries.some(q => q.isLoading)
    const errors = queries.filter(q => q.error).map(q => q.error)
    const allData = queries
        .filter(q => q.data)
        .flatMap(q => q.data!)
    
    if (isLoading) {
        const loadedCount = queries.filter(q => q.data).length
        return <div>Loading deals... {loadedCount}/{chunks.length} batches loaded</div>
    }
    
    if (errors.length > 0) {
        return <div>Error loading some deals: {errors[0]?.message}</div>
    }

    return (
        <div>{allData?.map(deal => <GameCard key={deal.appid} game={deal}/>)}</div>
    )
}

export default DealsGG