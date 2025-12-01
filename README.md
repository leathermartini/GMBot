# GMBot

A Discord bot logs Discord messages into an Obsidian file to be used as reference for an LLM GM

## Features
- Log all Discord messages in a particular channel to an Obsidian File, broken up by scene.
- /gmbot scene -> Creates a new scene, logging to a new file. Can mark a scene "private" and logging is disabled.
- /gmbot set_game_channel -> admin command to set the active game channel
- /gmbot ask_the_GM -> sends a prompt to an Ollama LLM with the default prompt, current scene log, and additional information
- /gmbot add_character/add_location/add_item -> Add important characters, locations, and items to the vault - further edits should be done in obsidian
- /gmbot get_characters/get_locations/get_items -> gets a list of known characters/locations/items


## Setup - TO UPDATE

1. Create a `.env` file with the following variables:
   ```env-example
   # Discord Bot Token (from Discord Developer Portal)
   DISCORD_TOKEN=<your API token>
   
   # Discord Server ID (from Discord server settings)
   # This is the ID of the server where the bot will operate
   # This is a security measure to prevent the bot from operating in other servers
   ALLOWED_GUILD_IDS=<your server ID>
   
   # Path to your Obsidian vault
   # For local Python deployment: Use absolute path to your vault
   # Example: /Users/username/Documents/ObsidianVault
   # For Docker deployment: leave this as /vault and map your local vault path to /vault in the container
   # Example: /Users/username/Documents/ObsidianVault:/vault
   OBSIDIAN_VAULT_PATH=<path to the obsidian vaul>
   
   # Channel ID of the Discord channel where the bot will operate
   BOT_CHANNEL_ID=<your channel id>
   
   # URL to Ollama instance
   OLLAMA_URL=<USL to ollama instance>
   # Default Ollama Model. Must be installed on Ollama server.
   OLLAMA_MODEL=<model to use, eg 'llama3.2:1b'>
   ```

## Deployment

### Python
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the bot:
   ```bash
   python bot.py
   ```

### Docker

#### Using Pre-built Image
1. Pull the image:
   ```bash
   docker pull ghcr.io/leathermartini/GMBot:main
   ```

2. Create a `.env` file with your configuration

3. Run the container:
   ```bash
   docker run -d \
     --name GMBot \
     -v /path/to/your/vault:/vault \
     --env-file .env \
     ghcr.io/yourusername/obsidian-discord:latest
   ```

#### Building Locally
1. Build the container:
   ```bash
   docker build -t GMBot .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name GMBot \
     -v /path/to/your/vault:/vault \
     --env-file .env \
     GMBot
   ```

#### Using Docker Compose
1. Download the `docker-compose.yml` file:
   ```bash
   curl -O https://raw.githubusercontent.com/leathermartini/GMBot/main/example.compose.yml docker-compose.yml
   ```

2. Edit the `OBSIDIAN_VAULT_PATH` in `.env` to match your local vault path

3. Run the bot:
   ```bash
   docker-compose up -d
   ```

## Usage

1. Send a message in your bot's channel
2. The bot will automatically save the message to the Obsidian vault, in the current scene.

## Coming Soon
- Update Scene
- Template for Obsidian file
- Add most of .env info into Obsidian file as a "config" page
