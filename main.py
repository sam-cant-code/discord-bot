import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp, asyncio, json, os, time, logging, contextlib, datetime, io, random
from dotenv import load_dotenv

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger('CoCBot')
load_dotenv()

PLAYERS_FILE, CONFIG_FILE, TROPHY_CACHE_FILE = 'players.json', 'lb_config.json', 'trophy_cache.json'
LEGEND_STATS_FILE, SUPERWHOO_FILE = 'legend_stats.json', 'superwhoo_stats.json'
NAME_CACHE_FILE = 'name_cache.json'
GIVEAWAY_FILE = 'giveaways.json'

# --- AUTOMATIC FILE CREATOR ---
def ensure_files_exist():
    files_with_defaults = {
        PLAYERS_FILE: [],
        CONFIG_FILE: {},
        TROPHY_CACHE_FILE: {},
        LEGEND_STATS_FILE: {},
        SUPERWHOO_FILE: {},
        NAME_CACHE_FILE: {},
        GIVEAWAY_FILE: {}
    }
    for filepath, default_data in files_with_defaults.items():
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump(default_data, f, indent=4)
            logger.info(f"Created missing configuration file: {filepath}")

ensure_files_exist()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COC_TOKEN = os.getenv('COC_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))
COC_HEADERS = {'Authorization': f'Bearer {COC_TOKEN}'}

intents = discord.Intents.default()
intents.message_content = True

TROPHY_EMOJI = "<:Trophy:1485318298445938740>"

# --- EMOJI & LEAGUE MAPPERS ---
LEAGUE_EMOJIS = {
    "Skeleton League 1": "<:skeleton_league_1:1485297995376361482>", "Skeleton League 2": "<:skeleton_league_2:1485297999998357816>", "Skeleton League 3": "<:skeleton_league_3:1485298004138266764>",
    "Barbarian League 4": "<:barbarian_league_4:1485298008999596172>", "Barbarian League 5": "<:barbarian_league_5:1485298014171037746>", "Barbarian League 6": "<:barbarian_league_6:1485298018080133162>",
    "Archer League 7": "<:archer_league_7:1485298022152667198>", "Archer League 8": "<:archer_league_8:1485298026410016951>", "Archer League 9": "<:archer_league_9:1485298030919028736>",
    "Wizard League 10": "<:wizard_league_10:1485298036111311050>", "Wizard League 11": "<:wizard_league_11:1485298040838426817>", "Wizard League 12": "<:wizard_league_12:1485298046362456136>",
    "Valkyrie League 13": "<:valkyrie_league_13:1485298051433238538>", "Valkyrie League 14": "<:valkyrie_league_14:1485298056172929034>", "Valkyrie League 15": "<:valkyrie_league_15:1485298060975411225>",
    "Witch League 16": "<:witch_league_16:1485298066322882733>", "Witch League 17": "<:witch_league_17:1485298072127930438>", "Witch League 18": "<:witch_league_18:1485298076519497970>",
    "Golem League 19": "<:golem_league_19:1485298081179238501>", "Golem League 20": "<:golem_league_20:1485298084983607366>", "Golem League 21": "<:golem_league_21:1485298089202941972>",
    "P.E.K.K.A League 22": "<:pekka_league_22:1485298092545675369>", "P.E.K.K.A League 23": "<:pekka_league_23:1485298097532829916>", "P.E.K.K.A League 24": "<:pekka_league_24:1485298102767452170>",
    "Titan League 25": "<:titan_league_25:1485298109981397163>", "Titan League 26": "<:titan_league_26:1485298115006300291>", "Titan League 27": "<:titan_league_27:1485298118416269425>",
    "Dragon League 28": "<:dragon_league_28:1485298122505846958>", "Dragon League 29": "<:dragon_league_29:1485298126935031958>", "Dragon League 30": "<:dragon_league_30:1485298131863077104>",
    "Electro League 31": "<:electro_league_31:1485298134958735360>", "Electro League 32": "<:electro_league_32:1485298138066714794>", "Electro League 33": "<:electro_league_33:1485298142776918126>",
    "Legend League 3": "<:legend_league:1485298146186625205>",
    "Legend League 2": "<:legend_league:1485298146186625205>",
    "Legend League 1": "<:legend_league:1485298146186625205>"
}

LEAGUE_WEIGHTS = {name: i for i, name in enumerate(LEAGUE_EMOJIS.keys(), start=1)}

TIER_ID_TO_NAME = {
    105000001: "Skeleton League 1", 105000034: "Legend League"
}
for i in range(1, 34): TIER_ID_TO_NAME[105000000 + i] = list(LEAGUE_EMOJIS.keys())[i-1]

# --- FILE HELPERS ---
async def load_json_file(filepath, default):
    def _read():
        try:
            with open(filepath, 'r') as f: data = json.load(f)
            return data if isinstance(data, type(default)) else default
        except: return default
    return await asyncio.to_thread(_read)

async def save_json_file(filepath, data):
    def _write():
        with open(filepath, 'w') as f: json.dump(data, f, indent=4)
    await asyncio.to_thread(_write)

# --- AUTOCOMPLETE & RESOLUTION ---
async def resolve_player_input(input_str: str) -> str:
    if not input_str: return None
    clean_input = input_str.strip()
    name_cache = await load_json_file(NAME_CACHE_FILE, {})
    for tag, name in name_cache.items():
        if clean_input.lower() == name.lower(): return tag
    return clean_input.lstrip('#').upper()

async def player_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    name_cache = await load_json_file(NAME_CACHE_FILE, {})
    return [app_commands.Choice(name=f"{name} (#{tag})", value=tag) for tag, name in name_cache.items()
            if current.lower() in name.lower() or current.lower() in tag.lower()][:25]

# --- FORMATTING HELPERS ---
def format_name_strict(name, max_width=10):
    if name and name.lower() == "sam": return "/Sam\\"
    safe_name = name.replace('`', "'")
    return (safe_name[:max_width - 2] + "..").ljust(max_width) if len(safe_name) > max_width else safe_name.ljust(max_width)

def to_superscript(num):
    return ''.join({'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}.get(c, '') for c in str(num))

def calc_legend_trophies(stars, dest):
    return dest // 10 if stars == 0 else 5 + max(0, dest - 1) // 9 if stars == 1 else 16 + max(0, dest - 50) // 3 if stars == 2 else 40 if stars == 3 else 0

def get_delta_str(tag, current, cache):
    diff = current - cache.get(tag, current) if isinstance(cache.get(tag), int) else 0
    return f" `▲ +{diff}`" if diff > 0 else f" `▼ {diff}`" if diff < 0 else ""

def is_admin_or_owner():
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

# --- API CORE ---
async def safe_fetch(session, url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=10) as r:
                if r.status == 429:
                    await asyncio.sleep(2 ** attempt); continue
                return r.status, (await r.json() if r.status == 200 else None)
        except: await asyncio.sleep(1)
    return None, None

async def fetch_player_data(session, tag, headers, trophy_cache, legend_stats_cache, semaphore=None):
    async with (semaphore or contextlib.nullcontext()):
        status, d = await safe_fetch(session, f"https://api.clashofclans.com/v1/players/%23{tag}", headers)
        if status == 200 and d:
            current_trophies = d.get('trophies', 0)
            l_name = TIER_ID_TO_NAME.get(d.get('leagueTier', {}).get('id'), "Unranked")

            if l_name == "Legend League" or current_trophies >= 5000:
                if current_trophies >= 5600: l_name = "Legend League 1"
                elif current_trophies >= 5300: l_name = "Legend League 2"
                else: l_name = "Legend League 3"

            weight = LEAGUE_WEIGHTS.get(l_name, 0)
            legend_log = None

            if weight >= 34:
                log_status, log_data = await safe_fetch(session, f"https://api.clashofclans.com/v1/players/%23{tag}/battlelog", headers)
                if log_status == 200 and log_data:
                    p_stats = legend_stats_cache.setdefault(tag, {"seen_battles": [], "initialized": False, "off_count": 0, "off_trophies": 0, "def_count": 0, "def_trophies": 0, "last_reset": None})
                    now_str = (datetime.datetime.now(datetime.timezone.utc).date() if datetime.datetime.now(datetime.timezone.utc).hour >= 5 else (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).date()).isoformat()

                    if p_stats.get("last_reset") != now_str:
                        p_stats.update({"off_count": 0, "off_trophies": 0, "def_count": 0, "def_trophies": 0, "last_reset": now_str})

                    legend_battles = [b for b in log_data.get('items', []) if b.get('battleType') == 'legend']
                    if not p_stats["initialized"]:
                        p_stats.update({"seen_battles": [f"{b.get('opponentPlayerTag')}_{b.get('attack')}_{b.get('stars')}_{b.get('destructionPercentage')}" for b in legend_battles], "initialized": True})
                    else:
                        seen_set = set(p_stats["seen_battles"])
                        for b in reversed(legend_battles):
                            sig = f"{b.get('opponentPlayerTag')}_{b.get('attack')}_{b.get('stars')}_{b.get('destructionPercentage')}"
                            if sig not in seen_set:
                                trop = calc_legend_trophies(b.get('stars', 0), b.get('destructionPercentage', 0))
                                if b.get('attack') and p_stats["off_count"] < 8:
                                    p_stats["off_trophies"] += trop; p_stats["off_count"] += 1
                                elif not b.get('attack') and p_stats["def_count"] < 8:
                                    p_stats["def_trophies"] += (0 if b.get('stars') == 0 else trop); p_stats["def_count"] += 1
                                p_stats["seen_battles"].append(sig)
                        p_stats["seen_battles"] = p_stats["seen_battles"][-100:]
                    legend_log = {k: p_stats[k] for k in ['off_count', 'off_trophies', 'def_count', 'def_trophies']}
                elif log_status == 403: legend_log = "private"

            return {
                'name': discord.utils.escape_markdown(d.get('name', 'Unknown')), 'trophies': current_trophies,
                'emoji': LEAGUE_EMOJIS.get(l_name, "➖"), 'league_weight': weight, 'th': d.get('townHallLevel', 1),
                'tag': tag, 'delta': get_delta_str(tag, current_trophies, trophy_cache), 'legend_log': legend_log
            }, tag, current_trophies, d
        return None, tag, None, None

# --- UI & VIEWS ---
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.success, custom_id="giveaway_join_btn")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw_data = await load_json_file(GIVEAWAY_FILE, {})
        msg_id_str = str(interaction.message.id)

        if msg_id_str not in gw_data or not gw_data[msg_id_str].get("active", False):
            return await interaction.response.send_message("❌ This giveaway has already ended!", ephemeral=True)

        entrants = gw_data[msg_id_str].get("entrants", [])

        if interaction.user.id in entrants:
            return await interaction.response.send_message("⚠️ You have already entered this giveaway!", ephemeral=True)

        entrants.append(interaction.user.id)
        gw_data[msg_id_str]["entrants"] = entrants
        await save_json_file(GIVEAWAY_FILE, gw_data)

        await interaction.response.send_message("✅ You have successfully entered the giveaway! Good luck!", ephemeral=True)


async def build_leaderboard_embeds(bot):
    players = await load_json_file(PLAYERS_FILE, [])
    if not players: return [discord.Embed(title="Server Leaderboard", description="Tracker is empty.", color=discord.Color.gold())], set(), []

    t_cache, l_cache, n_cache = await asyncio.gather(load_json_file(TROPHY_CACHE_FILE, {}), load_json_file(LEGEND_STATS_FILE, {}), load_json_file(NAME_CACHE_FILE, {}))
    new_cache, data_list, clans, sem = {}, [], set(), asyncio.Semaphore(3)

    results = await asyncio.gather(*(fetch_player_data(bot.session, tag, COC_HEADERS, t_cache, l_cache, sem) for tag in players))
    for p, tag, trop, raw in results:
        if p:
            data_list.append(p); new_cache[tag] = trop
            if raw and raw.get('clan'): clans.add(raw['clan']['tag'])
            if raw and raw.get('name'): n_cache[tag] = raw['name']

    await asyncio.gather(save_json_file(TROPHY_CACHE_FILE, new_cache), save_json_file(LEGEND_STATS_FILE, l_cache), save_json_file(NAME_CACHE_FILE, n_cache))
    data_list.sort(key=lambda x: (x['league_weight'], x['trophies']), reverse=True)

    embeds = []
    for i in range(0, max(1, len(data_list)), 20):
        desc = ""
        for j, p in enumerate(data_list[i:i + 20], start=i + 1):
            line = f"**`{f'{j}.'.ljust(3)}`**{p['emoji']} [**`{format_name_strict(p['name'])}`**](https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={p['tag'].replace('#', '')})**`|{p['trophies']:>4}`**{TROPHY_EMOJI}"
            if p['league_weight'] >= 34:
                ll = p['legend_log']
                if ll == "private": line += " | `🔒 Private`"
                elif isinstance(ll, dict): line += f" | `+{ll['off_trophies']}{to_superscript(ll['off_count'])}".ljust(9) + f"|-{ll['def_trophies']}{to_superscript(ll['def_count'])}".ljust(7) + "`"
            desc += line + p['delta'] + "\n"
        embed = discord.Embed(title="Server Leaderboard", description=desc, color=discord.Color.gold())
        embed.set_footer(text=f"Page {(i//20)+1}/{(len(data_list)+19)//20}")
        embeds.append(embed)
    return embeds, clans, players


class LeaderboardView(discord.ui.View):
    def __init__(self, bot, embeds=None, page=0, msg_id=None):
        super().__init__(timeout=None)
        self.bot, self.embeds, self.page, self.msg_id = bot, embeds, page, msg_id
        if embeds: self.update_btns()

    def update_btns(self):
        self.prev.disabled = self.page <= 0
        self.next.disabled = self.page >= len(self.embeds) - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="lb_prev")
    async def prev(self, interaction, button):
        self.page = max(0, self.page - 1); self.update_btns()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="lb_next")
    async def next(self, interaction, button):
        self.page = min(len(self.embeds)-1, self.page + 1); self.update_btns()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)


