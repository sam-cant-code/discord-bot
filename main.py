import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
import json
import os
import time
import logging
import contextlib
import datetime
from dotenv import load_dotenv

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger('CoCBot')

load_dotenv()

PLAYERS_FILE = 'players.json'
CONFIG_FILE = 'lb_config.json'
TROPHY_CACHE_FILE = 'trophy_cache.json'
CUSTOM_COMMANDS_FILE = 'custom_commands.json'

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COC_TOKEN = os.getenv('COC_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

intents = discord.Intents.default()
intents.message_content = True

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

LEAGUE_WEIGHTS = {name: i for i, name in enumerate(LEAGUE_EMOJIS.keys(), start=1)}

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

# --- NON-BLOCKING FILE HELPERS ---
async def load_json_file(filepath, default):
    def _read():
        try:
            with open(filepath, 'r') as file:
                data = json.load(file)
                if not isinstance(data, type(default)):
                    return default
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return default
    return await asyncio.to_thread(_read)

async def save_json_file(filepath, data):
    def _write():
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
    await asyncio.to_thread(_write)

# --- MATH & FORMATTING HELPERS ---
def calc_legend_trophies(stars, destruction):
    """Calculates the exact trophies earned or lost in a Legend League battle."""
    if stars == 0:
        return destruction // 10
    elif stars == 1:
        return 5 + max(0, destruction - 1) // 9
    elif stars == 2:
        return 16 + max(0, destruction - 50) // 3
    elif stars == 3:
        return 40
    return 0

def to_superscript(num):
    """Converts a standard integer string to unicode superscript characters."""
    sup_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}
    return ''.join(sup_map.get(char, '') for char in str(num))

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

def get_league_emoji(league_name: str) -> str:
    return LEAGUE_EMOJIS.get(league_name, "➖")

def get_league_weight(league_name: str) -> int:
    return LEAGUE_WEIGHTS.get(league_name, 0)

# --- PERMISSION CHECK ---
def is_admin_or_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == OWNER_ID:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        return False
    return app_commands.check(predicate)

