import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Wishlist from "./components/Wishlist";
import Library from "./components/Library";

const STEAM_ID = import.meta.env.VITE_STEAM_USER_ID;

type Mode = "wishlist" | "library";

function App() {
  const [steamId, setSteamId] = useState("");
  const [submittedId, setSubmittedId] = useState("");
  const [active, setActive] = useState(false);
  const [mode, setMode] = useState<Mode>("wishlist");
  const [maxPrice, setMaxPrice] = useState<number | "">("");

  const { isLoading: serverLoading, isError: serverDown } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("Server unavailable");
      return res.json();
    },
    retry: false,
  });

  const handleScan = () => {
    if (mode === "library") {
      setSubmittedId(STEAM_ID);
      setActive(true);
      return;
    }
    if (steamId.trim()) {
      setSubmittedId(steamId.trim());
      setActive(true);
    }
  };

  if (serverLoading)
    return (
      <div className="ds-app">
        <div className="ds-server-status checking">Connecting to server...</div>
      </div>
    );

  if (serverDown)
    return (
      <div className="ds-app">
        <div className="ds-server-status error">
          Server is offline. Start the backend and refresh.
        </div>
      </div>
    );

  return (
    <div className="ds-app">
      <header className="ds-header">
        <div className="ds-logo">
          DEAL<span>SCOUT</span>
        </div>
        <div className="ds-input-row">
          <div className="ds-mode-toggle">
            <button
              className={`ds-mode-btn${mode === "wishlist" ? " active" : ""}`}
              onClick={() => {
                setMode("wishlist");
                setActive(false);
              }}
            >
              Wishlist
            </button>
            <button
              className={`ds-mode-btn${mode === "library" ? " active" : ""}`}
              onClick={() => {
                setMode("library");
                setActive(false);
              }}
            >
              Unk's Library
            </button>
          </div>
          <input
            type="text"
            className="ds-steam-input"
            placeholder={
              mode === "library" ? "Using personal ID" : "Enter Steam ID..."
            }
            value={mode === "library" ? "" : steamId}
            onChange={(e) => mode === "wishlist" && setSteamId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleScan()}
            disabled={mode === "library"}
          />
          <input
            type="number"
            className="ds-steam-input"
            placeholder="Max price..."
            value={maxPrice}
            onChange={(e) =>
              setMaxPrice(e.target.value === "" ? "" : Number(e.target.value))
            }
            style={{ maxWidth: "120px" }}
            min={0}
            step={0.01}
          />
          <button
            className="ds-scan-btn"
            onClick={handleScan}
            disabled={mode === "wishlist" && !steamId.trim()}
          >
            SCAN
          </button>
        </div>
      </header>

      {active &&
        (mode === "wishlist" ? (
          <Wishlist
            steamId={submittedId}
            maxPrice={maxPrice === "" ? null : maxPrice}
          />
        ) : (
          <Library
            steamId={submittedId}
            maxPrice={maxPrice === "" ? null : maxPrice}
          />
        ))}
    </div>
  );
}

export default App;