class SayModal(discord.ui.Modal, title='Make the bot speak'):
    message_input = discord.ui.TextInput(label='What should the bot say?', style=discord.TextStyle.paragraph, placeholder='Type here...', required=True, max_length=2000)
    def __init__(self, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel
    async def on_submit(self, interaction: discord.Interaction):
        await self.target_channel.send(self.message_input.value)
        await interaction.response.send_message("✅ Ghost message sent!", ephemeral=True)


class SelfRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_role(self, interaction: discord.Interaction, role_name: str):
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role: return await interaction.response.send_message(f"❌ The role **{role_name}** could not be found.", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"➖ Successfully removed the **{role_name}** role.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"➕ Successfully added the **{role_name}** role.", ephemeral=True)

    @discord.ui.button(label="ORE WARS role", style=discord.ButtonStyle.primary, custom_id="role_btn_ore_wars", emoji="⚔️")
    async def btn_ore_wars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_role(interaction, "ORE WARS")

    @discord.ui.button(label="Friendly Challenge role", style=discord.ButtonStyle.success, custom_id="role_btn_fc", emoji="🛡️")
    async def btn_fc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_role(interaction, "Friendly Challenge")


# --- TICKET SYSTEM VIEWS & MODALS ---
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, custom_id="ticket_system_close", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket closing in 5 seconds...", ephemeral=False)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket Closed by User")
        except:
            pass


class TicketModal(discord.ui.Modal):
    def __init__(self, clan_name: str):
        super().__init__(title=f"Application: {clan_name}")
        self.clan_name = clan_name

    q1 = discord.ui.TextInput(
        label="1 - Player Tag - Player Name - Town Hall",
        style=discord.TextStyle.paragraph,
        placeholder="#TAG\nName\nTH 16",
        required=True
    )
    q2 = discord.ui.TextInput(
        label="2 - What are your game interests",
        style=discord.TextStyle.short,
        placeholder="CWL, Trophy Pushing, Farming",
        required=True
    )
    q3 = discord.ui.TextInput(
        label="3 - Where did you hear about us",
        style=discord.TextStyle.short,
        required=True
    )
    q4 = discord.ui.TextInput(
        label="4 - Language(s) - Location - Age",
        style=discord.TextStyle.paragraph,
        placeholder="English\nUS\n23",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel_name = f"ticket-{interaction.user.name.lower()}"
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        welcome_embed = discord.Embed(
            description=f"Thank you for your application to **{self.clan_name}**!\n\nOur team will be with you as soon as possible.\n\nTo close this ticket react with 🔒",
            color=discord.Color.brand_green()
        )

        # FIX: all f-strings are on a single line, no literal newlines inside them
        answers_embed = discord.Embed(color=discord.Color.dark_embed())
        answers_embed.add_field(name="1 - Player Tag - Player Name - Town Hall", value=f"```\n{self.q1.value}\n```", inline=False)
        answers_embed.add_field(name="2 - What are your game interests", value=f"```\n{self.q2.value}\n```", inline=False)
        answers_embed.add_field(name="3 - Where did you hear about us", value=f"```\n{self.q3.value}\n```", inline=False)
        answers_embed.add_field(name="4 - Language(s) - Location - Age", value=f"```\n{self.q4.value}\n```", inline=False)

        role_ping = ""
        if self.clan_name == "Angry Birds":
            role_ping = ""  # e.g., "<@&123456789012345678>"
        elif self.clan_name == "Night Birds":
            role_ping = ""
        elif self.clan_name == "Elite Syndicate":
            role_ping = ""

        ping_msg = f"{interaction.user.mention} {role_ping}"
        await ticket_channel.send(content=ping_msg, embed=welcome_embed)
        await ticket_channel.send(embed=answers_embed, view=TicketCloseView())
        await interaction.followup.send(f"✅ Ticket created! Please head over to {ticket_channel.mention}", ephemeral=True)


class TicketLauncherView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def launch_modal(self, interaction: discord.Interaction, clan_name: str):
        await interaction.response.send_modal(TicketModal(clan_name))

    @discord.ui.button(label="Angry Birds", style=discord.ButtonStyle.secondary, custom_id="btn_ticket_angry", emoji="🦅")
    async def apply_angry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.launch_modal(interaction, "Angry Birds")

    @discord.ui.button(label="Night Birds", style=discord.ButtonStyle.secondary, custom_id="btn_ticket_night", emoji="🦉")
    async def apply_night(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.launch_modal(interaction, "Night Birds")

    @discord.ui.button(label="Elite Syndicate", style=discord.ButtonStyle.secondary, custom_id="btn_ticket_elite", emoji="🛡️")
    async def apply_elite(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.launch_modal(interaction, "Elite Syndicate")


# --- BOT CLASS & SETUP ---
class CoCBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.session, self.lb_pages = None, {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()

        # Register Persistent Views so buttons work after restarts
        self.add_view(LeaderboardView(self))
        self.add_view(SelfRoleView())
        self.add_view(TicketLauncherView())
        self.add_view(TicketCloseView())
        self.add_view(GiveawayView())

        await self.tree.sync()
        # FIX: module-level tasks, not self.
        auto_lb.start()
        giveaway_checker.start()

    async def close(self):
        if self.session: await self.session.close()
        await super().close()

bot = CoCBot()


@tasks.loop(minutes=5)
async def auto_lb():
    try:
        embeds, _, _ = await build_leaderboard_embeds(bot)
        config = await load_json_file(CONFIG_FILE, {})
        if (chan := bot.get_channel(config.get("channel_id"))):
            msg = await chan.fetch_message(config["message_id"])
            await msg.edit(embed=embeds[0], view=LeaderboardView(bot, embeds))
    except: pass


@tasks.loop(minutes=1)
async def giveaway_checker():
    await bot.wait_until_ready()
    gw_data = await load_json_file(GIVEAWAY_FILE, {})
    current_time = int(time.time())
    changes_made = False

    for msg_id, data in gw_data.items():
        if data.get("active") and current_time >= data.get("end_time"):
            try:
                channel = bot.get_channel(data["channel_id"]) or await bot.fetch_channel(data["channel_id"])
                message = await channel.fetch_message(int(msg_id))

                entrants = data.get("entrants", [])
                winners_count = data.get("winners", 1)

                if not entrants:
                    await channel.send(f"Nobody entered the giveaway for **{data['prize']}**! 😢")
                else:
                    actual_winners = min(len(entrants), winners_count)
                    winners = random.sample(entrants, actual_winners)
                    winner_mentions = ", ".join(f"<@{w}>" for w in winners)
                    await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{data['prize']}**! (Hosted by <@{data['host_id']}>)")

                ended_embed = message.embeds[0]
                ended_embed.color = discord.Color.red()
                ended_embed.title = "🎊 Giveaway Ended 🎊"
                view = discord.ui.View()
                btn = discord.ui.Button(label="Giveaway Ended", style=discord.ButtonStyle.secondary, disabled=True)
                view.add_item(btn)
                await message.edit(embed=ended_embed, view=view)

            except Exception as e:
                logger.error(f"Failed to end giveaway {msg_id}: {e}")

            data["active"] = False
            changes_made = True

    if changes_made:
        await save_json_file(GIVEAWAY_FILE, gw_data)


# --- PREFIX COMMANDS ---
@bot.command(name='sync')
async def sync_tree(ctx):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.administrator:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Command tree synced! ({len(synced)} commands)")
    else:
        await ctx.send("❌ You do not have permission to run this command.")


# --- SLASH COMMANDS ---

@bot.tree.command(name='giveaway', description="Start a restart-proof giveaway.")
@app_commands.describe(prize="What are you giving away?", duration_minutes="How many minutes should it run?", winners="How many winners?")
@is_admin_or_owner()
async def start_giveaway(interaction: discord.Interaction, prize: str, duration_minutes: int, winners: int = 1):
    end_time = int(time.time()) + (duration_minutes * 60)

    embed = discord.Embed(
        title="🎉 New Giveaway! 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Hosted by:** {interaction.user.mention}\n\n**Ends:** <t:{end_time}:R> (<t:{end_time}:f>)",
        color=discord.Color.brand_green()
    )

    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed, view=GiveawayView())

    gw_data = await load_json_file(GIVEAWAY_FILE, {})
    gw_data[str(msg.id)] = {
        "channel_id": interaction.channel_id,
        "host_id": interaction.user.id,
        "prize": prize,
        "end_time": end_time,
        "winners": winners,
        "entrants": [],
        "active": True
    }
    await save_json_file(GIVEAWAY_FILE, gw_data)


@bot.tree.command(name='setup_tickets', description="Set up the ticket application panel.")
@is_admin_or_owner()
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="The Bird Nest Clans",
        description="**Select which clan you would like to apply to**\n\n"
                    "🦅 - Angry Birds\n"
                    "🦉 - Night Birds\n"
                    "🛡️ - Elite Syndicate\n",
        color=discord.Color.brand_green()
    )
    embed.set_footer(text="Application System")
    await interaction.channel.send(embed=embed, view=TicketLauncherView())
    await interaction.response.send_message("✅ Ticket panel deployed!", ephemeral=True)


@bot.tree.command(name='clan_info', description="Displays the clans in our alliance along with their links, types, and stats.")
async def command_clan_info(interaction: discord.Interaction):
    await interaction.response.defer()

    alliance_clans = [
        {
            "tag": "#2QUVQR0LC",
            "type": "Competitive clan",
            "requirements": "TH16+, Active Daily",
            "link": "https://link.clashofclans.com/en?action=OpenClanProfile&tag=2QUVQR0LC",
            "image_filename": "angrybirdsbanner.jpeg",
            "color": discord.Color.red()
        },
        {
            "tag": "#2GCCRP2JY",
            "type": "CWL Feeder clan",
            "requirements": "TH14+",
            "link": "https://link.clashofclans.com/en?action=OpenClanProfile&tag=2GCCRP2JY",
            "image_filename": "nightbirdsbanner.jpeg",
            "color": discord.Color.purple()
        },
        {
            "tag": "#2RYPQ0GRQ",
            "type": "Ore wars/sidewars clan",
            "requirements": "Heroes down allowed",
            "link": "https://link.clashofclans.com/en?action=OpenClanProfile&tag=2RYPQ0GRQ",
            "image_filename": "elitesyndicatebanner.jpeg",
            "color": discord.Color.blue()
        }
    ]

    embeds_to_send = []
    files_to_send = []

    for clan in alliance_clans:
        clean_tag = clan['tag'].replace('#', '%23')
        status, clan_data = await safe_fetch(bot.session, f"https://api.clashofclans.com/v1/clans/{clean_tag}", COC_HEADERS)

        wins = clan_data.get('warWins', 0) if status == 200 else "N/A"
        streak = clan_data.get('warWinStreak', 0) if status == 200 else "N/A"
        league = clan_data.get('warLeague', {}).get('name', 'Unranked') if status == 200 else "N/A"

        text_embed = discord.Embed(
            description=(
                f"**Type:** {clan['type']}\n"
                f"**Requirements:** {clan['requirements']}\n"
                f"**Clan League:** {league}\n"
                f"**War Wins:** {wins}\n"
                f"**Win Streak:** 🔥 {streak}\n"
                f"[🔗 View in Game]({clan['link']})"
            ),
            color=clan['color']
        )

        try:
            file = discord.File(clan['image_filename'], filename=clan['image_filename'])
            files_to_send.append(file)
            img_embed = discord.Embed(color=clan['color'])
            img_embed.set_image(url=f"attachment://{clan['image_filename']}")
            embeds_to_send.append(img_embed)
            embeds_to_send.append(text_embed)
        except FileNotFoundError:
            text_embed.description = f"*(Error: Could not find image file `{clan['image_filename']}`)*\n\n" + text_embed.description
            embeds_to_send.append(text_embed)

    await interaction.followup.send(embeds=embeds_to_send, files=files_to_send)


@bot.tree.command(name='say', description="Anonymously make the bot say a message in a specific channel.")
@app_commands.describe(channel="The channel where the bot should send the message.")
@is_admin_or_owner()
async def command_say_modal(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.send_modal(SayModal(target_channel=channel))


@bot.tree.command(name='setleaderboard', description="Set up the automated updating leaderboard in this channel.")
@is_admin_or_owner()
async def set_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    config = await load_json_file(CONFIG_FILE, {})
    if config.get("channel_id") and config.get("message_id") and (old_channel := bot.get_channel(config["channel_id"])):
        try: await (await old_channel.fetch_message(config["message_id"])).delete()
        except: pass

    embeds, _, _ = await build_leaderboard_embeds(bot)
    view = LeaderboardView(bot, embeds)
    lb_message = await interaction.channel.send(embed=embeds[0], view=view)
    view.msg_id, bot.lb_pages[lb_message.id] = lb_message.id, 0
    await save_json_file(CONFIG_FILE, {"channel_id": interaction.channel_id, "message_id": lb_message.id})
    await interaction.followup.send("✅ Automated leaderboard successfully set up in this channel!", ephemeral=True)


@bot.tree.command(name='setup_roles', description="Set up the self-assignable roles message in this channel.")
@is_admin_or_owner()
async def setup_roles(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎭 Self-Assign Roles",
        description="Click the buttons below to add or remove roles.\n\n"
                    "⚔️ **ORE WARS** - Get pinged for Ore Wars.\n"
                    "🛡️ **FC role** - Get pinged for Friendly Challenges(FC).",
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=SelfRoleView())
    await interaction.response.send_message("✅ Self-assign roles menu has been deployed!", ephemeral=True)


@bot.tree.command(name='add', description="Add a player to the tracker.")
@is_admin_or_owner()
async def add_p(interaction, tag: str):
    await interaction.response.defer(ephemeral=True)
    clean = tag.strip().lstrip('#').upper()
    s, d = await safe_fetch(bot.session, f"https://api.clashofclans.com/v1/players/%23{clean}", COC_HEADERS)
    if s == 200:
        players = await load_json_file(PLAYERS_FILE, [])
        if clean not in players:
            players.append(clean); await save_json_file(PLAYERS_FILE, players)
            await interaction.followup.send(f"✅ Added {d['name']}!")
        else: await interaction.followup.send("Already added.")
    else: await interaction.followup.send("API Error.")


@bot.tree.command(name='add_clan', description="Add all members of a Clash of Clans clan to the tracker.")
@is_admin_or_owner()
async def add_clan(interaction: discord.Interaction, clan_tag: str):
    await interaction.response.defer(ephemeral=True)
    status, data = await safe_fetch(bot.session, f"https://api.clashofclans.com/v1/clans/%23{clan_tag.strip().lstrip('#').upper()}", COC_HEADERS)

    if status == 200 and data:
        players, name_cache, added_count = await load_json_file(PLAYERS_FILE, []), await load_json_file(NAME_CACHE_FILE, {}), 0
        for m in data.get('memberList', []):
            m_tag = m.get('tag', '').lstrip('#').upper()
            if m_tag and m_tag not in players:
                players.append(m_tag); name_cache[m_tag] = m.get('name', 'Unknown'); added_count += 1
        if added_count > 0:
            await asyncio.gather(save_json_file(PLAYERS_FILE, players), save_json_file(NAME_CACHE_FILE, name_cache))
            await interaction.followup.send(f"✅ Successfully added **{added_count}** new members from **{data.get('name', 'Unknown Clan')}**!")
        else: await interaction.followup.send(f"⚠️ All members of **{data.get('name', 'Unknown Clan')}** are already in the tracker.")
    else: await interaction.followup.send("❌ Clan not found or API is rate-limiting.")


@bot.tree.command(name='remove', description="Remove a player from the server tracker.")
@app_commands.autocomplete(player=player_autocomplete)
@is_admin_or_owner()
async def remove_player(interaction: discord.Interaction, player: str):
    await interaction.response.defer(ephemeral=True)
    if not (target_tag := await resolve_player_input(player)): return await interaction.followup.send("❌ Please provide a valid player name or tag.")
    players = await load_json_file(PLAYERS_FILE, [])
    if target_tag in players:
        players.remove(target_tag); await save_json_file(PLAYERS_FILE, players)
        await interaction.followup.send(f"🗑️ Removed **#{target_tag}** from the server tracker.")
    else: await interaction.followup.send("⚠️ Player is not currently in the server tracker.")


@bot.tree.command(name='leaderboard', description="Manually fetch the current server leaderboard.")
@app_commands.checks.cooldown(1, 300, key=lambda i: i.guild_id)
async def command_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    embeds, _, _ = await build_leaderboard_embeds(bot)
    view = LeaderboardView(bot, embeds)
    msg = await interaction.followup.send(embed=embeds[0], view=view, wait=True)
    view.msg_id = msg.id; bot.lb_pages[msg.id] = 0


@bot.tree.command(name='profile', description="Look up a specific Clash of Clans player profile.")
@app_commands.autocomplete(player=player_autocomplete)
async def player_profile(interaction: discord.Interaction, player: str):
    await interaction.response.defer()
    if not (target_tag := await resolve_player_input(player)): return await interaction.followup.send("❌ Please provide a valid player name or tag.")

    legend_stats_cache = await load_json_file(LEGEND_STATS_FILE, {})
    p_dict, _, _, raw = await fetch_player_data(bot.session, target_tag, COC_HEADERS, {}, legend_stats_cache)
    await save_json_file(LEGEND_STATS_FILE, legend_stats_cache)

    if raw:
        sw_count = (await load_json_file(SUPERWHOO_FILE, {})).get(f"#{target_tag}", {}).get("count", 0)
        formatted_profile_name = '/Sam\\' if raw.get('name', '').lower() == 'sam' else raw.get('name', 'Unknown')
        embed = discord.Embed(title=f"{p_dict['emoji']} {formatted_profile_name} (TH{p_dict['th']})", url=f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={target_tag}", color=discord.Color.blue())
        embed.add_field(name="Clan", value=f"{raw.get('clan', {}).get('name', 'No Clan')} ({raw.get('role', 'Member').capitalize() if raw.get('clan') else 'N/A'})", inline=False)
        embed.add_field(name="Trophies", value=f"{TROPHY_EMOJI} {raw.get('trophies')} (Best: {raw.get('bestTrophies')})", inline=True)
        embed.add_field(name="War Stars", value=f"⭐ {raw.get('warStars')}", inline=True)
        embed.add_field(name="Attacks Won", value=f"⚔️ {raw.get('attackWins')}", inline=True)
        embed.add_field(name="Superwhoo Fails", value=f"💔 {sw_count}", inline=True)
        embed.set_footer(text=f"Tag: #{target_tag}")
        await interaction.followup.send(embed=embed)
    else: await interaction.followup.send("❌ Could not find that player, or the API is currently unavailable.")


@bot.tree.command(name='superwhoo', description="View the Superwhoo Leaderboard or a specific player's painful misses.")
@app_commands.autocomplete(player=player_autocomplete)
async def command_superwhoo(interaction: discord.Interaction, player: str = None):
    await interaction.response.defer()
    superwhoo_data = await load_json_file(SUPERWHOO_FILE, {})
    if not superwhoo_data: return await interaction.followup.send("🏆 The Superwhoo Leaderboard is currently empty. No painful misses yet!")

    if player:
        if not (target_tag := await resolve_player_input(player)): return await interaction.followup.send("❌ Please provide a valid player name or tag.")
        p_data = superwhoo_data.get(f"#{target_tag}")

        raw_name = (await load_json_file(NAME_CACHE_FILE, {})).get(target_tag, f'#{target_tag}')
        formatted_name = '/Sam\\' if raw_name.lower() == 'sam' else raw_name

        if not p_data or p_data['count'] == 0: return await interaction.followup.send(f"✅ Great news! **{formatted_name}** has no recorded fails.")

        history_text = ""
        for sig in reversed(p_data['seen']):
            parts = sig.split('_')
            try: time_str = datetime.datetime.strptime(parts[0], "%Y%m%dT%H%M%S.000Z").strftime("%b %d, %Y") if len(parts) >= 3 else "Unknown Date"
            except: time_str = "Unknown Date"

            if len(parts) >= 6 and parts[4].isdigit():
                star_display = "☆" * int(parts[4]) if int(parts[4]) > 0 else "0 ☆"
            else:
                star_display = "?"

            history_text += f"• **{f'{parts[5]}%' if len(parts) >= 6 else '97-99%'}** ({star_display}) *(War Ended: {time_str})*\n"

        if len(history_text) > 4000: history_text = history_text[:4000] + "...\n*(Showing latest 50)*"
        embed = discord.Embed(title=f"💔 {formatted_name}'s Superwhoo History", color=discord.Color.red())
        embed.add_field(name=f"Total Fails: {p_data['count']}", value=history_text, inline=False)
        return await interaction.followup.send(embed=embed)

    lb = sorted([{"name": d['name'], "count": d['count']} for d in superwhoo_data.values() if d['count'] > 0], key=lambda x: x['count'], reverse=True)
    if not lb: return await interaction.followup.send("🏆 The Superwhoo Leaderboard is currently empty. No painful misses yet!")

    desc_text = "".join(f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'`{i}.`'} **{discord.utils.escape_markdown('/Sam\\' if p['name'].lower() == 'sam' else p['name'])}** - {p['count']} Superwhoo{'s' if p['count'] != 1 else ''}\n" for i, p in enumerate(lb[:50], 1))
    embed = discord.Embed(title="🏆 The Superwhoo Leaderboard 🏆", description="The ultimate wall of shame for 97-99% war attacks (Normal & CWL).", color=discord.Color.red())
    embed.add_field(name="Rankings", value=desc_text, inline=False)
    await interaction.followup.send(embed=embed)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandNotFound):
        return
    if not interaction.response.is_done():
        try: await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)
        except: pass


if __name__ == '__main__': bot.run(DISCORD_TOKEN)