# --- REUSABLE API FETCH LOGIC ---
async def safe_fetch(session, url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=10) as r:
                if r.status == 429:
                    delay = 2 ** attempt
                    logger.warning(f"Rate limited (429) on API. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                data = None
                if r.status == 200:
                    data = await r.json()
                return r.status, data
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Network error on fetch: {e}")
            await asyncio.sleep(1)
    return None, None

async def fetch_league_history(session, tag, headers):
    hist_url = f"https://api.clashofclans.com/v1/players/%23{tag}/leaguehistory"
    status, hist_data = await safe_fetch(session, hist_url, headers)
    
    l_name = "Unranked"
    if status == 200 and hist_data:
        items = hist_data.get('items', [])
        if items:
            latest_item = sorted(items, key=lambda x: str(x.get('season', '')))[-1]
            tier_id = latest_item.get('leagueTierId', 0)
            l_name = TIER_ID_TO_NAME.get(tier_id, "Unranked")
    elif status != 200 and status is not None:
        logger.warning(f"History API returned {status} for #{tag}. Falling back to Unranked.")
        
    return l_name

async def fetch_player_data(session, tag, headers, trophy_cache, semaphore=None):
    async with (semaphore or contextlib.nullcontext()):
        await asyncio.sleep(0.1)
        
        url = f"https://api.clashofclans.com/v1/players/%23{tag}"
        status, d = await safe_fetch(session, url, headers)
        
        if status == 200 and d:
            th = d.get('townHallLevel', 1)
            current_trophies = d.get('trophies', 0)

            await asyncio.sleep(0.1)
            
            l_name = await fetch_league_history(session, tag, headers)
            weight = get_league_weight(l_name)
            
            # --- FETCH DAILY LEGEND STATS IF APPLICABLE ---
            legend_log = None
            if weight == 34:  # 34 is the weight for Legend League
                log_url = f"https://api.clashofclans.com/v1/players/%23{tag}/battlelog"
                log_status, log_data = await safe_fetch(session, log_url, headers)
                
                if log_status == 403:
                    legend_log = "private"
                elif log_status == 200 and log_data:
                    off_count, off_trophies, def_count, def_trophies = 0, 0, 0, 0
                    
                    # Legend League day resets at 05:00 AM UTC
                    now = datetime.datetime.utcnow()
                    if now.hour >= 5:
                        day_start = now.replace(hour=5, minute=0, second=0, microsecond=0)
                    else:
                        day_start = (now - datetime.timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                        
                    for battle in log_data.get('items', []):
                        if battle.get('battleType') == 'legend':
                            b_time_str = battle.get('battleTime')
                            is_today = False
                            
                            if b_time_str:
                                try:
                                    clean_time = b_time_str.replace('Z', '')
                                    if '.' in clean_time:
                                        clean_time = clean_time.split('.')[0]
                                    b_dt = datetime.datetime.strptime(clean_time, "%Y%m%dT%H%M%S")
                                    is_today = b_dt >= day_start
                                except Exception:
                                    is_today = True 
                            else:
                                is_today = True 
                                
                            if is_today:
                                is_attack = battle.get('attack', False)
                                stars = battle.get('stars', 0)
                                dest = battle.get('destructionPercentage', 0)
                                trophies = calc_legend_trophies(stars, dest)
                                
                                if is_attack and off_count < 8:
                                    off_trophies += trophies
                                    off_count += 1
                                elif not is_attack and def_count < 8:
                                    def_trophies += trophies
                                    def_count += 1
                                    
                            if b_time_str and not is_today:
                                break
                    
                    legend_log = {
                        'off_count': off_count, 'off_trophies': off_trophies,
                        'def_count': def_count, 'def_trophies': def_trophies
                    }

            player_dict = {
                'name':          discord.utils.escape_markdown(d.get('name', 'Unknown')),
                'trophies':      current_trophies,
                'emoji':         get_league_emoji(l_name),
                'league_weight': weight,
                'th':            th,
                'tag':           tag,
                'delta':         get_delta_str(tag, current_trophies, trophy_cache),
                'legend_log':    legend_log
            }
            return player_dict, tag, current_trophies, d
        else:
            logger.warning(f"Profile API returned {status} for #{tag}.")
            
        return None, tag, None, None

# --- LEADERBOARD BUILDER ---
async def build_leaderboard_embeds(bot):
    players = await load_json_file(PLAYERS_FILE, [])

    if not players:
        embed = discord.Embed(
            title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}",
            description="The server leaderboard is empty. Ask an admin to use `/add` or `/add_clan` to track someone.",
            color=discord.Color.gold()
        )
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text="Page 1/1 | Last Refreshed")
        return [embed]

    trophy_cache = await load_json_file(TROPHY_CACHE_FILE, {})
    new_cache = {}
    data_list = []
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}
    
    semaphore = asyncio.Semaphore(3)

    fetch_tasks = [fetch_player_data(bot.session, tag, headers, trophy_cache, semaphore) for tag in players]
    results = await asyncio.gather(*fetch_tasks)

    for player_dict, tag, current_trophies, _ in results:
        if player_dict:
            data_list.append(player_dict)
            new_cache[tag] = current_trophies

    await save_json_file(TROPHY_CACHE_FILE, new_cache)

    data_list.sort(key=lambda x: (x['league_weight'], x['trophies']), reverse=True)

    embeds = []
    chunk_size = 20
    total_pages = max(1, (len(data_list) + chunk_size - 1) // chunk_size)

    for i in range(0, max(1, len(data_list)), chunk_size):
        chunk = data_list[i:i + chunk_size]
        desc = ""
        for j, p in enumerate(chunk, start=i + 1):
            profile_url = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={p['tag']}"
            
            # Base text with main trophy number bolded
            line = f"**{j}.** {p['emoji']} [**{p['name']}**]({profile_url}) | **{p['trophies']}** {TROPHY_EMOJI}{p['delta']}"
            
            # Append Legend League daily tracking inline if applicable
            if p.get('league_weight') == 34:
                ll = p.get('legend_log')
                if ll == "private":
                    line += " | 🔒 Private"
                elif isinstance(ll, dict):
                    sup_off = to_superscript(ll['off_count'])
                    sup_def = to_superscript(ll['def_count'])
                    line += f" |  +{ll['off_trophies']}{sup_off} |  -{ll['def_trophies']}{sup_def}"
                    
            desc += line + "\n"

        embed = discord.Embed(
            title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}",
            description=desc,
            color=discord.Color.gold()
        )
        embed.timestamp = discord.utils.utcnow()
        current_page = (i // chunk_size) + 1
        embed.set_footer(text=f"Page {current_page}/{total_pages} | Last Refreshed")
        embeds.append(embed)

    return embeds

# --- INTERACTIVE VIEW ---
class LeaderboardView(discord.ui.View):
    def __init__(self, bot, embeds=None, current_page=0, message_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.embeds = embeds
        self.current_page = current_page
        self.message_id = message_id
        self.cooldown_seconds = 300
        
        if self.embeds:
            self.update_buttons()

    async def ensure_embeds(self, interaction: discord.Interaction):
        if not self.embeds:
            await interaction.response.defer()
            self.embeds = await build_leaderboard_embeds(self.bot)
            
            try:
                original_msg = await interaction.channel.fetch_message(interaction.message.id)
                footer = original_msg.embeds[0].footer.text
                page_str = footer.split('|')[0].strip().split(' ')[1]
                self.current_page = int(page_str.split('/')[0]) - 1
            except Exception:
                self.current_page = 0
                
            self.current_page = min(max(0, self.current_page), len(self.embeds) - 1)
            self.update_buttons()

    def update_buttons(self):
        if self.embeds:
            self.prev_button.disabled = self.current_page <= 0
            self.next_button.disabled = self.current_page >= len(self.embeds) - 1

    def save_state(self, interaction):
        msg_id = self.message_id or interaction.message.id
        self.bot.lb_pages[msg_id] = self.current_page

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="lb_prev_btn")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.ensure_embeds(interaction)
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        self.save_state(interaction)
        
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple, emoji="🔄", custom_id="refresh_lb_btn")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_time = time.time()

        if current_time - self.bot.last_refresh_time < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - (current_time - self.bot.last_refresh_time))
            minutes, seconds = divmod(remaining, 60)
            await interaction.response.send_message(
                f"⏳ The leaderboard was just updated! Please wait **{minutes}m {seconds}s** before refreshing again.",
                ephemeral=True
            )
            return

        if self.embeds:
            loading_embed = self.embeds[self.current_page].copy()
            loading_embed.set_footer(text="⏳ Fetching latest data from Clash of Clans API, please wait...")
        else:
            loading_embed = discord.Embed(
                title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}",
                description="⏳ Fetching latest data from Clash of Clans API, please wait...",
                color=discord.Color.gold()
            )
        
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(embed=loading_embed, view=self)
        
        self.bot.last_refresh_time = current_time
        new_embeds = await build_leaderboard_embeds(self.bot)
        
        self.embeds = new_embeds
        self.current_page = min(self.current_page, len(self.embeds) - 1)
        
        for child in self.children:
            child.disabled = False
        self.update_buttons()
        self.save_state(interaction)
        
        await interaction.edit_original_response(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="lb_next_btn")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.ensure_embeds(interaction)
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        self.update_buttons()
        self.save_state(interaction)
        
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


