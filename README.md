# GMBot

A Discord bot logs Discord messages into an Obsidian file to be used as reference for an LLM GM

## Features
- Log all Discord messages in a particular channel to an Obsidian File, broken up by scene.
- Command to change scene - pending

## Setup - TO UPDATE

1. Create a `.env` file with the following variables:
   ```env-example
    # Discord Bot Token (from Discord Developer Portal)
    DISCORD_TOKEN=your_discord_bot_token

    # Discord Server ID (from Discord server settings)
    # This is the ID of the server where the bot will operate
    # This is a security measure to prevent the bot from operating in other servers
    ALLOWED_GUILD_IDS=your_discord_server_id

    # Path to your Obsidian vault
    # For local Python deployment: Use absolute path to your vault
    # Example: /Users/username/Documents/ObsidianVault
    # For Docker deployment: leave this as /vault and map your local vault path to /vault in the container
    # Example: /Users/username/Documents/ObsidianVault:/vault
    OBSIDIAN_VAULT_PATH=path_to_your_obsidian_vault

    # Name of the Discord channel where the bot will operate
    # This should match exactly (case-sensitive)
    BOT_CHANNEL_NAME=your_channel_name

    # Optional: Section in daily notes where content should be appended
    # If specified, new content will be added under this section header
    # Example: "Daily Log" will append content under "# Daily Log" or "## Daily Log"
    CUREENT_SCENE=Scene_1
   ```

2. Create a channel with the name you specified in `BOT_CHANNEL_NAME`

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
   docker pull ghcr.io/sloraris/obsidian-discord:latest
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
