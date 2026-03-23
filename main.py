import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

PLAYERS_FILE = 'players.json'
CONFIG_FILE = 'lb_config.json'
TROPHY_CACHE_FILE = 'trophy_cache.json'
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COC_TOKEN = os.getenv('COC_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

# --- GLOBAL VARIABLES ---
LAST_REFRESH_TIME = 0.0  
manual_lb_messages = {}
CACHED_EMBEDS = []

# --- CUSTOM EMOJIS ---
TROPHY_EMOJI = "<:Trophy:1485318298445938740>"

# --- LEAGUE EMOJI MAPPER ---
LEAGUE_EMOJIS = {
    "Skeleton League 1": "<:skeleton_league_1:1485297995376361482>",
    "Skeleton League 2": "<:skeleton_league_2:1485297999998357816>",
    "Skeleton League 3": "<:skeleton_league_3:1485298004138266764>",
    "Barbarian League 4": "<:barbarian_league_4:1485298008999596172>",
    "Barbarian League 5": "<:barbarian_league_5:1485298014171037746>",
    "Barbarian League 6": "<:barbarian_league_6:1485298018080133162>",
    "Archer League 7": "<:archer_league_7:1485298022152667198>",
    "Archer League 8": "<:archer_league_8:1485298026410016951>",
    "Archer League 9": "<:archer_league_9:1485298030919028736>",
    "Wizard League 10": "<:wizard_league_10:1485298036111311050>",
    "Wizard League 11": "<:wizard_league_11:1485298040838426817>",
    "Wizard League 12": "<:wizard_league_12:1485298046362456136>",
    "Valkyrie League 13": "<:valkyrie_league_13:1485298051433238538>",
    "Valkyrie League 14": "<:valkyrie_league_14:1485298056172929034>",
    "Valkyrie League 15": "<:valkyrie_league_15:1485298060975411225>",
    "Witch League 16": "<:witch_league_16:1485298066322882733>",
    "Witch League 17": "<:witch_league_17:1485298072127930438>",
    "Witch League 18": "<:witch_league_18:1485298076519497970>",
    "Golem League 19": "<:golem_league_19:1485298081179238501>",
    "Golem League 20": "<:golem_league_20:1485298084983607366>",
    "Golem League 21": "<:golem_league_21:1485298089202941972>",
    "P.E.K.K.A League 22": "<:pekka_league_22:1485298092545675369>",
    "P.E.K.K.A League 23": "<:pekka_league_23:1485298097532829916>",
    "P.E.K.K.A League 24": "<:pekka_league_24:1485298102767452170>",
    "Titan League 25": "<:titan_league_25:1485298109981397163>",
    "Titan League 26": "<:titan_league_26:1485298115006300291>",
    "Titan League 27": "<:titan_league_27:1485298118416269425>",
    "Dragon League 28": "<:dragon_league_28:1485298122505846958>",
    "Dragon League 29": "<:dragon_league_29:1485298126935031958>",
    "Dragon League 30": "<:dragon_league_30:1485298131863077104>",
    "Electro League 31": "<:electro_league_31:1485298134958735360>",
    "Electro League 32": "<:electro_league_32:1485298138066714794>",
    "Electro League 33": "<:electro_league_33:1485298142776918126>",
    "Legend League": "<:legend_league:1485298146186625205>"
}

# Dynamically map each league to a numerical value based on its order above
LEAGUE_WEIGHTS = {name: i for i, name in enumerate(LEAGUE_EMOJIS.keys(), start=1)}

# --- TIER ID MAPPER ---
TIER_ID_TO_NAME = {
    105000001: "Skeleton League 1", 105000002: "Skeleton League 2", 105000003: "Skeleton League 3",
    105000004: "Barbarian League 4", 105000005: "Barbarian League 5", 105000006: "Barbarian League 6",
    105000007: "Archer League 7", 105000008: "Archer League 8", 105000009: "Archer League 9",
    105000010: "Wizard League 10", 105000011: "Wizard League 11", 105000012: "Wizard League 12",
    105000013: "Valkyrie League 13", 105000014: "Valkyrie League 14", 105000015: "Valkyrie League 15",
    105000016: "Witch League 16", 105000017: "Witch League 17", 105000018: "Witch League 18",
    105000019: "Golem League 19", 105000020: "Golem League 20", 105000021: "Golem League 21",
    105000022: "P.E.K.K.A League 22", 105000023: "P.E.K.K.A League 23", 105000024: "P.E.K.K.A League 24",
    105000025: "Titan League 25", 105000026: "Titan League 26", 105000027: "Titan League 27",
    105000028: "Dragon League 28", 105000029: "Dragon League 29", 105000030: "Dragon League 30",
    105000031: "Electro League 31", 105000032: "Electro League 32", 105000033: "Electro League 33",
    105000034: "Legend League"
}

# --- FILE HELPERS ---
def load_players():
    try:
        with open(PLAYERS_FILE, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                return []
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_players(players):
    with open(PLAYERS_FILE, 'w') as file:
        json.dump(players, file, indent=4)

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file, indent=4)

def load_trophy_cache():
    try:
        with open(TROPHY_CACHE_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_trophy_cache(cache):
    with open(TROPHY_CACHE_FILE, 'w') as file:
        json.dump(cache, file, indent=4)

def get_delta_str(tag, current_trophies, cache):
    if tag not in cache:
        return ""
    cached_val = cache[tag]
    if not isinstance(cached_val, int):
        return ""
    diff = current_trophies - cached_val
    if diff > 0:
        return f" `▲ +{diff}`"
    if diff < 0:
        return f" `▼ {diff}`"
    return ""

def normalize_league_name(league_name: str) -> str:
    """
    Since we only use tier ID mapping now, this simply ensures
    we return the league_name if it exists in LEAGUE_EMOJIS.
    """
    if league_name in LEAGUE_EMOJIS:
        return league_name
    return league_name

def get_league_emoji(league_name: str) -> str:
    return LEAGUE_EMOJIS.get(normalize_league_name(league_name), "➖")

def get_league_weight(league_name: str) -> int:
    return LEAGUE_WEIGHTS.get(normalize_league_name(league_name), 0)

# --- ASYNC API FETCH HELPER ---
async def fetch_player_data(session, tag, headers, trophy_cache):
    url = f"https://api.clashofclans.com/v1/players/%23{tag}"
    async with session.get(url, headers=headers) as r:
        if r.status == 200:
            d = await r.json()
            th = d.get('townHallLevel', 1)
            current_trophies = d.get('trophies', 0)

            # ALWAYS fetch league history
            hist_url = f"https://api.clashofclans.com/v1/players/%23{tag}/leaguehistory"
            l_name = "Unranked"

            async with session.get(hist_url, headers=headers) as hist_r:
                if hist_r.status == 200:
                    hist_data = await hist_r.json()
                    items = hist_data.get('items', [])
                    
                    if items:
                        # Optional Upgrade: Rank players by their best achieved tier
                        tier_id = max(item.get('leagueTierId', 0) for item in items)
                        if tier_id in TIER_ID_TO_NAME:
                            l_name = TIER_ID_TO_NAME[tier_id]

            # ---------------------------------------------------------------
            # DEBUG — logs every player's normalized API name and weight
            # ---------------------------------------------------------------
            normalized = normalize_league_name(l_name)
            weight     = get_league_weight(l_name)
            print(
                f"[DEBUG] {d.get('name', tag)!r:25} | "
                f"normalized: {normalized!r:25} | "
                f"weight: {weight}"
            )
            # ---------------------------------------------------------------

            player_dict = {
                'name':          discord.utils.escape_markdown(d.get('name', 'Unknown')),
                'trophies':      current_trophies,
                'emoji':         get_league_emoji(l_name),
                'league_weight': weight,
                'th':            th,
                'tag':           tag,
                'delta':         get_delta_str(tag, current_trophies, trophy_cache)
            }
            return player_dict, tag, current_trophies
    return None, tag, None

# --- LEADERBOARD BUILDER ---
async def build_leaderboard_embeds(session):
    global CACHED_EMBEDS
    players = load_players()

    if not players:
        embed = discord.Embed(
            title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}",
            description="The server leaderboard is empty. Ask an admin to use `/add` or `/add_clan` to track someone.",
            color=discord.Color.gold()
        )
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text="Page 1/1 | Last Refreshed")
        CACHED_EMBEDS = [embed]
        return CACHED_EMBEDS

    trophy_cache = load_trophy_cache()
    new_cache = {}
    data_list = []
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}

    fetch_tasks = [fetch_player_data(session, tag, headers, trophy_cache) for tag in players]
    results = await asyncio.gather(*fetch_tasks)

    for player_dict, tag, current_trophies in results:
        if player_dict:
            data_list.append(player_dict)
            new_cache[tag] = current_trophies

    save_trophy_cache(new_cache)

    # Sort primarily by league weight, then trophies as tiebreaker
    data_list.sort(key=lambda x: (x['league_weight'], x['trophies']), reverse=True)

    embeds = []
    chunk_size = 20
    total_pages = max(1, (len(data_list) + chunk_size - 1) // chunk_size)

    for i in range(0, max(1, len(data_list)), chunk_size):
        chunk = data_list[i:i + chunk_size]
        desc = ""
        for j, p in enumerate(chunk, start=i + 1):
            profile_url = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={p['tag']}"
            desc += f"**{j}.** {p['emoji']} [**{p['name']}**]({profile_url}) | {p['trophies']} {TROPHY_EMOJI}{p['delta']} | TH{p['th']}\n"

        embed = discord.Embed(
            title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}",
            description=desc,
            color=discord.Color.gold()
        )
        embed.timestamp = discord.utils.utcnow()
        current_page = (i // chunk_size) + 1
        embed.set_footer(text=f"Page {current_page}/{total_pages} | Last Refreshed")
        embeds.append(embed)

    CACHED_EMBEDS = embeds
    return CACHED_EMBEDS

# --- INTERACTIVE VIEW ---
class LeaderboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def get_current_page(self, interaction: discord.Interaction) -> int:
        try:
            footer = interaction.message.embeds[0].footer.text
            page_str = footer.split('|')[0].strip().split(' ')[1]
            return int(page_str.split('/')[0]) - 1
        except Exception:
            return 0

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="lb_prev_btn")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global CACHED_EMBEDS
        if not CACHED_EMBEDS:
            CACHED_EMBEDS = await build_leaderboard_embeds(interaction.client.session)
        current = self.get_current_page(interaction)
        new_page = max(0, current - 1)
        await interaction.response.edit_message(embed=CACHED_EMBEDS[new_page], view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple, emoji="🔄", custom_id="refresh_lb_btn")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global LAST_REFRESH_TIME, CACHED_EMBEDS
        current_time = time.time()
        cooldown_seconds = 300

        if current_time - LAST_REFRESH_TIME < cooldown_seconds:
            remaining = int(cooldown_seconds - (current_time - LAST_REFRESH_TIME))
            minutes, seconds = divmod(remaining, 60)
            await interaction.response.send_message(
                f"⏳ The leaderboard was just updated! Please wait **{minutes}m {seconds}s** before refreshing again.",
                ephemeral=True
            )
            return

        LAST_REFRESH_TIME = current_time
        await interaction.response.defer()
        CACHED_EMBEDS = await build_leaderboard_embeds(interaction.client.session)
        current = self.get_current_page(interaction)
        new_page = min(current, len(CACHED_EMBEDS) - 1)
        await interaction.edit_original_response(embed=CACHED_EMBEDS[new_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="lb_next_btn")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global CACHED_EMBEDS
        if not CACHED_EMBEDS:
            CACHED_EMBEDS = await build_leaderboard_embeds(interaction.client.session)
        current = self.get_current_page(interaction)
        new_page = min(len(CACHED_EMBEDS) - 1, current + 1)
        await interaction.response.edit_message(embed=CACHED_EMBEDS[new_page], view=self)


# --- BOT CLASS & SETUP ---
class CoCBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.session = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.add_view(LeaderboardView())
        await self.tree.sync()
        if not auto_update_leaderboard.is_running():
            auto_update_leaderboard.start()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = CoCBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} with Async Requests & Slash Commands!')