# --- BOT CLASS & SETUP ---
class CoCBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.session = None
        self.last_refresh_time = 0.0
        self.manual_lb_messages = {}
        self.lb_pages = {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.add_view(LeaderboardView(self))
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
    logger.info(f'Logged in as {bot.user.name} with Async Requests & Slash Commands!')

# --- CUSTOM COMMANDS LISTENER ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.content.startswith(bot.command_prefix):
        cmd_name = message.content[len(bot.command_prefix):].split(' ')[0].lower()
        custom_cmds = await load_json_file(CUSTOM_COMMANDS_FILE, {})
        guild_id = str(message.guild.id) if message.guild else None
        
        if guild_id and guild_id in custom_cmds:
            if cmd_name in custom_cmds[guild_id]:
                await message.channel.send(custom_cmds[guild_id][cmd_name])
                return

    await bot.process_commands(message)

# --- BACKGROUND TASK ---
@tasks.loop(minutes=60)
async def auto_update_leaderboard():
    config = await load_json_file(CONFIG_FILE, {})
    channel_id = config.get("channel_id")
    message_id = config.get("message_id")

    if not channel_id or not message_id:
        return

    channel = bot.get_channel(channel_id)
    if channel:
        try:
            message = await channel.fetch_message(message_id)
            embeds = await build_leaderboard_embeds(bot)
            bot.last_refresh_time = time.time()

            current = bot.lb_pages.get(message_id, 0)
            current = min(current, len(embeds) - 1)

            view = LeaderboardView(bot, embeds, current_page=current, message_id=message_id)
            await message.edit(embed=embeds[current], view=view)
            logger.info("Auto-updated background leaderboard successfully.")
        except discord.NotFound:
            logger.warning("Leaderboard message not found. Clearing config.")
            await save_json_file(CONFIG_FILE, {})
        except Exception as e:
            logger.error(f"Failed to auto-update leaderboard: {e}", exc_info=True)

# --- SLASH COMMANDS ---

@bot.tree.command(name='setleaderboard', description="Set up the automated updating leaderboard in this channel.")
@is_admin_or_owner()
async def set_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    config = await load_json_file(CONFIG_FILE, {})
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

    embeds = await build_leaderboard_embeds(bot)
    bot.last_refresh_time = time.time()
    
    view = LeaderboardView(bot, embeds)
    lb_message = await interaction.channel.send(embed=embeds[0], view=view)

    view.message_id = lb_message.id
    bot.lb_pages[lb_message.id] = 0

    await save_json_file(CONFIG_FILE, {
        "channel_id": interaction.channel_id,
        "message_id": lb_message.id
    })

    await interaction.followup.send("✅ Automated leaderboard successfully set up in this channel!", ephemeral=True)


@bot.tree.command(name='add', description="Add a Clash of Clans player to the tracker.")
@app_commands.describe(player_tag="The in-game tag of the player (with or without #)")
@is_admin_or_owner()
async def add_player(interaction: discord.Interaction, player_tag: str):
    await interaction.response.defer(ephemeral=True)

    clean_tag = player_tag.strip().lstrip('#').upper()
    url = f"https://api.clashofclans.com/v1/players/%23{clean_tag}"
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}

    status, data = await safe_fetch(interaction.client.session, url, headers)
    
    if status == 200 and data:
        players = await load_json_file(PLAYERS_FILE, [])
        if clean_tag not in players:
            players.append(clean_tag)
            await save_json_file(PLAYERS_FILE, players)
            await interaction.followup.send(f"✅ Added **{data.get('name')}** to the server tracker!")
        else:
            await interaction.followup.send("⚠️ Player is already in the server tracker.")
    else:
        await interaction.followup.send("❌ Player not found or API is rate-limiting. Double check the tag and try again.")


