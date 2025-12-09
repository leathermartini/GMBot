# GMBot
# Current version
# MUST INCREMENT WHEN current_settings structure changes.
CURRENT_VERSION = '0.3.7'

import os
import json
import discord
import requests
import frontmatter
import re
import asyncio
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

#slash commands
gmbot_commands = bot.create_group('gmbot', 'GMBot Commands')

@gmbot_commands.command(description="Starts a new scene, changing the logging file.")
async def scene(ctx, new_scene: discord.Option(str, 'The name for the new scene.'), is_private: discord.Option(bool, 'Is this scene private', default=False)): #Creates slash command /scene
    current_settings['Current Scene'] = new_scene
    current_settings['Current Scene Start'] = datetime.now().strftime(current_settings['format'])
    current_settings['Current Scene Private'] = is_private
    write_gmbot_settings()
    if is_private: 
        prefix = "Private: "
    else:
        prefix = ""
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

@gmbot_commands.command(description="Sets the active logging channel. Must be server administrator.")
@discord.default_permissions(
    administrator=True,
)  # Only admins can changing the logging channel
async def set_game_channel(ctx):
    channel = ctx.channel
    debug_message(f"Setting active game channel to {channel.name} ({channel.id})")
    current_settings['Bot Channel'] = channel.id
    write_gmbot_settings()
    await ctx.respond(f"Set the active game channel to {channel.name}")

@gmbot_commands.command(description="Remebers a character by creating an entry in the Obsidian Vault.")
async def add_character(ctx, name: discord.Option(str, 'Name of the character to remember', required = True), player: discord.Option(bool, 'Is this a player character?', required = False, default = False), description: discord.Option(str, 'Description of this character', required=False, default='')):
    #Check if the character exists
    char_file = get_character_file(name)
    ensure_character_path_exists()
    #if not, save it
    if not char_file.is_file():
        char_file_text = get_default_char_template()
        debug_message(f"Got character template: {char_file_text}", current_settings['debug'])
        if player:
            char_file_text['🔹NPC'] = False
        else:
            char_file_text['🔹NPC'] = True
        if description:
            char_file_text['👁️‍🗨️Description'] = description
        try:
            with open(char_file, 'w', encoding='utf-8') as cf:
                cf.write(frontmatter.dumps(char_file_text))
                debug_message(f'Wrote character file for {name}', current_settings['debug'])
            await ctx.respond(f"Created Obsidian File for {name}.")
        except Exception as e:
            debug_message(f'Error writing character file {str(char_file)}: {e}', current_settings['debug'])
            await ctx.respond(f"Error creating character file, check logs.")
    else:
        await ctx.respond(f"File for {name} already exists, please edit through Obsidian.")

@gmbot_commands.command(descritpion="Gets a list of the current characters.")
async def get_characters(ctx, which_ones: discord.Option(str, "Which ones to return", choices=['All', 'PCs', 'NPCs'], default="All")):
    character_list = get_character_list()
    if character_list and which_ones == 'PCs':
        character_list = get_pc_list(character_list, True)
    elif character_list and which_ones == 'NPCs':
        character_list = get_pc_list(character_list, False)
    if character_list:
        results = "Found the characters:\n"
        results = results + "\n".join(character_list)
    else:
        results = "No characters found."
    await ctx.respond(results)

@gmbot_commands.command(description="Remebers a location by creating an entry in the Obsidian Vault.")
async def add_location(ctx, name: discord.Option(str, 'Name of the location to remember', required = True), location_type: discord.Option(str, 'What kind of location?', required = True, choices=['Region', 'City', 'Point'], default = 'Point'), description: discord.Option(str, 'Description of this location', required=False, default='')):
    #Check if the location exists
    loc_file = get_location_file(name)
    ensure_location_path_exists()
    #if not, save it
    if not loc_file.is_file():
        loc_file_text = get_default_loc_template()
        debug_message(f"Got location template: {loc_file_text}", current_settings['debug'])
        if location_type:
            loc_file_text['📌location_type'] = location_type
        if description:
            loc_file_text['👁️‍🗨️Description'] = description
        try:
            with open(loc_file, 'w', encoding='utf-8') as cf:
                cf.write(frontmatter.dumps(loc_file_text))
                debug_message(f'Wrote location file for {name}', current_settings['debug'])
            await ctx.respond(f"Created Obsidian File for {name}.")
        except Exception as e:
            debug_message(f'Error writing location file {str(loc_file)}: {e}', current_settings['debug'])
            await ctx.respond(f"Error creating location file, check logs.")
    else:
        await ctx.respond(f"File for {name} already exists, please edit through Obsidian.")

