# AstroStats Discord Bot

[![Discord Bots](https://top.gg/api/widget/status/1088929834748616785.svg)](https://top.gg/bot/1088929834748616785)

AstroStats is a feature-rich Discord bot that helps you track gaming statistics for popular titles like Apex Legends, Fortnite, League of Legends, and Teamfight Tactics. Additionally, it offers fun mini-games and utilities to enhance your server experience.

## 📋 Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
- [Commands](#commands)
  - [Game Statistics](#game-statistics)
  - [Mini-Games](#mini-games)
  - [General Utilities](#general-utilities)
- [Self-Hosting](#self-hosting)
- [Support](#support)

## ✨ Features

### 🎮 Game Statistics
- **Apex Legends**: View player stats, including level, kills, damage, and rank
- **Fortnite**: Check season or lifetime stats, win rate, K/D, and match history
- **League of Legends**: Track summoner rankings, match history, and champion masteries
- **Teamfight Tactics**: View TFT rankings and match statistics

### 🐾 Mini-Games
- **Pet Battles**: Summon pets, train them, battle other users' pets, complete quests, and earn achievements
- **Squib Games**: Participate in multi-round elimination games with various mini-games

### 🔮 Utilities
- **Horoscope**: Get daily horoscope readings for all zodiac signs
- **Help System**: Detailed command help with examples

## 🚀 Getting Started

### Inviting the Bot

1. [Click here to invite AstroStats to your server](https://discord.com/oauth2/authorize?client_id=1088929834748616785&permissions=378944&integration_type=0&scope=bot+applications.commands)
2. Select the server where you want to add AstroStats
3. Authorize the required permissions
4. The bot will send a welcome message with getting started information

### Required Permissions

AstroStats requires the following permissions to function properly:
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Use External Emojis
- Add Reactions

## 🔍 Commands

AstroStats uses Discord's slash commands (`/`). Here's a breakdown of available commands:

### Game Statistics

#### Apex Legends
- `/apex <platform> <username>` - Check Apex Legends player stats
  - Platforms: Xbox, Playstation, Origin (PC)
  - Example: `/apex Origin (PC) Shroud`

#### Fortnite
- `/fortnite <time> <name>` - Check Fortnite player stats
  - Time: Season, Lifetime
  - Example: `/fortnite Season Ninja`

#### League of Legends
- `/league profile <region> <riotid>` - Check League of Legends player stats
  - Example: `/league profile EUW1 Faker#KR1`
- `/league championmastery <region> <riotid>` - View top 10 Champion Masteries
  - Example: `/league championmastery EUW1 Faker#KR1`

#### Teamfight Tactics
- `/tft <region> <riotid>` - Check TFT player stats
  - Example: `/tft EUW1 Player#0001`

### Mini-Games

#### Pet Battles
- `/petbattles summon <name> <pet>` - Summon a new pet
  - Available pets: Lion, Dog, Cat, Tiger, Rhino, Panda, Red Panda, Fox
  - Example: `/petbattles summon Fluffy Dog`
- `/petbattles stats` - View your pet's stats
- `/petbattles battle <opponent>` - Battle another user's pet
- `/petbattles quests` - View your current daily quests
- `/petbattles achievements` - View your achievements
- `/petbattles leaderboard` - View the top pets leaderboard
- `/petbattles vote` - Vote for the bot and earn rewards

#### Squib Games
- `/squibgames start` - Start a new multi-minigame Squib Game session
- `/squibgames run` - Run all minigame rounds until one winner remains
- `/squibgames status` - View the current Squib Game session status

### General Utilities

- `/help` - List all available commands
- `/horoscope <sign>` - Check your daily horoscope
- `/review` - Leave a review on Top.gg