# --- BACKGROUND TASK ---
@tasks.loop(minutes=60)
async def auto_update_leaderboard():
    global LAST_REFRESH_TIME, CACHED_EMBEDS
    config = load_config()
    channel_id = config.get("channel_id")
    message_id = config.get("message_id")

    if not channel_id or not message_id:
        return

    channel = bot.get_channel(channel_id)
    if channel:
        try:
            message = await channel.fetch_message(message_id)
            CACHED_EMBEDS = await build_leaderboard_embeds(bot.session)
            LAST_REFRESH_TIME = time.time()

            try:
                footer = message.embeds[0].footer.text
                page_str = footer.split('|')[0].strip().split(' ')[1]
                current = int(page_str.split('/')[0]) - 1
                current = min(current, len(CACHED_EMBEDS) - 1)
            except Exception:
                current = 0

            await message.edit(embed=CACHED_EMBEDS[current], view=LeaderboardView())
        except discord.NotFound:
            save_config({})
        except Exception as e:
            print(f"Failed to update leaderboard: {e}")

# --- SLASH COMMANDS ---

@bot.tree.command(name='setleaderboard', description="Set up the automated updating leaderboard in this channel.")
@app_commands.default_permissions(administrator=True)
async def set_leaderboard(interaction: discord.Interaction):
    global LAST_REFRESH_TIME, CACHED_EMBEDS

    await interaction.response.defer(ephemeral=True)

    config = load_config()
    old_channel_id = config.get("channel_id")
    old_message_id = config.get("message_id")

    if old_channel_id and old_message_id:
        old_channel = bot.get_channel(old_channel_id)
        if old_channel:
            try:
                old_msg = await old_channel.fetch_message(old_message_id)
                await old_msg.delete()
            except Exception:
                pass

    CACHED_EMBEDS = await build_leaderboard_embeds(interaction.client.session)
    LAST_REFRESH_TIME = time.time()

    lb_message = await interaction.channel.send(embed=CACHED_EMBEDS[0], view=LeaderboardView())

    save_config({
        "channel_id": interaction.channel_id,
        "message_id": lb_message.id
    })

    await interaction.followup.send("✅ Automated leaderboard successfully set up in this channel!", ephemeral=True)