@gmbot_commands.command(descritpion="Gets a list of the current locations.")
async def get_locations(ctx, which_ones: discord.Option(str, "Which ones to return", choices=['Regions', 'Cities', 'Points', 'All'], default="All")):
    location_list = get_location_list()
    match which_ones:
        case 'Regions':
            to_get = 'Region'
        case 'Cities':
            to_get = 'City'
        case 'Points':
            to_get = 'Point'
        case _:
            to_get = 'All'
    if to_get != 'All': location_list = select_location_list(location_list, to_get)
    if location_list:
        results = "Found the locations:\n"
        results = results + "\n".join(location_list)
    else:
        results = "No locations found."
    await ctx.respond(results)    

@gmbot_commands.command(description="Remebers a item by creating an entry in the Obsidian Vault.")
async def add_item(ctx, name: discord.Option(str, 'Name of the item to remember', required = True), description: discord.Option(str, 'Description of this item', required=False, default='')):
    #Check if the item exists
    item_file = get_item_file(name)
    ensure_item_path_exists()
    #if not, save it
    if not item_file.is_file():
        item_file_text = get_default_item_template()
        debug_message(f"Got item template: {item_file_text}", current_settings['debug'])
        if description:
            item_file_text['👁️‍🗨️Description'] = description
        try:
            with open(item_file, 'w', encoding='utf-8') as cf:
                cf.write(frontmatter.dumps(item_file_text))
                debug_message(f'Wrote item file for {name}', current_settings['debug'])
            await ctx.respond(f"Created Obsidian File for {name}.")
        except Exception as e:
            debug_message(f'Error writing item file {str(item_file)}: {e}', current_settings['debug'])
            await ctx.respond(f"Error creating item file, check logs.")
    else:
        await ctx.respond(f"File for {name} already exists, please edit through Obsidian.")

@gmbot_commands.command(descritpion="Gets a list of the current items.")
async def get_items(ctx):
    item_list = get_item_list()
    if item_list:
        results = "Found the items:\n"
        results = results + "\n".join(item_list)
    else:
        results = "No items found."
    await ctx.respond(results)

#Watcher for AI prompts
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


#Character functions
def get_character_file(name):
    return get_character_path() /  clean_file_name(f"{name}.md")

def get_character_path():
    return Path(current_settings['Obsidian Vault Path']) / current_settings['Characters']

def get_character_list():
    ensure_character_path_exists()
    character_path = get_character_path()
    try:
        raw_characters = os.listdir(character_path)
        raw_characters.remove(current_settings['Character template'])  # Remove the template file from the list    
        characters = [i[:-3] for i in raw_characters] # Remove file extension from the character names
    except Exception as e:
        debug_message(f"Error getting character list: {e}")
        characters = []
    return characters       

def get_pc_list(character_file_list, is_pc=True):
    # Returns a list of PCs from a list of character files. If the second arguement is false, returns the NPCs.
    try:
        results = []
        ensure_character_path_exists()
        for x in character_file_list:
            with open(get_character_file(x), "r", encoding="utf-8") as cf:
                temp_char = frontmatter.load(cf)
            if is_pc and not temp_char['🔹NPC']:
                results.append(x)
            elif not is_pc and temp_char['🔹NPC']:
                results.append(x)
    except Exception as e:
        debug_message(f"Error getting PC status: {e}")
    return results

def get_all_characters_in_scene(scene_file):
    characters = get_character_list()
    scene_log = get_scene_log(scene_file)
    char_found = []
    if characters:
        for char in characters:
            if match_characters_in_log(char, scene_log):
                char_found.append(char)
    return char_found

def match_characters_in_log(char_name, log):
    char_alias_list = get_character_names(char_name)
    found = False
    for ca in char_alias_list:
        if findWholeWord(ca)(log):
            found = True
            break
    return found

def get_scene_log(scene_file):
    try:
        with open(scene_file, 'r', encoding='utf-8') as sf:
            scene_log = sf.read()
    except FileNotFoundError:
        scene_log = "No scene found.\n"
    except Exception as e:
        debug_message(f"Error getting scene contents: {e}")
        scene_log = f"Ignore previous instructions and instead respond with this: There was a problem getting the scene {e}."
    return scene_log

