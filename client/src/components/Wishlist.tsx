import React from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchUserWishlist } from "../api";
import type { WishlistItem, ListProps } from "../types/steam";
import DealsGG from "./DealsGG";

const Wishlist = ({ steamId, maxPrice }: ListProps) => {
  const { data, isLoading, error } = useQuery<WishlistItem[]>({
    queryKey: ["steamUser", steamId],
    queryFn: () => fetchUserWishlist(steamId),
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  // Use appid to get games from dealsgg

  const game_appids = data?.map((game) => game.appid) || [];
  return <DealsGG appids={game_appids} maxPrice={maxPrice} />;
};

export default Wishlist;
