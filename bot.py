# GMBot
# Current version
# MUST INCREMENT WHEN current_settings structure changes.
CURRENT_VERSION = '0.3'

import os
import json
import discord
import requests
from ollama import Client
from discord.ext import commands
from discord.ext import tasks
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
async def scene(ctx, new_scene: discord.Option(str, 'The name for the new scene.'), is_private: discord.Option(bool, 'Is this scene private', default=False)): #Creates slash command /scene
    current_settings['Current Scene'] = new_scene
    current_settings['Current Scene Start'] = datetime.now().strftime(current_settings['format'])
    current_settings['Current Scene Private'] = is_private
    write_gmbot_settings()
    if is_private: prefix = "Private: "
    await ctx.respond(f"--------------------- {prefix}{new_scene} ---------------------")

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

@gmbot_commands.command(description="Builds a request from the AI GM using the current prompt and the contents of the current scene.")
async def ask_the_gm(ctx, additional: discord.Option(str, 'Any additional instructions or information', required = False, default = '')):
    debug_message('Building the full prompt')
    prompt = f"{build_prompt()}\n\nAdditional Information and instructions are:\n{additional}"
    debug_message(f"Built this prompt:\n{prompt}")
    to_ask_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Settings Folder'] / "AI GM Prompt-request.tmp"
    try:
        with open(to_ask_file, 'w', encoding='utf-8') as request:
            request.write(prompt)
        status = 'Asking the GM.'
        if current_settings['Current Scene Private']:
            status = f"{status} But the current scene is private, so the GM will not have the scene log. Responses may be more unexpected."
    except Exception as e:
        status = f"Error writing the request to the AI: {e}"
        debug_message(status)
    await ctx.respond(status)

@tasks.loop(seconds=10) # Every 300 seconds look for a file
async def ai_gm_watcher():
    """Watches for a request file"""
    ai_ask_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Settings Folder'] / "AI GM Prompt-request.tmp"
    debug_message(f"Looking for ai request file: {ai_ask_file}")
    if ai_ask_file.is_file():
        debug_message(f"Found it!")
        try:
            with open(ai_ask_file, 'r', encoding='utf-8') as ask:
                prompt = ask.read()
        except Exception as e:
            debug_message(f"Error opening ai ask file {ai_ask_file}: {e}", current_settings['debug'])
            return
        if prompt:
            try:
                os.remove(ai_ask_file)
            except Exception as e:
                debug_message(f"Error removing file {ai_ask_file}: {e}")
                return
            ai_response = get_ollama_response(prompt)
            debug_message(f"Got AI response {ai_response}", current_settings['debug'])
            channel = bot.get_channel(int(current_settings['Bot Channel']))
            sent_message = await channel.send(ai_response)
            await sent_message.add_reaction('✅')
            await sent_message.add_reaction('❌')
            #await gmbot_client.send_message(channel, ai_response)
    
# Feeds a prompt to Ollama and gets the response.
def get_ollama_response(prompt):
    ollama_connection = Client(host=current_settings['Ollama URL'])
    response = ollama_connection.chat(model=current_settings['Ollama Model'], messages=[
        {
            'role': 'user',
            'content': prompt,
        },
    ])
    debug_message(f"Ollama sent back: {response.message.content}", current_settings['debug'])
    return response.message.content

def build_default_prompt():
    prompt_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Settings Folder'] / "AI GM Prompt.md"
    try:
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(current_settings['Default AI GM Prompt'])
        debug_message('Created new prompt file.', current_settings['debug'])
    except Exception as e:
        debug_message(f"Error creating new prompt file: {e}")