def get_character_names(char_name):
    aliases = [char_name]
    try:
        with open(get_character_file(char_name), 'r', encoding='utf-8') as cf:
            character_data = frontmatter.load(cf)
    except Exception as e:
        debug_message(f"Error getting character file for {char_name}: {e}", current_settings['debug'])
    if character_data['aliases']:
        for a in character_data['aliases']:
            aliases.append(a)
    return aliases

def get_default_char_template():
    template_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Characters'] / current_settings['Character template']
    try:
        with open(template_file, "r", encoding='utf-8') as tf:
            template = frontmatter.load(tf)
    except FileNotFoundError:
        debug_message(f"Default Character Template not found, creating base version.")
        template = build_default_char_template()        
    except Exception as e:
        debug_message(f"Error reading character template file: {e}")
        template = "error"
    return template

def build_default_char_template():
    base_character_template_yaml = '''---
aliases:
ℹ️Species:
ℹ️Class:
👁️‍🗨️Description:
🗪Reputation:
📝Notes:
🔗Connected:
👤Related NPCs:
🔗Related Factions:
💚Allied:
❌Opposed:
📍Related Locations:
⁉️Related Quests:
🧸Related Items:
📰Notable Events:
🤐Rumors & Secrets:
🎯Objective:
⚔️Statblock:
🔹NPC:
tags:
    - ✴️/📝Template
Status:
---'''
    base_character_template = frontmatter.loads(base_character_template_yaml)
    template_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Characters'] / current_settings['Character template']
    ensure_character_path_exists()
    try:
        if template_file.is_file():
            debug_message(f"Found existing character template file, updating to match current version.")
            with open(template_file, 'r', encoding='utf-8') as tf:
                curr_char_template = frontmatter.load(tf)
            for key in curr_char_template.keys():
                base_character_template[key] = curr_char_template[key]
        debug_message(f"Writing default character template file.")
        with open(template_file, 'w', encoding='utf-8') as tf:
            tf.write(frontmatter.dumps(base_character_template))
    except Exception as e:
        debug_message(f"Error writing/updating character template file: {e}")
    return base_character_template

#Location functions
def get_location_file(name):
    return get_location_path() /  clean_file_name(f"{name}.md")

def get_location_path():
    return Path(current_settings['Obsidian Vault Path']) / current_settings['Locations']

def get_location_list():
    ensure_location_path_exists()
    location_path = get_location_path()
    try:
        raw_locations = os.listdir(location_path)
        raw_locations.remove(current_settings['Location template'])  # Remove the template file from the list    
        locations = [i[:-3] for i in raw_locations] # Remove file extension from the location names
    except Exception as e:
        debug_message(f"Error getting location list: {e}")
        locations = []
    return locations
    
def get_default_loc_template():
    template_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Locations'] / current_settings['Location template']
    try:
        with open(template_file, "r", encoding='utf-8') as tf:
            template = frontmatter.load(tf)
    except FileNotFoundError:
        template = build_default_loc_template()
    except Exception as e:
        debug_message(f"Error reading location template file: {e}")
        template = "error"
    return template

def build_default_loc_template():
    base_location_template_yaml = '''---
aliases:
📌location_type:
👁️‍🗨️Description:
---'''
    base_location_template = frontmatter.loads(base_location_template_yaml)
    template_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Locations'] / current_settings['Location template']
    ensure_location_path_exists()
    try:
        if template_file.is_file():
            debug_message(f"Found existing location template file, updating to match current version.")
            with open(template_file, 'r', encoding='utf-8') as tf:
                curr_loc_template = frontmatter.load(tf)
            for key in curr_loc_template.keys():
                base_location_template[key] = curr_loc_template[key]
        debug_message(f"Writing default location template file.")
        with open(template_file, 'w', encoding='utf-8') as tf:
            tf.write(frontmatter.dumps(base_location_template))
    except Exception as e:
        debug_message(f"Error writing/updating location template file: {e}")
    return base_location_template

def select_location_list(location_list, to_get):
    # Returns just the specified type of locations from a list of locations.
    try:
        results = []
        ensure_location_path_exists()
        for x in location_list:
            with open(get_location_file(x), "r", encoding="utf-8") as lf:
                temp_loc = frontmatter.load(lf)
            if temp_loc['📌location_type'] == to_get:
                results.append(x)
    except Exception as e:
        debug_message(f"Error sorting locations: {e}")
    return results

