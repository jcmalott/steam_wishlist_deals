import React from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchUserLibrary } from "../api";
import type { LibraryItem, ListProps } from "../types/steam";
import DealsGG from "./DealsGG";

const Library = ({ steamId, maxPrice }: ListProps) => {
  const { data, isLoading, error } = useQuery<LibraryItem[]>({
    queryKey: ["steamUser", steamId],
    queryFn: () => fetchUserLibrary(steamId),
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  // Use appid to get games from dealsgg

  const game_appids = data?.map((game) => game.appid) || [];
  return <DealsGG appids={game_appids} maxPrice={maxPrice} />;
};

export default Library;
