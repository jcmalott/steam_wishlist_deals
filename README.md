# Steam Deals

Allows users with a Steam account to view deals for games on their wishlist or library.<br>
https://store.steampowered.com/account/

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)

## Installation

Clone repo. <br>
Open a terminal to the file location you want to install the project.
```bash
git clone https://github.com/jcmalott/steam_wishlist_deals.git
cd steam_wishlist_deals
npm install
```

## Usage

To run the application in default mode, displaying user wishlist deals, in the terminal within the project location.

```python
py main.py
```

This will open a Gradio web application.
![Main Screen](images/initial-screen.jpg)

For testing purposes, my default Steam ID will be displayed; alternatively, you can also enter your ID. <br>
To start the search for deals, click within the ID box and hit Enter. <br>
The application will need to retrieve your wishlist from Steam and search each game individually. Steam only allows
looking up a single game at a time.

Once ready, all deals will be displayed.
![Deals Screen](images/wishlist-deals.jpg)

A drop-down search bar is displayed at the top for displaying a single game. <br>
From top to bottom.
- Current Best Deal
- The cheapest price it sold for
- Steam's current price
- Cheapest price sold on Steam

Click the GG Deams button to take you to that deal. <br>
![Best Deal](images/gg-deals.jpg)
Click the Steam button to go to that game's Steam page.
![Steam Page](images/steam-page.jpg)
