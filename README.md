# AstroStats Discord Bot

AstroStats is an open-source Discord bot that provides game stats for League of Legends, Teamfight Tactics (TFT), Apex Legends, and Fortnite, as well as daily horoscopes. We welcome contributions from the community to enhance its features and functionality.

## Features

- **Pet Battles**
  - Summon your very own server pet and battle other server members to become top of the leaderboard! 

- **Game Stats:**

  - **League of Legends:** Get detailed statistics for any summoner.
  - **Teamfight Tactics (TFT):** View your match history and rankings.
  - **Apex Legends:** Retrieve player stats, including kills, level, and rank.
  - **Fortnite:** Check your wins, kills, and other game stats.

- **Horoscopes:**
  - Receive daily horoscopes for all zodiac signs.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Discord.py library
- Requests library

### Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/yourusername/AstroStats.git
   ```
2. Install the required libraries:
   ```sh
   pip install -r requirements.txt
   ```
3. Set up your Discord bot token and API keys in a `.env` file:
   ```env
   DISCORD_TOKEN=your_discord_token
   LOL_API_KEY=your_lol_api_key
   TFT_API_KEY=your_tft_api_key
   APEX_API_KEY=your_apex_api_key
   FORTNITE_API_KEY=your_fortnite_api_key
   ```

### Running the Bot

Run the bot using the following command:

```sh
python bot.py
```
