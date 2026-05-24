import asyncio
import json
import os
import asyncpg
from dotenv import load_dotenv

# Load environment variables (Make sure your .env has SUPABASE_DB_URL)
load_dotenv()
SUPABASE_DB_URL = os.getenv('SUPABASE_DB_URL')

# File names mapping to how your bot previously saved them
FILES = {
    'players': 'players.json',
    'lb_config': 'lb_config.json',
    'clan_info': 'clan_info_config.json',
    'trophy_cache': 'trophy_cache.json',
    'name_cache': 'name_cache.json',
    'legend_stats': 'legend_stats.json',
    'superwhoo': 'superwhoo_stats.json',
    'giveaways': 'giveaways.json'
}

def load_json(filepath, default):
    """Helper to safely load a JSON file if it exists."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading {filepath}: {e}")
            return default
    return default

async def migrate():
    if not SUPABASE_DB_URL:
        print("❌ ERROR: SUPABASE_DB_URL not found in .env file.")
        return

    print("🔄 Connecting to Supabase...")
    try:
        conn = await asyncpg.connect(SUPABASE_DB_URL)
        print("✅ Connected to database!\n")
        
        print("🏗️ Creating tables if they don't exist...")
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS players (tag TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS configs (name TEXT PRIMARY KEY, channel_id BIGINT, message_id BIGINT);
            CREATE TABLE IF NOT EXISTS cache (tag TEXT PRIMARY KEY, name TEXT, trophies INTEGER);
            CREATE TABLE IF NOT EXISTS legend_stats (tag TEXT PRIMARY KEY, data TEXT);
            CREATE TABLE IF NOT EXISTS superwhoo (tag TEXT PRIMARY KEY, data TEXT);
            CREATE TABLE IF NOT EXISTS giveaways (msg_id TEXT PRIMARY KEY, data TEXT);
        ''')
        print("✅ Tables ready!\n")
        
    except Exception as e:
        print(f"❌ Failed to connect or create tables: {e}")
        return

    # --- 1. MIGRATING PLAYERS ---
    print("⏳ Migrating players...")
    players = load_json(FILES['players'], [])
    if players:
        for tag in players:
            await conn.execute("INSERT INTO players (tag) VALUES ($1) ON CONFLICT DO NOTHING", tag)
        print(f"   ✅ Migrated {len(players)} players.")
    else:
        print("   ⏭️ No players to migrate.")

    # --- 2. MIGRATING CONFIGS ---
    print("\n⏳ Migrating configurations...")
    lb_config = load_json(FILES['lb_config'], {})
    if lb_config.get("channel_id"):
        await conn.execute(
            "INSERT INTO configs (name, channel_id, message_id) VALUES ($1, $2, $3) ON CONFLICT (name) DO UPDATE SET channel_id = EXCLUDED.channel_id, message_id = EXCLUDED.message_id",
            'lb_config', lb_config.get("channel_id"), lb_config.get("message_id")
        )
        print("   ✅ Migrated lb_config.")

    clan_info = load_json(FILES['clan_info'], {})
    if clan_info.get("channel_id"):
        await conn.execute(
            "INSERT INTO configs (name, channel_id, message_id) VALUES ($1, $2, $3) ON CONFLICT (name) DO UPDATE SET channel_id = EXCLUDED.channel_id, message_id = EXCLUDED.message_id",
            'clan_info', clan_info.get("channel_id"), clan_info.get("message_id")
        )
        print("   ✅ Migrated clan_info_config.")

    # --- 3. MIGRATING CACHES (Names and Trophies) ---
    print("\n⏳ Migrating caches...")
    name_cache = load_json(FILES['name_cache'], {})
    trophy_cache = load_json(FILES['trophy_cache'], {})
    
    # Merge all unique tags from both caches
    all_cached_tags = set(name_cache.keys()).union(set(trophy_cache.keys()))
    
    for tag in all_cached_tags:
        name = name_cache.get(tag)
        trophies = trophy_cache.get(tag)
        
        # Insert or update. If name or trophies is None, Postgres will just leave it null or update with null
        await conn.execute("""
            INSERT INTO cache (tag, name, trophies) 
            VALUES ($1, $2, $3) 
            ON CONFLICT (tag) DO UPDATE 
            SET name = COALESCE(EXCLUDED.name, cache.name), 
                trophies = COALESCE(EXCLUDED.trophies, cache.trophies)
        """, tag, name, trophies)
    if all_cached_tags:
        print(f"   ✅ Migrated data for {len(all_cached_tags)} cached profiles.")
    else:
        print("   ⏭️ No cache data to migrate.")

    # --- 4. MIGRATING COMPLEX JSON DATA (Legend Stats, Superwhoo, Giveaways) ---
    async def migrate_json_dict_table(table_name, file_key, key_col="tag"):
        print(f"\n⏳ Migrating {table_name}...")
        data_dict = load_json(FILES[file_key], {})
        if data_dict:
            for k, v in data_dict.items():
                await conn.execute(
                    f"INSERT INTO {table_name} ({key_col}, data) VALUES ($1, $2) ON CONFLICT ({key_col}) DO UPDATE SET data = EXCLUDED.data",
                    str(k), json.dumps(v)
                )
            print(f"   ✅ Migrated {len(data_dict)} entries into {table_name}.")
        else:
            print(f"   ⏭️ No data found for {table_name}.")

    await migrate_json_dict_table('legend_stats', 'legend_stats')
    await migrate_json_dict_table('superwhoo', 'superwhoo')
    await migrate_json_dict_table('giveaways', 'giveaways', key_col='msg_id')

    await conn.close()
    print("\n🎉 MIGRATION COMPLETE! You are now safe to delete your JSON files and start your updated bot.")

if __name__ == '__main__':
    asyncio.run(migrate())