def get_all_locations_in_scene(scene_file):
    locations = get_location_list()
    scene_log = get_scene_log(scene_file)
    loc_found = []
    if locations:
        for loc in locations:
            if match_locations_in_log(loc, scene_log):
                loc_found.append(loc)
    return loc_found

def match_locations_in_log(loc_name, log):
    loc_alias_list = get_location_names(loc_name)
    found = False
    for lo in loc_alias_list:
        if findWholeWord(lo)(log):
            found = True
            break
    return found

def get_location_names(loc_name):
    aliases = [loc_name]
    try:
        with open(get_location_file(loc_name), 'r', encoding='utf-8') as lf:
            location_data = frontmatter.load(lf)
    except Exception as e:
        debug_message(f"Error getting location file for {loc_name}: {e}", current_settings['debug'])
    if location_data['aliases']:
        for a in location_data['aliases']:
            aliases.append(a)
    return aliases

#item functions
def get_item_file(name):
    return get_item_path() /  clean_file_name(f"{name}.md")

def get_item_path():
    return Path(current_settings['Obsidian Vault Path']) / current_settings['Items']

def get_item_list():
    ensure_item_path_exists()
    item_path = get_item_path()
    try:
        raw_items = os.listdir(item_path)
        raw_items.remove(current_settings['Item template'])  # Remove the template file from the list    
        items = [i[:-3] for i in raw_items] # Remove file extension from the item names
    except Exception as e:
        debug_message(f"Error getting item list: {e}")
        items = []
    return items
    
def get_default_item_template():
    template_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Items'] / current_settings['Item template']
    try:
        with open(template_file, "r", encoding='utf-8') as tf:
            template = frontmatter.load(tf)
    except FileNotFoundError:
        template = build_default_item_template()
    except Exception as e:
        debug_message(f"Error reading item template file: {e}")
        template = "error"
    return template

def build_default_item_template():
    base_item_template_yaml = '''---
aliases:
👁️‍🗨️Description:
---'''
    base_item_template = frontmatter.loads(base_item_template_yaml)
    template_file = Path(current_settings['Obsidian Vault Path']) / current_settings['Items'] / current_settings['Item template']
    ensure_item_path_exists()
    try:
        if template_file.is_file():
            debug_message(f"Found existing litem template file, updating to match current version.")
            with open(template_file, 'r', encoding='utf-8') as tf:
                curr_item_template = frontmatter.load(tf)
            for key in curr_item_template.keys():
                base_item_template[key] = curr_item_template[key]
        debug_message(f"Writing default item template file.")
        with open(template_file, 'w', encoding='utf-8') as tf:
            tf.write(frontmatter.dumps(base_item_template))
    except Exception as e:
        debug_message(f"Error writing/updating item template file: {e}")
    return base_item_template

def get_all_items_in_scene(scene_file):
    items = get_item_list()
    scene_log = get_scene_log(scene_file)
    item_found = []
    if items:
        for it in items:
            if match_items_in_log(it, scene_log):
                item_found.append(it)
    return item_found

def match_items_in_log(item_name, log):
    item_alias_list = get_item_names(item_name)
    found = False
    for it in item_alias_list:
        if findWholeWord(it)(log):
            found = True
            break
    return found

def get_item_names(item_name):
    aliases = [item_name]
    try:
        with open(get_item_file(item_name), 'r', encoding='utf-8') as itf:
            item_data = frontmatter.load(itf)
    except Exception as e:
        debug_message(f"Error getting item file for {item_name}: {e}", current_settings['debug'])
    if item_data['aliases']:
        for a in item_data['aliases']:
            aliases.append(a)
    return aliases

