import { useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { fetchDealsGG } from "../api";
import GameCard from "./GameCard";
import type { DealsGGItem } from "../types/steam";
import axios from "axios";

type SortKey = "found" | "price" | "discount" | "name";

const DealsGG = ({
  appids,
  maxPrice,
}: {
  appids: number[];
  maxPrice: number | null;
}) => {
  const BATCH_SIZE = 30;
  const MAX_BATCHES = 15;
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<SortKey>("found");
  const PAGE_SIZE = 20;
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  // Number of batches requested so far; grows only until enough games match.
  const [chunkCount, setChunkCount] = useState(1);

  const [prevReset, setPrevReset] = useState({ filter, sort, maxPrice, appids });
  if (
    prevReset.filter !== filter ||
    prevReset.sort !== sort ||
    prevReset.maxPrice !== maxPrice ||
    prevReset.appids !== appids
  ) {
    if (prevReset.appids !== appids) setChunkCount(1);
    setPrevReset({ filter, sort, maxPrice, appids });
    setVisibleCount(PAGE_SIZE);
  }

  const chunks = useMemo(() => {
    const results: number[][] = [];
    const limit = Math.min(appids.length, BATCH_SIZE * MAX_BATCHES);
    for (let i = 0; i < limit; i += BATCH_SIZE)
      results.push(appids.slice(i, i + BATCH_SIZE));
    return results;
  }, [appids]);

  const queries = useQueries({
    queries: chunks.slice(0, chunkCount).map((chunk) => ({
      queryKey: ["appids", chunk],
      queryFn: () => fetchDealsGG(chunk),
      staleTime: 5 * 60 * 1000,
      retry: (failureCount: number, error: unknown) => {
        if (axios.isAxiosError(error) && error.response?.status === 429)
          return false;
        return failureCount < 3;
      },
    })),
  });

  const loadedCount = queries.filter((q) => q.data).length;
  const isLoading = queries.some((q) => q.isLoading);
  const rateLimited = queries.some(
    (q) => axios.isAxiosError(q.error) && q.error.response?.status === 429,
  );

  const allData: DealsGGItem[] = useMemo(
    () => queries.flatMap((q) => q.data ?? []),
    [queries],
  );

  const totalRetail = allData.reduce(
    (sum, g) => sum + (g?.prices?.retail_price ?? 0),
    0,
  );
  const totalDeal = allData.reduce(
    (sum, g) =>
      sum + (g?.prices?.keyshop_price ?? g?.prices?.retail_price ?? 0),
    0,
  );
  const lowestDeal = allData.reduce((min, g) => {
    const p = g?.prices?.keyshop_price ?? g?.prices?.retail_price ?? Infinity;
    return p > 0 && p < min ? p : min;
  }, Infinity);

  const filtered = useMemo(() => {
    let list = allData.filter((g) => {
      if (
        filter !== "" &&
        !g?.name?.toLowerCase().includes(filter.toLowerCase())
      )
        return false;

      if (maxPrice !== null) {
        const retail = g?.prices?.retail_price ?? 0;
        const deal = g?.prices?.keyshop_price ?? 0;
        const belowOnSteam = retail > 0 && retail <= maxPrice;
        const belowOnDeals = deal > 0 && deal <= maxPrice;
        if (!belowOnSteam && !belowOnDeals) return false;
      }

      return true;
    });

    if (sort === "discount")
      list = list.sort((a, b) => {
        const deal_a = a?.prices?.keyshop_price ?? 0;
        const deal_b = b?.prices?.keyshop_price ?? 0;
        if (!deal_a && deal_b) return 1;
        if (deal_a && !deal_b) return -1;
        const discA =
          (a?.prices?.retail_price ?? 0) > 0
            ? (a.prices!.retail_price - deal_a) / a.prices!.retail_price
            : 0;
        const discB =
          (b?.prices?.retail_price ?? 0) > 0
            ? (b.prices!.retail_price - deal_b) / b.prices!.retail_price
            : 0;
        return discB - discA;
      });

    if (sort === "price")
      list = list.sort((a, b) => {
        const retail_a = a?.prices?.retail_price ?? 0;
        const deal_a = a?.prices?.keyshop_price ?? 0;
        const retail_b = b?.prices?.retail_price ?? 0;
        const deal_b = b?.prices?.keyshop_price ?? 0;
        const best_a = deal_a > 0 ? Math.min(retail_a, deal_a) : retail_a;
        const best_b = deal_b > 0 ? Math.min(retail_b, deal_b) : retail_b;
        return best_a - best_b;
      });

    if (sort === "name")
      list = list.sort((a, b) => (a?.name ?? "").localeCompare(b?.name ?? ""));

    return list;
  }, [allData, filter, sort, maxPrice]);

  const hasMoreBatches = chunkCount < chunks.length;
  const allSettled = queries.every((q) => q.isSuccess);
  if (hasMoreBatches && allSettled && filtered.length < visibleCount)
    setChunkCount(chunkCount + 1);

  return (
    <div>
      {isLoading && !rateLimited && (
        <>
          <div className="ds-status">
            Loading deals... {loadedCount} / {queries.length} batches
          </div>
          <div className="ds-progress-bar">
            <div
              className="ds-progress-fill"
              style={{ width: `${(loadedCount / queries.length) * 100}%` }}
            />
          </div>
        </>
      )}

      {rateLimited && (
        <div className="ds-rate-limit">
          Rate limited by DealsGG — showing {allData.length} games fetched so
          far.
        </div>
      )}

      {allData.length > 0 && (
        <div className="ds-stats">
          <div className="ds-stat">
            <span className="ds-stat-val">{allData.length}</span>{" "}
            <span className="ds-stat-lbl">games found</span>
          </div>
          {lowestDeal < Infinity && (
            <div className="ds-stat">
              <span className="ds-stat-val">${lowestDeal.toFixed(2)}</span>{" "}
              <span className="ds-stat-lbl">lowest deal</span>
            </div>
          )}
          <div className="ds-stat">
            <span className="ds-stat-val">${totalRetail.toFixed(2)}</span>{" "}
            <span className="ds-stat-lbl">total retail</span>
          </div>
          <div className="ds-stat">
            <span className="ds-stat-val">${totalDeal.toFixed(2)}</span>{" "}
            <span className="ds-stat-lbl">total if bought now</span>
          </div>
        </div>
      )}

      <div className="ds-controls">
        <input
          className="ds-filter"
          placeholder="Filter games..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        {(["price", "discount", "name"] as SortKey[]).map((s) => (
          <button
            key={s}
            className={`ds-sort-btn${sort === s ? " active" : ""}`}
            onClick={() => setSort(sort === s ? "found" : s)}
          >
            {s === "price"
              ? "Price ↑"
              : s === "discount"
                ? "Discount ↓"
                : "Name A–Z"}
          </button>
        ))}
      </div>

      <div className="ds-game-list">
        {filtered.slice(0, visibleCount).map((deal) => (
          <GameCard key={deal.appid} game={deal} />
        ))}
      </div>

      {(visibleCount < filtered.length || hasMoreBatches) && (
        <div className="ds-load-more">
          <button
            className="ds-sort-btn"
            disabled={isLoading}
            onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
          >
            Load More
          </button>
        </div>
      )}
    </div>
  );
};

export default DealsGG;