@bot.tree.command(name='add', description="Add a Clash of Clans player to the tracker.")
@app_commands.describe(player_tag="The in-game tag of the player (with or without #)")
@app_commands.default_permissions(administrator=True)
async def add_player(interaction: discord.Interaction, player_tag: str):
    await interaction.response.defer(ephemeral=True)

    clean_tag = player_tag.strip().lstrip('#')
    url = f"https://api.clashofclans.com/v1/players/%23{clean_tag}"
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}

    async with interaction.client.session.get(url, headers=headers) as r:
        if r.status == 200:
            data = await r.json()
            players = load_players()
            if clean_tag not in players:
                players.append(clean_tag)
                save_players(players)
                await interaction.followup.send(f"✅ Added **{data.get('name')}** to the server tracker!")
            else:
                await interaction.followup.send("⚠️ Player is already in the server tracker.")
        else:
            await interaction.followup.send("❌ Player not found in Clash of Clans. Double check the tag.")


@bot.tree.command(name='add_clan', description="Add all members of a Clash of Clans clan to the tracker.")
@app_commands.describe(clan_tag="The in-game tag of the clan (with or without #)")
@app_commands.default_permissions(administrator=True)
async def add_clan(interaction: discord.Interaction, clan_tag: str):
    await interaction.response.defer(ephemeral=True)

    clean_tag = clan_tag.strip().lstrip('#')
    url = f"https://api.clashofclans.com/v1/clans/%23{clean_tag}"
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}

    async with interaction.client.session.get(url, headers=headers) as r:
        if r.status == 200:
            data = await r.json()
            members = data.get('memberList', [])
            clan_name = data.get('name', 'Unknown Clan')

            players = load_players()
            added_count = 0

            for member in members:
                member_tag = member.get('tag', '').lstrip('#')
                if member_tag and member_tag not in players:
                    players.append(member_tag)
                    added_count += 1

            if added_count > 0:
                save_players(players)
                await interaction.followup.send(f"✅ Successfully added **{added_count}** new members from **{clan_name}** to the server tracker!")
            else:
                await interaction.followup.send(f"⚠️ All members of **{clan_name}** are already in the tracker.")
        else:
            await interaction.followup.send("❌ Clan not found. Double check the clan tag.")


