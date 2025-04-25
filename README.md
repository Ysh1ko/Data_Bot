# Discord Data Bot

A multifunctional Discord bot built with Python, designed to fetch and visualize game-related data using Google Sheets and generate stylish response images.

## 🚀 Features

- 📊 **Google Sheets Integration**  
  Retrieves dynamic data based on user input (IDs, stats, etc.).

- 🖼️ **Image Output with Data Overlay**  = WORK IN PROGRESS


  Generates custom images displaying retrieved data using the PIL (Pillow) library.

- 🧠 **User ID Tracking**  
  Uses Redis to cache and associate user-specific IDs for easier access.

- 📉 **Custom Progress Bars**  = WORK IN PROGRESS
  Visualizes statistics like kill/dead ratios using dynamically generated progress bars.

- ⚙️ **Command-Based Interaction**  
  Easy-to-use commands like `top`, `stats` in Discord.

## 🛠️ Tech Stack

- Python 3.x  
- `discord.py`  
- Google Sheets API  
- Redis  
- Pillow (PIL)  
- QuickChart API (for chart rendering)

## ⚙️ Example Command Flow

1. User sends a command (e.g., `stat 12345`)
2. Bot saves the ID to Redis for the user.
3. Data is fetched from Google Sheets based on the ID.
4. A customized image is generated and returned via Discord.

## 🙏 Shout-out

Special thanks to the **original creator** of the base code that inspired this bot.  
This version expands and customizes the original.
https://github.com/sovanna/rok-discord-data

## 🔒 Notes

- API keys and secrets are **not** included in the repo.
- Use `.env` or `config.json` to store tokens securely.
