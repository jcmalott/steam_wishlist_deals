import React from 'react'

import type { DealsGGItem } from '../types/steam'


const GameCard = ({game}: {game: DealsGGItem}) => {
    return (
      <div className="w-full max-w-5xl mx-auto">
        <div className="border-4 border-black rounded-xl overflow-hidden shadow-2xl">
          <div className="flex items-center">
            {/* LEFT: Image */}
            <div className="px-6">
              <div className="h-40 border-2 border-black bg-gray-50 overflow-hidden">
                  {game?.image_url ? (
                  <img
                      src={game.image_url}
                      alt={game.name}
                      className="w-full h-full object-cover"
                  />
                  ) : (
                  <div className="w-full h-full flex items-center justify-center">
                      <span className="text-lg font-bold text-gray-400 uppercase tracking-wider">
                      Image
                      </span>
                  </div>
                  )}
              </div>
            </div>

            {/* MIDDLE: Game Name (takes remaining space) */}
            <div className="flex-1 px-8 py-10">
              <h2 className="text-3xl font-black text-center uppercase tracking-wider">
                {game?.name}
              </h2>
            </div>

            {/* RIGHT: Price Buttons (vertical stack) */}
            <div className="p-6 flex flex-col gap-1 w-1/4">
              {displayPriceButton("Retail", game?.prices?.retail_price)}
              {displayPriceButton("Keyshop", game?.prices?.keyshop_price)}
              <a href={game?.url} target="_blank"  rel="noopener noreferrer" className="mt-2 text-center bg-blue-600 text-white font-bold py-2 px-4 rounded hover:bg-blue-700">View Deal</a>
            </div>
          </div>
        </div>
      </div>
    )
}

function displayPriceButton(title: string, price: number = 0){
    return(
        <div className="flex gap-1">
            <div className=" border-2 border-black px-4 py-2 w-50">
                <span className="text-sm font-black uppercase tracking-wider">{title}</span>
            </div>
            <span className="flex justify-center items-center text-2xl font-bold w-50">{'$' + price.toFixed(2)}</span>
        </div>
    )
}

function covertToUSD(cents: number): string {
  return '$' + (cents / 100).toFixed(2)
}

export default GameCard;
