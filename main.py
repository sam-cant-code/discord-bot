import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp, asyncio, json, os, time, logging, contextlib, datetime, re, io
from dotenv import load_dotenv

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger('CoCBot')
load_dotenv()

PLAYERS_FILE, CONFIG_FILE, TROPHY_CACHE_FILE = 'players.json', 'lb_config.json', 'trophy_cache.json'
LEGEND_STATS_FILE, SUPERWHOO_FILE = 'legend_stats.json', 'superwhoo_stats.json'
NAME_CACHE_FILE, ARMIES_DB_FILE = 'name_cache.json', 'armies_db.json'

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COC_TOKEN = os.getenv('COC_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

intents = discord.Intents.default()
intents.message_content = True

TROPHY_EMOJI = "<:Trophy:1485318298445938740>"

# --- EMOJI & LEAGUE MAPPERS (Compressed) ---
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
    "Legend League": "<:legend_league:1485298146186625205>"
}
LEAGUE_WEIGHTS = {name: i for i, name in enumerate(LEAGUE_EMOJIS.keys(), start=1)}

TROOP_EMOJIS = {
    0: "<:Avatar_Barbarian:1493123027486117978>", 1: "<:Avatar_Archer:1493123099598655639>", 2: "goblin", 3: "giant", 4: "wallbreaker", 5: "balloon",
    6: "wizard", 7: "healer", 8: "dragon", 9: "pekka", 10: "<:Avatar_Minion:1493123172822810674> ", 11: "hogrider", 12: "valkyrie", 13: "golem",
    15: "witch", 17: "<:Avatar_Lava_Hound:1493123323939262604>", 22: "bowler", 23: "<:Avatar_Baby_Dragon:1493123145526280202>", 24: "miner",
    26: "superbarbarian", 27: "superarcher", 28: "sneakygoblin", 35: "icehound", 51: "wallwrecker", 52: "battleblimp", 53: "yeti", 57: "superminions",
    58: "icegolem", 59: "electrodragon", 62: "stoneslammer", 63: "<:Avatar_Inferno_Dragon:1493123215545995335>", 65: "<:Avatar_Dragon_Rider:1493122980795125931>",
    66: "troop66", 75: "<:Avatar_Siege_Barracks:1493245189450633397> ", 80: "<:Avatar_Rocket_Balloon:1493123292763000943> ", 82: "headhunter",
    87: "loglauncher", 91: "flameflinger", 92: "battledrill", 95: "electrotitan", 97: "apprenticewarden", 110: "rootrider", 132: "thrower",
    147: "meteorgolem", 150: "furnace", 177: "smasher"
}

SPELL_EMOJIS = {
    0: "lightning", 1: "heal", 2: "rage", 3: "jump", 4: "spell4", 5: "<:Freeze_Spell_info:1493245284740894921>", 7: "earthquake", 8: "haste",
    9: "<:Poison_Spell_info:1493245348628664600>", 10: "bat", 11: "invisibility", 17: "skeleton_spell", 70: "<:Overgrowth_Spell_info:1493245378483454052>",
    98: "<:Revive_Spell_info:1493245315405447218>", 120: "<:Totem_Spell_info:1493245251270348992>"
}

TIER_ID_TO_NAME = {
    105000001: "Skeleton League 1", 105000002: "Skeleton League 2", 105000003: "Skeleton League 3", 105000004: "Barbarian League 4",
    105000005: "Barbarian League 5", 105000006: "Barbarian League 6", 105000007: "Archer League 7", 105000008: "Archer League 8",
    105000009: "Archer League 9", 105000010: "Wizard League 10", 105000011: "Wizard League 11", 105000012: "Wizard League 12",
    105000013: "Valkyrie League 13", 105000014: "Valkyrie League 14", 105000015: "Valkyrie League 15", 105000016: "Witch League 16",
    105000017: "Witch League 17", 105000018: "Witch League 18", 105000019: "Golem League 19", 105000020: "Golem League 20",
    105000021: "Golem League 21", 105000022: "P.E.K.K.A League 22", 105000023: "P.E.K.K.A League 23", 105000024: "P.E.K.K.A League 24",
    105000025: "Titan League 25", 105000026: "Titan League 26", 105000027: "Titan League 27", 105000028: "Dragon League 28",
    105000029: "Dragon League 29", 105000030: "Dragon League 30", 105000031: "Electro League 31", 105000032: "Electro League 32",
    105000033: "Electro League 33", 105000034: "Legend League"
}

# --- NON-BLOCKING FILE HELPERS ---
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

# --- PLAYER NAME RESOLUTION & AUTOCOMPLETE ---
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