@bot.tree.command(name='remove', description="Remove a player from the server tracker.")
@app_commands.describe(player_tag="The in-game tag of the player (with or without #)")
@app_commands.default_permissions(administrator=True)
async def remove_player(interaction: discord.Interaction, player_tag: str):
    await interaction.response.defer(ephemeral=True)

    clean_tag = player_tag.strip().lstrip('#')
    players = load_players()

    if clean_tag in players:
        players.remove(clean_tag)
        save_players(players)
        await interaction.followup.send(f"🗑️ Removed **#{clean_tag}** from the server tracker.")
    else:
        await interaction.followup.send("⚠️ Player is not currently in the server tracker.")


@bot.tree.command(name='leaderboard', description="Manually fetch the current server leaderboard.")
@app_commands.checks.cooldown(1, 300, key=lambda i: i.guild_id)
async def command_leaderboard(interaction: discord.Interaction):
    global LAST_REFRESH_TIME, manual_lb_messages, CACHED_EMBEDS

    await interaction.response.defer()

    if interaction.channel_id in manual_lb_messages:
        try:
            old_msg = await interaction.channel.fetch_message(manual_lb_messages[interaction.channel_id])
            await old_msg.delete()
        except Exception:
            pass

    CACHED_EMBEDS = await build_leaderboard_embeds(interaction.client.session)
    LAST_REFRESH_TIME = time.time()

    msg = await interaction.followup.send(embed=CACHED_EMBEDS[0], view=LeaderboardView(), wait=True)
    manual_lb_messages[interaction.channel_id] = msg.id

