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

bot = discord.Bot(intents=intents)

gmbot_commands = bot.create_group('gmbot', 'GMBot Commands')

@gmbot_commands.command(description="Starts a new scene, changing the logging file.")
async def scene(ctx, new_scene: discord.Option(str)): #Creates slash command /scene
    current_settings['Current Scene'] = new_scene
    current_settings['Current Scene Start'] = datetime.now().strftime(current_settings['format'])
    write_gmbot_settings()
    await ctx.respond(f"--------------------- {new_scene} ---------------------")

@gmbot_commands.command(description="Toggles debugging to the Obsidian vault, in the Settings folder.")
async def debug(ctx): #Creates slash command /gmbdebug
    debug_message('Toggling debug value')
    current_settings['debug'] = not current_settings['debug'] 
    if current_settings['debug']:
        message = 'Debug turned on.'
    else:
        message = 'Debug turned off.'
    write_gmbot_settings()
    await ctx.respond(message)

# Constants
# DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
# ALLOWED_GUILD_IDS = os.getenv('ALLOWED_GUILD_IDS')
# OBSIDIAN_VAULT_PATH = os.getenv('OBSIDIAN_VAULT_PATH')
# BOT_CHANNEL_NAME = os.getenv('BOT_CHANNEL_NAME')
# CURRENT_SCENE = os.getenv('CURRENT_SCENE')
# DEBUG_ON = False

def debug_message(message, debug_log=False):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    file_path = Path(current_settings['Obsidian Vault Path']) / current_settings['Settings Folder'] / "Debug Log.md"
    formatted_content = f"{current_time}: {message}\n"
    print(formatted_content)
    if debug_log:
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(formatted_content)
            return
        except FileNotFoundError:
            # Write to create the file.
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('GMBot Debug Log\n')
                f.write(formatted_content)
        except Exception as e:
            print(f"Error writing debug log: {e}")

def get_formatted_date():
    """Get today's date in a readable format for H1."""
    return datetime.now().strftime('%A, %B %d, %Y')

def write_gmbot_settings():
    # writes current settings to the gmbot.json file
    try:
        with open('gmbot.json', 'w') as configfile:
                json.dump(current_settings, configfile)
        debug_message('Wrote settings to config file', current_settings['debug'])
    except Exception as err:
        debug_message(f"Error writing config file: {Err}", current_settings['debug'])

def get_gmbot_settings():
    # Default settings
    global current_settings
    if 'current_settings' not in globals():
        current_settings = {
            'folder': 'Scenes',  # Root of vault
            'format': '%Y-%m-%d %H-%M',
            'Settings Folder': 'Settings',
            'template': 'Settings/Default Scene Template.md',
            'debug': False,
            # The following are pulled from globals
            'Current Scene': os.getenv('CURRENT_SCENE'),
            'Current Scene Start': '0000-00-00 00-00',
            'Bot Channel': os.getenv('BOT_CHANNEL_NAME'),
            'Allowed Guild ids': os.getenv('ALLOWED_GUILD_IDS'),
            'Bot Discord Token': os.getenv('DISCORD_TOKEN'),
            'Obsidian Vault Path': os.getenv('OBSIDIAN_VAULT_PATH')
        }

    try:
        # Load the settings file
        with open('gmbot.json', 'r') as configfile:
            current_settings = json.load(configfile)
        #Load settings into Globals.
        debug_message('Found config file and loaded it.', current_settings['debug'])
    except FileNotFoundError:
        # Settings file doesn't exist, so create it.
        write_gmbot_settings()
        debug_message('No config file found, creating from defaults.', current_settings['debug'])
    except Exception as err:
        debug_message(f"Error reading GMBot config file: {err}", current_settings['debug'])
    
    return

def get_current_scene_path():
    filename = f"{current_settings['Current Scene Start']} - {current_settings['Current Scene']}.md"

    # Construct the full path
    vault_path = Path(current_settings['Obsidian Vault Path'])
    if current_settings['folder']:
        # Create the folder if it doesn't exist
        debug_message(f"GMBot Scene location specified, ensuring {vault_path}/{current_settings['folder']}/{filename} exists...", current_settings['debug'])
        folder_path = vault_path / current_settings['folder']
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path / filename
    else:
        debug_message(f"No GMBot Scene directory specified. Defaulting to {vault_path}/{filename}...", current_settings['debug'])
        return vault_path / filename
    
def parse_template_string(template_string):
    """Parse Templated strings to include scene names and dates"""
    # Replaces {date} with the current date
    # Replaces {scene} with the value of current_settings['Current Scene']
    # Add end of line
    return template_string.format(date=get_formatted_date(), scene=current_settings['Current Scene']) + '\n'

def ensure_current_scene_exists(file_path):
    """Create the current scene if it doesn't exist, using template if available and enabled."""
    if not file_path.exists():
        template_content = ""

        # Try to load template if specified
        if current_settings['template']:
            template_path = Path(current_settings['Obsidian Vault Path']) / current_settings['template']
            try:
                if template_path.exists():
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
            except Exception as e:
                debug_message(f"Error reading template: {e}", current_settings['debug'])
            debug_message(f"Current template string is: {template_content}", current_settings['debug'])
            
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
        debug_message(f"Error modifying current scene: {e}", current_settings['debug'])
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
    if guild.id not in current_settings['Allowed Guild ids']:
        await guild.leave()
        debug_message(f"Left unauthorized server: {guild.name} ({guild.id})", current_settings['debug'])

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
        debug_message(f'{bot.user} has connected to {guild.name}', current_settings['debug'])
    debug_message(f'{bot.user} is connected to {len(bot.guilds)} guild(s)', current_settings['debug'])

@bot.event
async def on_message(message):
    # Only process messages in the bot's assigned channel
    if message.channel.name == current_settings['Bot Channel'] and not message.author.bot:
        try:
            # Format the base content
            base_content = message.content
            # Get attachments
            if message.attachments:
                attachment_links = [f"[{a.filename}]({a.url})" for a in message.attachments]
                base_content += f"\n\nAttachments:\n" + "\n".join(f"- {link}" for link in attachment_links)
            # Default to daily note
            await update_bot_status("saving")
            debug_message(f"Adding message {message.id} content ({message.content}) to current scene", current_settings['debug'])
            current_scene_path = get_current_scene_path()
            ensure_current_scene_exists(current_scene_path)
            append_to_scene(current_scene_path, message.author.display_name, base_content)    
            # Add complete emoji reaction and reset status
            if current_settings['debug']:
                await message.add_reaction('✅')
            await update_bot_status()
        except Exception as e:
            debug_message(f"Error processing message: {e}", current_settings['debug'])
            await message.add_reaction('❌')
            await update_bot_status()  # Reset status in case of error

# Run the bot
if __name__ == "__main__":
    get_gmbot_settings()
    if not current_settings['Bot Discord Token']:
        raise ValueError("Discord token not found in .env file")
    if not current_settings['Obsidian Vault Path']:
        raise ValueError("Obsidian vault path not found in .env file")

    debug_message("Bot is starting...", current_settings['debug'])
    bot.run(current_settings['Bot Discord Token'])
