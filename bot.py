import os
import json
import discord
from discord.ext import commands
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)

# Constants
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_GUILD_IDS = os.getenv('ALLOWED_GUILD_IDS')
OBSIDIAN_VAULT_PATH = os.getenv('OBSIDIAN_VAULT_PATH')
BOT_CHANNEL_NAME = os.getenv('BOT_CHANNEL_NAME')
CURRENT_SCENE = os.getenv('CURRENT_SCENE')

def get_formatted_date():
    """Get today's date in a readable format for H1."""
    return datetime.now().strftime('%A, %B %d, %Y')

def get_gmbot_settings():
    # Todo - work out settings in vault for now, returns defaults
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    # settings_path = vault_path / '.obsidian' / 'daily-notes.json'
    

    # Default settings if plugin not installed or configured
    # May not use plugin above
    default_settings = {
        'folder': 'Scenes',  # Root of vault
        'format': 'YYYY-MM-DD',
        'template': 'Default Scene Template' + '.md'
    }

    #try:
    #    if settings_path.exists():
    #        print("Found daily notes settings file")
    #        with open(settings_path, 'r', encoding='utf-8') as f:
    #            settings = json.load(f)
    #            return {
    #                'folder': settings.get('folder', default_settings['folder']),
    #                'format': settings.get('format', default_settings['format']),
    #                'template': settings.get('template', default_settings['template'])
    #            }
    #except Exception as e:
    #    print(f"Error reading Daily Notes settings: {e}")

    return default_settings

def format_date_for_filename(date_format):
    """Convert Obsidian's moment.js date format to Python's strftime format."""
    # Basic conversion of common formats
    format_map = {
        'YYYY': '%Y',
        'YY': '%y',
        'MM': '%m',
        'DD': '%d',
        'HH': '%H',
        'mm': '%M',
        'ss': '%S'
    }

    # Replace each format token with its Python equivalent
    python_format = date_format
    for moment_fmt, py_fmt in format_map.items():
        python_format = python_format.replace(moment_fmt, py_fmt)

    return python_format

def get_current_scene_path():
    """Get the path to GMBot's notes using Obsidian's settings."""
    settings = get_gmbot_settings()

    # Convert moment.js format to Python's strftime format
    python_date_format = format_date_for_filename(settings['format'])
    filename = f"{CURRENT_SCENE}.md"

    # Construct the full path
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    if settings['folder']:
        # Create the folder if it doesn't exist
        print(f"GMBot Scene location specified, ensuring {vault_path}/{settings['folder']}/{filename} exists...")
        folder_path = vault_path / settings['folder']
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path / filename
    else:
        print(f"No GMBot Scene directory specified. Defaulting to {vault_path}/{filename}...")
        return vault_path / filename
    
def parse_template_string(template_string):
    """Parse Templated strings to include scene names and dates"""
    # Replaces {date} with the current date
    # Replaces {scene} with the value of CURRENT_SCENE
    # Add end of line
    return template_string.format(date=get_formatted_date(), scene=CURRENT_SCENE) + '\n'

def ensure_current_scene_exists(file_path):
    """Create the current scene if it doesn't exist, using template if available and enabled."""
    if not file_path.exists():
        settings = get_gmbot_settings()
        template_content = ""

        # Try to load template if specified
        if settings['template']:
            template_path = Path(OBSIDIAN_VAULT_PATH) / settings['template']
            try:
                if template_path.exists():
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
            except Exception as e:
                print(f"Error reading template: {e}")
            print(f"Current template string is: {template_content}")
            
        # If no template or template not found, use default
        if not template_content:
            template_content = f"# {get_formatted_date()}"

        # Parse the Scene template to add correct information
        template_content = parse_template_string(template_content)
            
        # Create the note
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(template_content)

def append_to_scene(file_path, author, content):
    """Append content to the current scene with timestamp."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    formatted_content = f"{current_time}: <{author}> {content}\n"

    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(formatted_content)
        return
    except Exception as e:
        print(f"Error modifying current scene: {e}")
        # Fallback to simple append if anything goes wrong
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(formatted_content)

def slugify(text):
    """Convert text to a URL and filename friendly format."""
    # Remove special characters and convert spaces to hyphens
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text

@bot.event
async def on_guild_join(guild):
    if guild.id not in ALLOWED_GUILD_IDS:
        await guild.leave()
        print(f"Left unauthorized server: {guild.name} ({guild.id})")

async def update_bot_status(status_type="default"):
    """Update bot status based on current action."""
    if status_type == "saving":
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="writing to current scene 💾"
            ),
            status=discord.Status.online
        )
    elif status_type == "creating":
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="with new files ✨"
            ),
            status=discord.Status.online
        )
    else:
        # Default status
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="waiting :clock:"
            ),
            status=discord.Status.online
        )

@bot.event
async def on_ready():
    # Set the default bot status
    await update_bot_status()

    # List all guilds bot has successfully joined
    for guild in bot.guilds:
        print(f'{bot.user} has connected to {guild.name}')
    print(f'{bot.user} is connected to {len(bot.guilds)} guild(s)')

@bot.event
async def on_message(message):
    # Only process messages in the bot's assigned channel
    if message.channel.name == BOT_CHANNEL_NAME and not message.author.bot:
        try:
            # Format the base content
            base_content = message.content
            # Get attachments
            if message.attachments:
                attachment_links = [f"[{a.filename}]({a.url})" for a in message.attachments]
                base_content += f"\n\nAttachments:\n" + "\n".join(f"- {link}" for link in attachment_links)
            # Default to daily note
            await update_bot_status("saving")
            print(f"Adding message {message.id} content to current scene")
            current_scene_path = get_current_scene_path()
            ensure_current_scene_exists(current_scene_path)
            append_to_scene(current_scene_path, message.author, base_content)    
            # Add complete emoji reaction and reset status
            await message.add_reaction('✅')
            await update_bot_status()
        except Exception as e:
            print(f"Error processing message: {e}")
            await message.add_reaction('❌')
            await update_bot_status()  # Reset status in case of error


# Run the bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("Discord token not found in .env file")
    if not OBSIDIAN_VAULT_PATH:
        raise ValueError("Obsidian vault path not found in .env file")

    print("Bot is starting...")
    bot.run(DISCORD_TOKEN)