# --- MATH & FORMATTING HELPERS ---
def format_name_strict(name, max_width=10):
    safe_name = name.replace('`', "'")
    return (safe_name[:max_width - 2] + "..").ljust(max_width) if len(safe_name) > max_width else safe_name.ljust(max_width)

def calc_legend_trophies(stars, dest):
    return dest // 10 if stars == 0 else 5 + max(0, dest - 1) // 9 if stars == 1 else 16 + max(0, dest - 50) // 3 if stars == 2 else 40 if stars == 3 else 0

def to_superscript(num):
    return ''.join({'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}.get(c, '') for c in str(num))

def get_delta_str(tag, current, cache):
    diff = current - cache.get(tag, current) if isinstance(cache.get(tag), int) else 0
    return f" `▲ +{diff}`" if diff > 0 else f" `▼ {diff}`" if diff < 0 else ""

get_league_emoji = lambda l: LEAGUE_EMOJIS.get(l, "➖")
get_league_weight = lambda l: LEAGUE_WEIGHTS.get(l, 0)
get_battle_sig = lambda b: f"{b.get('opponentPlayerTag')}_{b.get('attack')}_{b.get('stars')}_{b.get('destructionPercentage')}"

def get_army_summary(share_code: str) -> str:
    units, spells = [], []
    u_match, s_match = re.search(r'u([\d\-x]+)', share_code), re.search(r's([\d\-x]+)', share_code)
    
    if u_match:
        for i in u_match.group(1).split('-'):
            if 'x' in i: qty, u_id = i.split('x'); units.append(f"{qty}x{TROOP_EMOJIS.get(int(u_id), f'unit{u_id}')}")
    if s_match:
        for i in s_match.group(1).split('-'):
            if 'x' in i: qty, s_id = i.split('x'); spells.append(f"{qty}x{SPELL_EMOJIS.get(int(s_id), f'spell{s_id}')}")
            
    return " | ".join(filter(None, [" ".join(units), " ".join(spells)])) or "unknowntroops"

def is_admin_or_owner():
    def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

# --- REUSABLE API FETCH LOGIC ---
async def safe_fetch(session, url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=10) as r:
                if r.status == 429:
                    logger.warning(f"Rate limited (429) on API. Retrying in {2**attempt}s...")
                    await asyncio.sleep(2 ** attempt); continue
                return r.status, (await r.json() if r.status == 200 else None)
        except Exception as e:
            logger.error(f"Network error on fetch: {e}")
            await asyncio.sleep(1)
    return None, None

async def fetch_league_history(session, tag, headers):
    status, hist = await safe_fetch(session, f"https://api.clashofclans.com/v1/players/%23{tag}/leaguehistory", headers)
    if status == 200 and hist and hist.get('items'):
        return TIER_ID_TO_NAME.get(sorted(hist['items'], key=lambda x: str(x.get('season', '')))[-1].get('leagueTierId', 0), "Unranked")
    return "Unranked"

async def fetch_player_data(session, tag, headers, trophy_cache, legend_stats_cache, armies_db, semaphore=None):
    async with (semaphore or contextlib.nullcontext()):
        await asyncio.sleep(0.1)
        status, d = await safe_fetch(session, f"https://api.clashofclans.com/v1/players/%23{tag}", headers)
        
        if status == 200 and d:
            current_trophies = d.get('trophies', 0)
            await asyncio.sleep(0.1)
            
            league_tier_id = d.get('leagueTier', {}).get('id')
            l_name = TIER_ID_TO_NAME.get(league_tier_id, (d.get('leagueTier') or d.get('league') or {}).get('name', 'Unranked'))
            if l_name == "Unranked": l_name = await fetch_league_history(session, tag, headers)
            weight = get_league_weight(l_name)
            
            legend_log = None
            log_status, log_data = await safe_fetch(session, f"https://api.clashofclans.com/v1/players/%23{tag}/battlelog", headers)
            
            if log_status == 200 and log_data:
                items = log_data.get('items', [])
                
                # Process Armies DB
                if tag not in armies_db: armies_db[tag] = {"seen_battles": [], "ranked": {}, "unranked": {}}
                p_armies = armies_db[tag]
                if "armies" in p_armies: p_armies["ranked"] = p_armies.pop("armies")
                p_armies.setdefault("ranked", {}); p_armies.setdefault("unranked", {})
                
                for b in items:
                    sig = get_battle_sig(b)
                    if sig not in p_armies["seen_battles"]:
                        p_armies["seen_battles"].append(sig)
                        if b.get('attack') and 'armyShareCode' in b:
                            category = "ranked" if b.get('battleType') in ['legend', 'homeVillage'] else "unranked"
                            code = b['armyShareCode']
                            p_armies[category].setdefault(code, {"uses": 0, "total_dest": 0})
                            p_armies[category][code]["uses"] += 1
                            p_armies[category][code]["total_dest"] += b.get('destructionPercentage', 0)
                p_armies["seen_battles"] = p_armies["seen_battles"][-200:]
                
                # Process Legend Stats
                if weight == 34:  
                    if tag not in legend_stats_cache: legend_stats_cache[tag] = {"seen_battles": [], "initialized": False, "off_count": 0, "off_trophies": 0, "def_count": 0, "def_trophies": 0, "last_reset": None}
                    p_stats = legend_stats_cache[tag]

                    now = datetime.datetime.now(datetime.timezone.utc)
                    current_day_str = (now.date() if now.hour >= 5 else (now - datetime.timedelta(days=1)).date()).isoformat()

                    if p_stats.get("last_reset") != current_day_str:
                        p_stats.update({"off_count": 0, "off_trophies": 0, "def_count": 0, "def_trophies": 0, "last_reset": current_day_str})
                        logger.info(f"🔄 [{tag}] New Legend Day! Stats reset.")

                    legend_battles = [b for b in items if b.get('battleType') == 'legend']
                    if not p_stats.get("initialized"):
                        p_stats.update({"seen_battles": [get_battle_sig(b) for b in legend_battles], "initialized": True})
                    else:
                        seen_set = set(p_stats.get("seen_battles", []))
                        for b in reversed([b for b in legend_battles if get_battle_sig(b) not in seen_set]):
                            sig, is_attack, stars, dest = get_battle_sig(b), b.get('attack', False), b.get('stars', 0), b.get('destructionPercentage', 0)
                            trophies = calc_legend_trophies(stars, dest)
                            if is_attack and p_stats["off_count"] < 8:
                                p_stats["off_trophies"] += trophies; p_stats["off_count"] += 1
                            elif not is_attack and p_stats["def_count"] < 8:
                                p_stats["def_trophies"] += (0 if stars == 0 else trophies); p_stats["def_count"] += 1
                            p_stats["seen_battles"].append(sig)
                        p_stats["seen_battles"] = p_stats["seen_battles"][-100:]

                    legend_log = {k: p_stats[k] for k in ['off_count', 'off_trophies', 'def_count', 'def_trophies']}
            elif log_status == 403 and weight == 34:
                legend_log = "private"

            return {
                'name': discord.utils.escape_markdown(d.get('name', 'Unknown')), 'trophies': current_trophies,
                'emoji': get_league_emoji(l_name), 'league_weight': weight, 'th': d.get('townHallLevel', 1),
                'tag': tag, 'delta': get_delta_str(tag, current_trophies, trophy_cache), 'legend_log': legend_log
            }, tag, current_trophies, d
        return None, tag, None, None

# --- SUPERWHOO LOGIC ---
def process_war_data(war_data, superwhoo_data, tracked_clan_tags, tracked_players):
    end_time, formatted_tracked = war_data.get('endTime', 'unknown_time'), [f"#{p.lstrip('#').upper()}" for p in tracked_players]
    for clan_side in ['clan', 'opponent']:
        side_data = war_data.get(clan_side, {})
        if side_data.get('tag') not in tracked_clan_tags: continue
        for member in side_data.get('members', []):
            tag, name = member.get('tag'), member.get('name')
            if tag not in formatted_tracked or 'attacks' not in member: continue
            for idx, attack in enumerate(member['attacks']):
                dest, stars = attack.get('destructionPercentage', 0), attack.get('stars', 0)
                if 97 <= dest <= 99:
                    sig = f"{end_time}_{tag}_{attack.get('defenderTag')}_{idx}_{stars}_{dest}"
                    legacy_sig = f"{end_time}_{tag}_{attack.get('defenderTag')}_{idx}"
                    if tag not in superwhoo_data: superwhoo_data[tag] = {"name": name, "count": 0, "seen": []}
                    if legacy_sig in superwhoo_data[tag]["seen"]:
                        superwhoo_data[tag]["seen"].remove(legacy_sig); superwhoo_data[tag]["count"] = max(0, superwhoo_data[tag]["count"] - 1)
                    if sig not in superwhoo_data[tag]["seen"]:
                        superwhoo_data[tag]["count"] += 1; superwhoo_data[tag]["seen"].append(sig)
                        superwhoo_data[tag]["seen"] = superwhoo_data[tag]["seen"][-50:]; superwhoo_data[tag]["name"] = name 

async def process_clan_wars(bot, clan_tags, tracked_players):
    if not clan_tags: return
    headers, superwhoo_data = {'Authorization': f'Bearer {COC_TOKEN}'}, await load_json_file(SUPERWHOO_FILE, {})
    for c_tag in clan_tags:
        c_tag_clean = c_tag.replace('#', '%23')
        status, war = await safe_fetch(bot.session, f"https://api.clashofclans.com/v1/clans/{c_tag_clean}/currentwar", headers)
        if status == 200 and war and war.get('state') != 'notInWar': process_war_data(war, superwhoo_data, clan_tags, tracked_players)
        await asyncio.sleep(0.1) 
        status, cwl_group = await safe_fetch(bot.session, f"https://api.clashofclans.com/v1/clans/{c_tag_clean}/currentwar/leaguegroup", headers)
        if status == 200 and cwl_group and cwl_group.get('state') != 'ended':
            for round_data in cwl_group.get('rounds', []):
                for war_tag in [w for w in round_data.get('warTags', []) if w != "#0"]:
                    w_status, cwl_war = await safe_fetch(bot.session, f"https://api.clashofclans.com/v1/clanwarleagues/wars/{war_tag.replace('#', '%23')}", headers)
                    if w_status == 200 and cwl_war and (cwl_war.get('clan', {}).get('tag') == c_tag or cwl_war.get('opponent', {}).get('tag') == c_tag):
                        process_war_data(cwl_war, superwhoo_data, clan_tags, tracked_players)
                    await asyncio.sleep(0.1)
    await save_json_file(SUPERWHOO_FILE, superwhoo_data)

# --- LEADERBOARD BUILDER ---
async def build_leaderboard_embeds(bot):
    players = await load_json_file(PLAYERS_FILE, [])
    if not players:
        embed = discord.Embed(title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}", description="The server leaderboard is empty. Ask an admin to use `/add` or `/add_clan`.", color=discord.Color.gold())
        embed.timestamp, embed.set_footer = discord.utils.utcnow(), lambda **k: setattr(embed, '_footer', k)
        embed.set_footer(text="Page 1/1 | Last Refreshed")
        return [embed], set(), [] 

    trophy_cache, legend_stats_cache, name_cache, armies_db = await asyncio.gather(
        load_json_file(TROPHY_CACHE_FILE, {}), load_json_file(LEGEND_STATS_FILE, {}), 
        load_json_file(NAME_CACHE_FILE, {}), load_json_file(ARMIES_DB_FILE, {})
    )
    
    new_cache, data_list, unique_clans, headers, semaphore = {}, [], set(), {'Authorization': f'Bearer {COC_TOKEN}'}, asyncio.Semaphore(3)
    results = await asyncio.gather(*(fetch_player_data(bot.session, tag, headers, trophy_cache, legend_stats_cache, armies_db, semaphore) for tag in players))

    for p_dict, tag, cur_trophies, raw in results:
        if p_dict:
            data_list.append(p_dict); new_cache[tag] = cur_trophies
            if raw and raw.get('clan'): unique_clans.add(raw['clan']['tag'])
            if raw and raw.get('name'): name_cache[tag] = raw.get('name')

    await asyncio.gather(
        save_json_file(TROPHY_CACHE_FILE, new_cache), save_json_file(LEGEND_STATS_FILE, legend_stats_cache),
        save_json_file(NAME_CACHE_FILE, name_cache), save_json_file(ARMIES_DB_FILE, armies_db)
    )

    data_list.sort(key=lambda x: (x['league_weight'], x['trophies']), reverse=True)
    embeds, chunk_size = [], 20
    total_pages = max(1, (len(data_list) + chunk_size - 1) // chunk_size)

    for i in range(0, max(1, len(data_list)), chunk_size):
        desc = ""
        for j, p in enumerate(data_list[i:i + chunk_size], start=i + 1):
            line = f"`{f'{j}.'.ljust(3)}`{p['emoji']} [**`{format_name_strict(p['name'], 10)}`**](https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={p['tag'].replace('#', '')})`|{p['trophies']:>4}`{TROPHY_EMOJI}"
            if p.get('league_weight') == 34:
                ll = p.get('legend_log')
                if ll == "private": line += " | `🔒 Private`"
                elif isinstance(ll, dict): line += f" | `+{ll['off_trophies']}{to_superscript(ll['off_count'])}".ljust(9) + f"|-{ll['def_trophies']}{to_superscript(ll['def_count'])}".ljust(7) + "`"
            desc += line + p['delta'] + "\n"

        embed = discord.Embed(title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}", description=desc, color=discord.Color.gold())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f"Page {(i // chunk_size) + 1}/{total_pages} | Last Refreshed")
        embeds.append(embed)

    return embeds, unique_clans, players

# --- INTERACTIVE VIEW ---
class LeaderboardView(discord.ui.View):
    def __init__(self, bot, embeds=None, current_page=0, message_id=None):
        super().__init__(timeout=None)
        self.bot, self.embeds, self.current_page, self.message_id, self.cooldown_seconds = bot, embeds, current_page, message_id, 300
        if self.embeds: self.update_buttons()

    async def ensure_embeds(self, interaction):
        if not self.embeds:
            await interaction.response.defer()
            self.embeds, unique_clans, tracked_players = await build_leaderboard_embeds(self.bot)
            self.bot.loop.create_task(process_clan_wars(self.bot, unique_clans, tracked_players))
            try:
                original_msg = await interaction.channel.fetch_message(interaction.message.id)
                self.current_page = int(original_msg.embeds[0].footer.text.split('|')[0].strip().split(' ')[1].split('/')[0]) - 1
            except: self.current_page = 0
            self.current_page = min(max(0, self.current_page), len(self.embeds) - 1)
            self.update_buttons()

    def update_buttons(self):
        if self.embeds:
            self.prev_button.disabled, self.next_button.disabled = self.current_page <= 0, self.current_page >= len(self.embeds) - 1

    def save_state(self, interaction):
        self.bot.lb_pages[self.message_id or interaction.message.id] = self.current_page

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="lb_prev_btn")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.ensure_embeds(interaction); self.current_page = max(0, self.current_page - 1)
        self.update_buttons(); self.save_state(interaction)
        await (interaction.edit_original_response if interaction.response.is_done() else interaction.response.edit_message)(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple, emoji="🔄", custom_id="refresh_lb_btn")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (current_time := time.time()) - self.bot.last_refresh_time < self.cooldown_seconds:
            return await interaction.response.send_message(f"⏳ Please wait **{int(self.cooldown_seconds - (current_time - self.bot.last_refresh_time)) // 60}m {int(self.cooldown_seconds - (current_time - self.bot.last_refresh_time)) % 60}s** before refreshing again.", ephemeral=True)
        loading_embed = self.embeds[self.current_page].copy() if self.embeds else discord.Embed(title=f"{TROPHY_EMOJI} Server Leaderboard {TROPHY_EMOJI}", color=discord.Color.gold())
        loading_embed.set_footer(text="⏳ Fetching latest data from Clash of Clans API, please wait...")
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=loading_embed, view=self)
        
        self.bot.last_refresh_time = current_time
        self.embeds, unique_clans, tracked_players = await build_leaderboard_embeds(self.bot)
        self.bot.loop.create_task(process_clan_wars(self.bot, unique_clans, tracked_players))
        self.current_page = min(self.current_page, len(self.embeds) - 1)
        for child in self.children: child.disabled = False
        self.update_buttons(); self.save_state(interaction)
        await interaction.edit_original_response(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="lb_next_btn")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.ensure_embeds(interaction); self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        self.update_buttons(); self.save_state(interaction)
        await (interaction.edit_original_response if interaction.response.is_done() else interaction.response.edit_message)(embed=self.embeds[self.current_page], view=self)

# --- BOT CLASS & SETUP ---
class CoCBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.session, self.last_refresh_time, self.manual_lb_messages, self.lb_pages = None, 0.0, {}, {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession(); self.add_view(LeaderboardView(self)); await self.tree.sync()
        if not auto_update_leaderboard.is_running(): auto_update_leaderboard.start()

    async def close(self):
        if self.session: await self.session.close()
        await super().close()

bot = CoCBot()

@bot.event
async def on_ready(): logger.info(f'Logged in as {bot.user.name} with Async Requests & Slash Commands!')

# --- BACKGROUND TASK ---
@tasks.loop(minutes=5)
async def auto_update_leaderboard():
    try:
        embeds, unique_clans, tracked_players = await build_leaderboard_embeds(bot)
        bot.loop.create_task(process_clan_wars(bot, unique_clans, tracked_players))
        bot.last_refresh_time = time.time()
        config = await load_json_file(CONFIG_FILE, {})
        if config.get("channel_id") and config.get("message_id") and (channel := bot.get_channel(config["channel_id"])):
            message = await channel.fetch_message(config["message_id"])
            current = min(bot.lb_pages.get(config["message_id"], 0), len(embeds) - 1)
            await message.edit(embed=embeds[current], view=LeaderboardView(bot, embeds, current_page=current, message_id=config["message_id"]))
            logger.info("Auto-updated background leaderboard successfully.")
    except discord.NotFound: logger.warning("Leaderboard message not found. Clearing config."); await save_json_file(CONFIG_FILE, {})
    except Exception as e: logger.error(f"Failed to auto-update leaderboard: {e}")

# --- SLASH COMMANDS ---
@bot.tree.command(name='setleaderboard', description="Set up the automated updating leaderboard in this channel.")
@is_admin_or_owner()
async def set_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    config = await load_json_file(CONFIG_FILE, {})
    if config.get("channel_id") and config.get("message_id") and (old_channel := bot.get_channel(config["channel_id"])):
        try: await (await old_channel.fetch_message(config["message_id"])).delete()
        except: pass

    embeds, unique_clans, tracked_players = await build_leaderboard_embeds(bot)
    bot.loop.create_task(process_clan_wars(bot, unique_clans, tracked_players))
    bot.last_refresh_time, view = time.time(), LeaderboardView(bot, embeds)
    lb_message = await interaction.channel.send(embed=embeds[0], view=view)
    view.message_id, bot.lb_pages[lb_message.id] = lb_message.id, 0
    await save_json_file(CONFIG_FILE, {"channel_id": interaction.channel_id, "message_id": lb_message.id})
    await interaction.followup.send("✅ Automated leaderboard successfully set up in this channel!", ephemeral=True)

@bot.tree.command(name='add', description="Add a Clash of Clans player to the tracker.")
@is_admin_or_owner()
async def add_player(interaction: discord.Interaction, player_tag: str):
    await interaction.response.defer(ephemeral=True)
    clean_tag = player_tag.strip().lstrip('#').upper()
    status, data = await safe_fetch(interaction.client.session, f"https://api.clashofclans.com/v1/players/%23{clean_tag}", {'Authorization': f'Bearer {COC_TOKEN}'})
    
    if status == 200 and data:
        players = await load_json_file(PLAYERS_FILE, [])
        if clean_tag not in players:
            players.append(clean_tag); await save_json_file(PLAYERS_FILE, players)
            name_cache = await load_json_file(NAME_CACHE_FILE, {}); name_cache[clean_tag] = data.get('name', 'Unknown')
            await save_json_file(NAME_CACHE_FILE, name_cache)
            await interaction.followup.send(f"✅ Added **{data.get('name')}** to the server tracker!")
        else: await interaction.followup.send("⚠️ Player is already in the server tracker.")
    else: await interaction.followup.send("❌ Player not found or API is rate-limiting.")

@bot.tree.command(name='add_clan', description="Add all members of a Clash of Clans clan to the tracker.")
@is_admin_or_owner()
async def add_clan(interaction: discord.Interaction, clan_tag: str):
    await interaction.response.defer(ephemeral=True)
    status, data = await safe_fetch(interaction.client.session, f"https://api.clashofclans.com/v1/clans/%23{clan_tag.strip().lstrip('#').upper()}", {'Authorization': f'Bearer {COC_TOKEN}'})
    
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
    if interaction.channel_id in bot.manual_lb_messages:
        try: await (await interaction.channel.fetch_message(bot.manual_lb_messages[interaction.channel_id])).delete()
        except: pass
    embeds, unique_clans, tracked_players = await build_leaderboard_embeds(bot)
    bot.loop.create_task(process_clan_wars(bot, unique_clans, tracked_players))
    bot.last_refresh_time, view = time.time(), LeaderboardView(bot, embeds)
    msg = await interaction.followup.send(embed=embeds[0], view=view, wait=True)
    bot.manual_lb_messages[interaction.channel_id] = msg.id; view.message_id = msg.id; bot.lb_pages[msg.id] = 0

@command_leaderboard.error
async def command_leaderboard_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ The leaderboard command is on cooldown! Try again in **{int(error.retry_after)//60}m {int(error.retry_after)%60}s**.", ephemeral=True)

@bot.tree.command(name='profile', description="Look up a specific Clash of Clans player profile.")
@app_commands.autocomplete(player=player_autocomplete)
async def player_profile(interaction: discord.Interaction, player: str):
    await interaction.response.defer()
    if not (target_tag := await resolve_player_input(player)): return await interaction.followup.send("❌ Please provide a valid player name or tag.")
    
    legend_stats_cache, armies_db = await load_json_file(LEGEND_STATS_FILE, {}), await load_json_file(ARMIES_DB_FILE, {}) 
    p_dict, _, _, raw = await fetch_player_data(interaction.client.session, target_tag, {'Authorization': f'Bearer {COC_TOKEN}'}, {}, legend_stats_cache, armies_db)
    await asyncio.gather(save_json_file(LEGEND_STATS_FILE, legend_stats_cache), save_json_file(ARMIES_DB_FILE, armies_db))

    if raw:
        sw_count = (await load_json_file(SUPERWHOO_FILE, {})).get(f"#{target_tag}", {}).get("count", 0)
        embed = discord.Embed(title=f"{p_dict['emoji']} {raw.get('name')} (TH{p_dict['th']})", url=f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={target_tag}", color=discord.Color.blue())
        embed.add_field(name="Clan", value=f"{raw.get('clan', {}).get('name', 'No Clan')} ({raw.get('role', 'Member').capitalize() if raw.get('clan') else 'N/A'})", inline=False)
        embed.add_field(name="Trophies", value=f"{TROPHY_EMOJI} {raw.get('trophies')} (Best: {raw.get('bestTrophies')})", inline=True)
        embed.add_field(name="War Stars", value=f"⭐ {raw.get('warStars')}", inline=True)
        embed.add_field(name="Attacks Won", value=f"⚔️ {raw.get('attackWins')}", inline=True)
        embed.add_field(name="Superwhoo Fails", value=f"💔 {sw_count}", inline=True)
        embed.set_footer(text=f"Tag: #{target_tag}")
        await interaction.followup.send(embed=embed)
    else: await interaction.followup.send("❌ Could not find that player, or the API is currently unavailable.")

@bot.tree.command(name='armies', description="Shows the armies a player is currently using.")
@app_commands.autocomplete(player=player_autocomplete)
@app_commands.choices(mode=[app_commands.Choice(name="Ranked", value="ranked"), app_commands.Choice(name="Unranked", value="unranked")])
async def player_armies(interaction: discord.Interaction, player: str, mode: str = "ranked"):
    await interaction.response.defer()
    if not (target_tag := await resolve_player_input(player)): return await interaction.followup.send("❌ Please provide a valid player name or tag.")
        
    armies_db = await load_json_file(ARMIES_DB_FILE, {})
    if target_tag in armies_db and "armies" in armies_db[target_tag]:
        armies_db[target_tag]["ranked"] = armies_db[target_tag].pop("armies"); armies_db[target_tag].setdefault("unranked", {})
            
    has_tracked, armies_to_show, title_prefix = target_tag in armies_db and armies_db[target_tag].get(mode), {}, ""
    
    if has_tracked:
        armies_to_show, title_prefix, display_name = armies_db[target_tag][mode], "All-Time Tracked", (await load_json_file(NAME_CACHE_FILE, {})).get(target_tag, f"#{target_tag}")
    else:
        status, log_data = await safe_fetch(interaction.client.session, f"https://api.clashofclans.com/v1/players/%23{target_tag}/battlelog", {'Authorization': f'Bearer {COC_TOKEN}'})
        if status == 403: return await interaction.followup.send("🔒 This player's battle log is private.")
        if status != 200 or not log_data or 'items' not in log_data: return await interaction.followup.send("❌ Could not fetch battle log.")
            
        profile_status, profile_data = await safe_fetch(interaction.client.session, f"https://api.clashofclans.com/v1/players/%23{target_tag}", {'Authorization': f'Bearer {COC_TOKEN}'})
        display_name = profile_data.get('name', f"#{target_tag}") if profile_status == 200 else f"#{target_tag}"
        
        for b in log_data.get('items', []):
            if b.get('attack') and 'armyShareCode' in b and ("ranked" if b.get('battleType') in ['legend', 'homeVillage'] else "unranked") == mode:
                armies_to_show.setdefault(b['armyShareCode'], {"uses": 0, "total_dest": 0})
                armies_to_show[b['armyShareCode']]["uses"] += 1; armies_to_show[b['armyShareCode']]["total_dest"] += b.get('destructionPercentage', 0)
        title_prefix = "Recent Live"
        
    if not armies_to_show: return await interaction.followup.send(f"⚠️ No **{mode}** armies found for this player in their recent log.")
        
    sorted_armies = sorted(armies_to_show.items(), key=lambda x: x[1]['uses'], reverse=True)
    embed = discord.Embed(title=f"⚔️ {title_prefix} {'Ranked' if mode == 'ranked' else 'Unranked (War/Friendly)'} Armies for {display_name}", color=discord.Color.brand_green() if mode == "ranked" else discord.Color.orange())
    
    for i, (code, stats) in enumerate(sorted_armies[:5]):
        embed.add_field(name=f"Army {i+1} (Used {stats['uses']} times)", value=f"**Avg Destruction:** {stats['total_dest'] / stats['uses']:.1f}%\n**Composition:** {get_army_summary(code)}\n[🔗 Click to Copy Army In-Game](https://link.clashofclans.com/en?action=CopyArmy&army={code})", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='superwhoo', description="Shows the leaderboard or a specific player's 97-99% attack fails!")
@app_commands.autocomplete(player=player_autocomplete)
async def command_superwhoo(interaction: discord.Interaction, player: str = None):
    await interaction.response.defer()
    superwhoo_data = await load_json_file(SUPERWHOO_FILE, {})
    if not superwhoo_data: return await interaction.followup.send("🏆 The Superwhoo Leaderboard is currently empty. No painful misses yet!")

    if player:
        if not (target_tag := await resolve_player_input(player)): return await interaction.followup.send("❌ Please provide a valid player name or tag.")
        p_data = superwhoo_data.get(f"#{target_tag}")
        if not p_data or p_data['count'] == 0: return await interaction.followup.send(f"✅ Great news! **{(await load_json_file(NAME_CACHE_FILE, {})).get(target_tag, f'#{target_tag}')}** has no recorded fails.")

        history_text = ""
        for sig in reversed(p_data['seen']):
            parts = sig.split('_')
            try: time_str = datetime.datetime.strptime(parts[0], "%Y%m%dT%H%M%S.000Z").strftime("%b %d, %Y") if len(parts) >= 3 else "Unknown Date"
            except: time_str = "Unknown Date"
            history_text += f"• **{f'{parts[5]}%' if len(parts) >= 6 else '97-99%'}** ({parts[4] if len(parts) >= 6 else '?'}⭐) *(War Ended: {time_str})*\n"

        if len(history_text) > 4000: history_text = history_text[:4000] + "...\n*(Showing latest 50)*"
        embed = discord.Embed(title=f"💔 {p_data['name']}'s Superwhoo History", color=discord.Color.red())
        embed.add_field(name=f"Total Fails: {p_data['count']}", value=history_text, inline=False)
        return await interaction.followup.send(embed=embed)

    lb = sorted([{"name": d['name'], "count": d['count']} for d in superwhoo_data.values() if d['count'] > 0], key=lambda x: x['count'], reverse=True)
    if not lb: return await interaction.followup.send("🏆 The Superwhoo Leaderboard is currently empty. No painful misses yet!")

    desc_text = "".join(f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'`{i}.`'} **{discord.utils.escape_markdown(p['name'])}** - {p['count']} Superwhoo{'s' if p['count'] != 1 else ''}\n" for i, p in enumerate(lb[:50], 1))
    embed = discord.Embed(title="🏆 The Superwhoo Leaderboard 🏆", description="The ultimate wall of shame for 97-99% war attacks (Normal & CWL).", color=discord.Color.red())
    embed.add_field(name="Rankings", value=desc_text, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='auto_emojis', description="Generates the TROOP_EMOJIS dictionary code using your server's emojis.")
@is_admin_or_owner()
async def auto_emojis(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.guild: return await interaction.followup.send("❌ You must run this command inside a server, not in DMs.")
        
    base_troops = {0: "barbarian", 1: "archer", 2: "goblin", 3: "giant", 4: "wallbreaker", 5: "balloon", 6: "wizard", 7: "healer", 8: "dragon", 9: "pekka", 10: "minion", 11: "hogrider", 12: "valkyrie", 13: "golem", 15: "witch", 17: "lavahound", 22: "bowler", 23: "babydragon", 24: "miner", 26: "superbarbarian", 27: "superarcher", 28: "sneakygoblin", 35: "icehound", 51: "wallwrecker", 52: "battleblimp", 53: "yeti", 57: "superwallbreaker", 58: "icegolem", 59: "electrodragon", 62: "stoneslammer", 63: "infernodragon", 65: "dragonrider", 66: "superminion", 75: "siegebarracks", 80: "rocketballoon", 82: "headhunter", 87: "loglauncher", 91: "flameflinger", 92: "battledrill", 95: "electrotitan", 97: "apprenticewarden", 110: "rootrider", 132: "thrower", 147: "meteorgolem", 150: "furnace", 177: "smasher"}
    server_emojis = {e.name.lower().replace("avatar_", "").replace("_", ""): str(e) for e in interaction.guild.emojis}
    
    matches_found, output_str = 0, "TROOP_EMOJIS = {\n"
    for t_id, name in base_troops.items():
        output_str += f'    {t_id}: "{server_emojis.get(name, name)}",\n'
        if name in server_emojis: matches_found += 1
            
    await interaction.followup.send(f"✅ Found **{matches_found}** matching emojis! Paste contents into script.", file=discord.File(io.BytesIO((output_str + "}").encode('utf-8')), filename="troop_emojis.py"))

@bot.command(name='sync')
async def force_sync(ctx):
    if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.administrator:
        bot.tree.copy_global_to(guild=ctx.guild)
        await ctx.send(f"✅ Instantly synced {len(await bot.tree.sync(guild=ctx.guild))} slash commands to this server!")
    else: await ctx.send("❌ You don't have permission to do this.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure): await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
    else:
        logger.error(f"App command error: {error}")
        if not interaction.response.is_done(): await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)

if __name__ == '__main__': bot.run(DISCORD_TOKEN)