@bot.tree.command(name='add_clan', description="Add all members of a Clash of Clans clan to the tracker.")
@app_commands.describe(clan_tag="The in-game tag of the clan (with or without #)")
@is_admin_or_owner()
async def add_clan(interaction: discord.Interaction, clan_tag: str):
    await interaction.response.defer(ephemeral=True)

    clean_tag = clan_tag.strip().lstrip('#').upper()
    url = f"https://api.clashofclans.com/v1/clans/%23{clean_tag}"
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}

    status, data = await safe_fetch(interaction.client.session, url, headers)
    
    if status == 200 and data:
        members = data.get('memberList', [])
        clan_name = data.get('name', 'Unknown Clan')

        players = await load_json_file(PLAYERS_FILE, [])
        added_count = 0

        for member in members:
            member_tag = member.get('tag', '').lstrip('#').upper()
            if member_tag and member_tag not in players:
                players.append(member_tag)
                added_count += 1

        if added_count > 0:
            await save_json_file(PLAYERS_FILE, players)
            await interaction.followup.send(f"✅ Successfully added **{added_count}** new members from **{clan_name}** to the server tracker!")
        else:
            await interaction.followup.send(f"⚠️ All members of **{clan_name}** are already in the tracker.")
    else:
        await interaction.followup.send("❌ Clan not found or API is rate-limiting. Double check the clan tag and try again.")


@bot.tree.command(name='remove', description="Remove a player from the server tracker.")
@app_commands.describe(player_tag="The in-game tag of the player (with or without #)")
@is_admin_or_owner()
async def remove_player(interaction: discord.Interaction, player_tag: str):
    await interaction.response.defer(ephemeral=True)

    clean_tag = player_tag.strip().lstrip('#').upper()
    players = await load_json_file(PLAYERS_FILE, [])

    if clean_tag in players:
        players.remove(clean_tag)
        await save_json_file(PLAYERS_FILE, players)
        await interaction.followup.send(f"🗑️ Removed **#{clean_tag}** from the server tracker.")
    else:
        await interaction.followup.send("⚠️ Player is not currently in the server tracker.")