@command_leaderboard.error
async def command_leaderboard_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes, seconds = divmod(int(error.retry_after), 60)
        await interaction.response.send_message(
            f"⏳ The leaderboard command is on cooldown! Try again in **{minutes}m {seconds}s**.",
            ephemeral=True
        )


@bot.tree.command(name='profile', description="Look up a specific Clash of Clans player profile.")
@app_commands.describe(player_tag="The in-game tag of the player (with or without #)")
async def player_profile(interaction: discord.Interaction, player_tag: str):
    await interaction.response.defer()

    clean_tag = player_tag.strip().lstrip('#')
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}
    url = f"https://api.clashofclans.com/v1/players/%23{clean_tag}"

    async with interaction.client.session.get(url, headers=headers) as r:
        if r.status == 200:
            d = await r.json()
            th = d.get('townHallLevel', 1)

            # Replaced fallback logic with the new leaguehistory fetch
            hist_url = f"https://api.clashofclans.com/v1/players/%23{clean_tag}/leaguehistory"
            l_name = "Unranked"

            async with interaction.client.session.get(hist_url, headers=headers) as hist_r:
                if hist_r.status == 200:
                    hist_data = await hist_r.json()
                    items = hist_data.get('items', [])
                    if items:
                        tier_id = max(item.get('leagueTierId', 0) for item in items)
                        if tier_id in TIER_ID_TO_NAME:
                            l_name = TIER_ID_TO_NAME[tier_id]

            emoji = get_league_emoji(l_name)
            clan = d.get('clan', {}).get('name', 'No Clan')
            role = d.get('role', 'Member').capitalize() if d.get('clan') else 'N/A'

            embed = discord.Embed(title=f"{emoji} {d.get('name')} (TH{th})", color=discord.Color.blue())
            embed.add_field(name="Clan", value=f"{clan} ({role})", inline=False)
            embed.add_field(name="Trophies", value=f"{TROPHY_EMOJI} {d.get('trophies')} (Best: {d.get('bestTrophies')})", inline=True)
            embed.add_field(name="War Stars", value=f"⭐ {d.get('warStars')}", inline=True)
            embed.add_field(name="Attacks Won", value=f"⚔️ {d.get('attackWins')}", inline=True)
            embed.set_footer(text=f"Tag: #{clean_tag}")

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Could not find that player. Make sure the tag is correct!")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)