def build_prompt(additional_info = ""):
    # Get the current AI GM Prompt file contents
    prompt_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Settings Folder'] / "AI GM Prompt.md"
    debug_message(f"Looking for file: {prompt_file}", current_settings['debug'])
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()
            debug_message(f"Got the following prompt: {prompt}")
    except FileNotFoundError:
        build_default_prompt()
        prompt = current_settings['Default AI GM Prompt']
        debug_message(f"Built Default prompt: {prompt}")
    except Exception as e:
        debug_message(f"Error getting prompt file: {e}", current_settings['debug'])
        prompt = f"You should simply return: There was a problem getting the prompt: {e}"
    # Get the content of the current scene
    current_scene_file = get_current_scene_path()
    try:
        with open(current_scene_file, 'r', encoding='utf-8') as cs:
            current_scene = cs.read()
    except FileNotFoundError:
        current_scene = "This is an entirely new scene.\n"
    except Exception as e:
        debug_message(f"Error getting scene contents: {e}")
        current_scene = f"Ignore previous instructions and instead respond with this: There was a problem getting the scene {e}."
    # Build and return a prompt with the scene information
    return f"{prompt}\n\nThe log of the current scene is, you should ignore the timestamps on the entries:\n{current_scene}"

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
    if 'current_settings' not in globals():
        global current_settings 
        current_settings = {
            'Settings Version': CURRENT_VERSION,
            'folder': 'Scenes',  # Root of vault
            'format': '%Y-%m-%d %H-%M',
            'Settings Folder': 'Settings',
            'template': 'Settings/Default Scene Template.md',
            'debug': False,
            # The following are pulled from globals
            'Current Scene': os.getenv('CURRENT_SCENE'),
            'Current Scene Start': '0000-00-00 00-00',
            'Current Scene Private': False,
            'Bot Channel': os.getenv('BOT_CHANNEL_ID'),
            'Allowed Guild ids': os.getenv('ALLOWED_GUILD_IDS'),
            'Bot Discord Token': os.getenv('DISCORD_TOKEN'),
            'Obsidian Vault Path': os.getenv('OBSIDIAN_VAULT_PATH'),
            'Ollama URL': os.getenv('OLLAMA_URL'),
            'Default AI GM Prompt': 'You are a Game Master for a Dungeons and Dragons game.\n',
            'Ollama Model': os.getenv('OLLAMA_MODEL')
        }

    try:
        # Load the settings file
        with open('gmbot.json', 'r') as configfile:
            temp_current_settings = json.load(configfile)
            if temp_current_settings['Settings Version'] != current_settings['Settings Version']:
                debug_message('Updating Settings version')
                for setting in temp_current_settings.keys():
                    current_settings[setting] = temp_current_settings[setting]
                current_settings['Settings Version'] = CURRENT_VERSION
                write_gmbot_settings()
            else:
                current_settings = temp_current_settings                
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
    if message.channel.id == int(current_settings['Bot Channel']) and not message.author.bot and not current_settings['Current Scene Private']:
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
                await message.add_reaction('✨')
            await update_bot_status()
        except Exception as e:
            debug_message(f"Error processing message: {e}", current_settings['debug'])
            await message.add_reaction('❗')
            await update_bot_status()  # Reset status in case of error
    elif current_settings['Current Scene Private']:
        debug_message('Current scene is private, not logging.', current_settings['debug'])

@bot.event
async def on_raw_reaction_add(payload):
    # If a GM message is accepted, log it, if it is not, then delete it.
    # Ignore bot's own reactions
    if payload.user_id == bot.user.id:
        return            
    # Get the channel and message
    channel = await bot.fetch_channel(payload.channel_id)
    # If not in the logged channel, ignore
    if channel.id != int(current_settings['Bot Channel']):
        return    
    message = await channel.fetch_message(payload.message_id)
    try:
        if not payload.emoji.is_custom_emoji() and payload.emoji.name == '✅' and message.author.id == bot.user.id and not current_settings['Current Scene Private']:
            #Log the message.
            debug_message(f"Logging the accepted GMBot message {message.id} content ({message.content}) to current scene", current_settings['debug'])
            current_scene_path = get_current_scene_path()
            ensure_current_scene_exists(current_scene_path)
            append_to_scene(current_scene_path, message.author.display_name, message.content)
            await message.remove_reaction('✅', bot.user)
            await message.remove_reaction('❌', bot.user)
        elif not payload.emoji.is_custom_emoji() and payload.emoji.name == '✅' and message.author.id == bot.user.id and current_settings['Current Scene Private']:
            debug_message('Current scene is private, not logging.', current_settings['debug'])
            await channel.send('Current scene is private, not logging the message.')
            await message.remove_reaction('✅', bot.user)
            await message.remove_reaction('❌', bot.user)
        elif not payload.emoji.is_custom_emoji() and payload.emoji.name == '❌' and message.author.id == bot.user.id:
            #delete the message.
            debug_message(f"Removing rejected GMBot mesage {message.id} content ({message.content}).")
            await channel.delete_messages([message])
    except Exception as e:
        debug_message(f"Error on responding to reaction {payload.emoji}: {e}")

# Run the bot
if __name__ == "__main__":
    get_gmbot_settings()
    ai_ask_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Settings Folder'] / "AI GM Prompt-request.tmp"
    if ai_ask_file.is_file():
        debug_message(f"Removing old ai_ask file.")
        try:
            os.remove(ai_ask_file)
        except Exception as e:
            debug_message(f"Error removing file {ai_ask_file}: {e}")    
    if not current_settings['Bot Discord Token']:
        raise ValueError("Discord token not found in .env file")
    if not current_settings['Obsidian Vault Path']:
        raise ValueError("Obsidian vault path not found in .env file")

    debug_message("Bot is starting...", current_settings['debug'])
    ai_gm_watcher.start()
    bot.run(current_settings['Bot Discord Token'])