@bot.tree.command(name='leaderboard', description="Manually fetch the current server leaderboard.")
@app_commands.checks.cooldown(1, 300, key=lambda i: i.guild_id)
async def command_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    if interaction.channel_id in bot.manual_lb_messages:
        try:
            old_msg = await interaction.channel.fetch_message(bot.manual_lb_messages[interaction.channel_id])
            await old_msg.delete()
        except Exception:
            pass

    embeds = await build_leaderboard_embeds(bot)
    bot.last_refresh_time = time.time()
    
    view = LeaderboardView(bot, embeds)
    msg = await interaction.followup.send(embed=embeds[0], view=view, wait=True)
    
    bot.manual_lb_messages[interaction.channel_id] = msg.id
    view.message_id = msg.id
    bot.lb_pages[msg.id] = 0


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

    clean_tag = player_tag.strip().lstrip('#').upper()
    headers = {'Authorization': f'Bearer {COC_TOKEN}'}
    
    player_dict, _, _, raw_data = await fetch_player_data(
        interaction.client.session, clean_tag, headers, {}, semaphore=None
    )

    if raw_data:
        clan = raw_data.get('clan', {}).get('name', 'No Clan')
        role = raw_data.get('role', 'Member').capitalize() if raw_data.get('clan') else 'N/A'

        embed = discord.Embed(title=f"{player_dict['emoji']} {raw_data.get('name')} (TH{player_dict['th']})", color=discord.Color.blue())
        embed.add_field(name="Clan", value=f"{clan} ({role})", inline=False)
        embed.add_field(name="Trophies", value=f"{TROPHY_EMOJI} {raw_data.get('trophies')} (Best: {raw_data.get('bestTrophies')})", inline=True)
        embed.add_field(name="War Stars", value=f"⭐ {raw_data.get('warStars')}", inline=True)
        embed.add_field(name="Attacks Won", value=f"⚔️ {raw_data.get('attackWins')}", inline=True)
        embed.set_footer(text=f"Tag: #{clean_tag}")

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Could not find that player, or the API is currently unavailable.")

# --- CUSTOM COMMANDS MANAGEMENT ---

@bot.tree.command(name='add_command', description="Create a custom text command (e.g. !hello).")
@app_commands.describe(command_name="The trigger word (without the !)", response="What the bot should say")
@is_admin_or_owner()
async def add_custom_command(interaction: discord.Interaction, command_name: str, response: str):
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild_id)
    cmd_name = command_name.lower().strip()
    
    if " " in cmd_name:
        await interaction.followup.send("❌ Command name cannot contain spaces.", ephemeral=True)
        return

    custom_cmds = await load_json_file(CUSTOM_COMMANDS_FILE, {})
    
    if guild_id not in custom_cmds:
        custom_cmds[guild_id] = {}
        
    custom_cmds[guild_id][cmd_name] = response
    
    await save_json_file(CUSTOM_COMMANDS_FILE, custom_cmds)
    await interaction.followup.send(f"✅ Added custom command **!{cmd_name}**!\n**Response:** {response}")

@bot.tree.command(name='remove_command', description="Delete a custom text command.")
@app_commands.describe(command_name="The trigger word to delete (without the !)")
@is_admin_or_owner()
async def remove_custom_command(interaction: discord.Interaction, command_name: str):
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild_id)
    cmd_name = command_name.lower().strip()
    
    custom_cmds = await load_json_file(CUSTOM_COMMANDS_FILE, {})
    
    if guild_id in custom_cmds and cmd_name in custom_cmds[guild_id]:
        del custom_cmds[guild_id][cmd_name]
        await save_json_file(CUSTOM_COMMANDS_FILE, custom_cmds)
        await interaction.followup.send(f"🗑️ Successfully removed the **!{cmd_name}** command.")
    else:
        await interaction.followup.send(f"⚠️ Could not find a custom command named **!{cmd_name}**.")

@bot.tree.command(name='list_commands', description="List all custom text commands for this server.")
async def list_custom_commands(interaction: discord.Interaction):
    await interaction.response.defer()
    
    guild_id = str(interaction.guild_id)
    custom_cmds = await load_json_file(CUSTOM_COMMANDS_FILE, {})
    
    if guild_id in custom_cmds and custom_cmds[guild_id]:
        commands_list = "\n".join([f"• **!{cmd}**" for cmd in custom_cmds[guild_id].keys()])
        embed = discord.Embed(title="📜 Server Custom Commands", description=commands_list, color=discord.Color.green())
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("This server doesn't have any custom commands set up yet.")

# Global Error Handler for Custom Check
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("⛔ You do not have permission to use this command. It is restricted to Server Admins and the Bot Owner.", ephemeral=True)
    else:
        logger.error(f"App command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)