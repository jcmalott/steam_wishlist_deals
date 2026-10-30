import type { DealsGGItem } from "../types/steam";

const GameCard = ({ game }: { game: DealsGGItem }) => {
  const retail = game?.prices?.retail_price ?? 0;
  const deal = game?.prices?.keyshop_price ?? 0;
  const hasDeal = deal > 0;
  const savings =
    hasDeal && retail > 0 ? Math.round(((retail - deal) / retail) * 100) : 0;
  const steamUrl = `https://store.steampowered.com/app/${game.appid}`;

  return (
    <div className="ds-card">
      <div className="ds-card-img">
        {game?.image_url ? (
          <img src={game.image_url} alt={game.name} />
        ) : (
          <span className="ds-card-img-placeholder">NO IMG</span>
        )}
      </div>

      <div className="ds-card-body">
        <div className="ds-card-name">{game?.name}</div>

        <div className="ds-card-row">
          <span className="ds-row-label">Steam</span>
          <span className="ds-price-val steam">${retail.toFixed(2)}</span>
          <a
            href={steamUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="ds-row-btn"
          >
            View →
          </a>
        </div>

        <div className={`ds-card-row${!hasDeal ? " no-deal" : ""}`}>
          <span className="ds-row-label">DealsGG</span>
          {hasDeal ? (
            <>
              <span className="ds-price-val best">${deal.toFixed(2)}</span>
              {savings > 0 && (
                <span className="ds-savings-badge">−{savings}%</span>
              )}
              <a
                href={game?.url}
                target="_blank"
                rel="noopener noreferrer"
                className="ds-row-btn"
              >
                View →
              </a>
            </>
          ) : (
            <span className="ds-no-deal">No deal found</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default GameCard;