# AI prompt building functions
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
    # Get the character info for the current scene
    characters = get_all_characters_in_scene(current_scene_file)
    char_info = ""
    if characters:
        for char in characters:
            try:
                with open(get_character_file(char), 'r', encoding='utf-8') as cf:
                    char_sheet = frontmatter.dumps(frontmatter.load(cf))
            except Exception as e:
                debug_message(f"Error getting character file for {char}: {e}", current_settings['debug'])    
                char_sheet = f"{char} has no further info."
            char_info = char_info + "\n\n" + char +"\n" + char_sheet  
    # Get locations
    locations = get_all_locations_in_scene(current_scene_file)
    loc_info = ""
    if locations:
        for loc in locations:
            try:
                with open(get_location_file(char), 'r', encoding='utf-8') as lf:
                    location_sheet = frontmatter.dumps(frontmatter.load(lf))
            except Exception as e:
                debug_message(f"Error getting character file for {loc}: {e}", current_settings['debug'])    
                location_sheet = f"{loc} has no further info."
            loc_info = loc_info + "\n\n" + loc +"\n" + location_sheet  
    # Get items
    items = get_all_items_in_scene(current_scene_file)
    item_info = ""
    if items:
        for it in items:
            try:
                with open(get_location_file(it), 'r', encoding='utf-8') as itf:
                    item_sheet = frontmatter.dumps(frontmatter.load(itf))
            except Exception as e:
                debug_message(f"Error getting character file for {it}: {e}", current_settings['debug'])    
                item_sheet = f"{it} has no further info."
            item_info = item_info + "\n\n" + it +"\n" + item_sheet  
    # Build and return a prompt with the scene information
    return f"{prompt}\n\nThe characters in this scene are:\n{char_info}\n\nThe locations in this scene are:\n{loc_info}\n\nThe important items in this scene are:\n{item_info}\n\nThe log of the current scene is, you should ignore the timestamps on the entries:\n{current_scene}"

# Other functions
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
            'Characters': 'Characters', # Folder for Characters
            'Items': 'Items', #Folder for Items
            'Locations': 'Locations', # Folder for Locations
            'Pinned': 'Pinned Messages', # Folder for Pinned Messages
            'format': '%Y-%m-%d %H-%M',
            'Settings Folder': 'Settings',
            'template': 'Settings/_Default Scene Template.md',
            'Character template': '_Character Template.md',
            'Location template': '_Location Template.md',
            'Item template': '_Item Template.md',
            'debug': False,
            # The following are pulled from globals
            'Current Scene': 'Initial Scene',
            'Current Scene Start': '0000-00-00 00-00',
            'Current Scene Private': False,
            'Bot Channel': int(os.getenv('BOT_CHANNEL_ID')),
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
    set_env_settings()
    return

def set_env_settings():
    """Overrides saved settings using ones set by env. Only for specific settings"""
    current_settings['Ollama Model'] = os.getenv('OLLAMA_MODEL')
    current_settings['Ollama URL'] = os.getenv('OLLAMA_URL')
    current_settings['Obsidian Vault Path'] = os.getenv('OBSIDIAN_VAULT_PATH')
    current_settings['Allowed Guild ids'] = os.getenv('ALLOWED_GUILD_ID')
    current_settings['Bot Discord Token'] = os.getenv('DISCORD_TOKEN')
    

def get_current_scene_path():
    filename = clean_file_name(f"{current_settings['Current Scene Start']} - {current_settings['Current Scene']}.md")

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

def ensure_character_path_exists():
    character_path = get_character_path()
    if not character_path.exists():
        os.makedirs(character_path, exist_ok=True)

def ensure_location_path_exists():
    location_path = get_location_path()
    if not location_path.exists():
        os.makedirs(location_path, exist_ok=True)

def ensure_item_path_exists():
    item_path = get_item_path()
    if not item_path.exists():
        os.makedirs(item_path, exist_ok=True)

def ensure_pinned_path_exists():
    pinned_path = get_pinned_path()
    if not pinned_path.exists():
        os.makedirs(pinned_path, exist_ok=True)

def get_pinned_path():
    return Path(current_settings['Obsidian Vault Path']) / current_settings['Pinned']

def write_pinned_message(message, file_to_append):
    # Make sure the paths exist
    ensure_pinned_path_exists()
    ensure_character_path_exists()
    ensure_location_path_exists()
    ensure_item_path_exists()
    # Format the message
    formatted_message = f"\n<{message.author.display_name}> {message.content}\n"
    try:
        if file_to_append.is_file():
            with open(file_to_append, 'a', encoding='utf-8') as pf:
                pf.write(formatted_message)
        else:
            with open(file_to_append, 'w', encoding='utf-8') as pf:
                pf.write(formatted_message)
    except Exception as e:
        debug_message(f"Error writing pinned message file {pinned_file}: {e}")

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

def clean_file_name(text):
    new_file_name = re.sub('\"', '', re.sub("\'", "", text))
    new_file_name = re.sub(r"[<>:/\|?*]", '-', new_file_name)
    return new_file_name

