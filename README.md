# Clash of Clans Leaderboard Bot

The ultimate Discord bot that tracks your Clash of Clans clan members, monitors real-time trophy pushes, and generates interactive server leaderboards.

## 🛠️ Setup & Installation

**1. Get your Discord Token**
* Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
* Navigate to the **Bot** tab, enable the **Message Content Intent**, and copy your Bot Token.
* Go to the **OAuth2** -> **URL Generator** tab. Select the `bot` and `applications.commands` scopes.
* Grant the following text permissions: **Read Messages**, **Send Messages**, and **Embed Links**.
* Copy the generated URL to invite the bot to your server.

**2. Get your Clash of Clans API Key**
* Go to the [Clash of Clans Developer Site](https://developer.clashofclans.com/) and create an account.
* Click **Create New Key**.
* **Lunes Configuration:** On your Lunes panel, set your startup script to `bash startup.bash`. Grab the IP address from your server panel and paste it directly into the "Allowed IP Addresses" field on the CoC developer site.
* Create the key and copy the JWT token.

**3. Configure Environment Variables**
Create a file named `.env` in the same directory as your bot script and add your tokens:
```env
DISCORD_TOKEN=your_discord_bot_token_here
COC_TOKEN=your_clash_of_clans_api_token_here
```

**4. Run the Bot**
Upload your files to your Lunes host and start the server! (Dependencies are already handled in your discord.py environment).

---

## 💻 Slash Commands

| Command | Description |
|---------|-------------|
| `/setleaderboard` | Spawns the auto-refreshing leaderboard in the channel. |
| `/add <tag>` | Adds a specific player to the tracker. |
| `/add_clan <tag>` | Bulk imports all current members of a clan. |
| `/remove <tag>` | Removes a player from the tracker. |
| `/leaderboard` | Manually displays the current leaderboard instantly. |
| `/profile <tag>` | Shows a detailed stats card for any CoC player. |

*Note: The bot automatically creates and manages `players.json`, `lb_config.json`, and `trophy_cache.json` in its directory to store data.*