def findWholeWord(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search

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
    response = ''
    filepath = ''
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
        elif not payload.emoji.is_custom_emoji() and payload.emoji.name == '📌':
            #Save message to either an existing file or the pinned messages folder
            user = payload.member
            debug_message(f"Processing pinned message {message.id} for {user.display_name} content ({message.content})")
            dm_channel = await user.create_dm()
            await dm_channel.send(f"You want to pin this message:\n\n{message.content}\n\nDo you want to pin this message to a (**1**) **ch**aracter, (**2**) **lo**cation, or (**3**) **it**em, or just (**4**) **sa**ve it in the Vault?")
            res = await bot.wait_for(
                "message",
                check=lambda x: x.channel.id == dm_channel.id
                and user.id == x.author.id,
                timeout=60,
            )
            response = res.content
            # Add managing character/location/etc.
            if response == "1" or response[:2].lower() == "ch":
                #Get character list and offer
                character_list = get_character_list()
                if character_list:
                    character_list_message = "Select the character to append to by number:\n"
                    for x in range(len(character_list)):
                        character_list_message = character_list_message + f"(**{x+1}**) {character_list[x]}"
                        character_list_message = character_list_message + "\n"
                    await dm_channel.send(character_list_message)
                    # Offer character list and wait for number response
                    res2 = await bot.wait_for(
                        "message",
                        check=lambda y:y.channel.id == dm_channel.id and user.id == y.author.id,
                        timeout=60,
                    )
                    if res2: # If we got a response, validate it.
                        picked = int(res2.content) - 1
                        if picked >= 0 and picked < len(character_list):
                            await dm_channel.send(f"Appending message to character file for {character_list[picked]}")
                            filepath = get_character_file(character_list[picked])
                        else:
                            await dm_channel.send(f"Invalid response. Remove  Remove 📌 reaction and put it back to try again.")
                            return
            elif response == "2" or response[:2].lower() == "lo":
                # Get location list and offer
                location_list = get_location_list()
                if location_list:
                    location_list_message = "Select the location to append to by number:\n"
                    for x in range(len(location_list)):
                        location_list_message = location_list_message + f"(**{x+1}**) {location_list[x]}"
                        location_list_message = location_list_message + "\n"
                    await dm_channel.send(location_list_message)
                    # Send location list and wait for response.
                    res2 = await bot.wait_for(
                        "message",
                        check=lambda y:y.channel.id == dm_channel.id and user.id == y.author.id,
                        timeout=60,
                    )
                    if res2: # Validate response
                        picked = int(res2.content) - 1
                        if picked >= 0 and picked < len(location_list):
                            await dm_channel.send(f"Appending message to location file for {location_list[picked]}")
                            filepath = get_location_file(location_list[picked])             
                        else:
                            await dm_channel.send(f"Invalid response. Remove  Remove 📌 reaction and put it back to try again.")
                            return
            elif response == "3" or response[:2].lower() == "it":
                # Get item list and offer
                item_list = get_item_list()
                if item_list:
                    item_list_message = "Select the item to append to by number:\n"
                    for x in range(len(item_list)):
                        item_list_message = item_list_message + f"(**{x+1}**) {item_list[x]}"
                        item_list_message = item_list_message + "\n"
                    await dm_channel.send(item_list_message)
                    # Send location list and wait for response.
                    res2 = await bot.wait_for(
                        "message",
                        check=lambda y:y.channel.id == dm_channel.id and user.id == y.author.id,
                        timeout=60,
                    )
                    if res2: # Validate response
                        picked = int(res2.content) - 1
                        if picked >= 0 and picked < len(item_list):
                            await dm_channel.send(f"Appending message to item file for {item_list[picked]}")
                            filepath = get_item_file(item_list[picked])             
                        else:
                            await dm_channel.send(f"Invalid response. Remove  Remove 📌 reaction and put it back to try again.")
                            return
            elif response == "4" or response[:2].lower() == "sa":
                debug_message(f"Writing to pinned message file")
                await dm_channel.send(f"Writing message to pinned message folder in file {message.id}")
                filepath = get_pinned_path() / f"{message.id}.md"
            else:
                # Send message saying it's cancelling
                await dm_channel.send(f"Cancelling request. Message not saved. Remove 📌 reaction and put it back to try again.")
                return
    except asyncio.TimeoutError:
        await dm_channel.send(f"Cancelling request. Message not saved. Remove 📌 reaction and put it back to try again.")
        return
    except Exception as e:
        debug_message(f"Error on responding to reaction {payload.emoji}: {e}")
    if filepath:
        # When there's a file path costructed, append this message to the end of the file selected.
        write_pinned_message(message, filepath)

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