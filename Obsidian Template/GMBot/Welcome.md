\# GMBot



A Discord bot logs Discord messages into an Obsidian file to be used as reference for an LLM GM



\## Features

\- Log all Discord messages in a particular channel to an Obsidian File, broken up by scene.

\- /gmbot scene -> Creates a new scene, logging to a new file. Can mark a scene "private" and logging is disabled.

\- /gmbot set\_game\_channel -> admin command to set the active game channel

\- /gmbot ask\_the\_GM -> sends a prompt to an Ollama LLM with the default prompt, current scene log, and additional information

\- /gmbot add\_character/add\_location/add\_item -> Add important characters, locations, and items to the vault - further edits should be done in obsidian

\- /gmbot get\_characters/get\_locations/get\_items -> gets a list of known characters/locations/items





\## Setup - TO UPDATE



1\. Create a `.env` file with the following variables:

&nbsp;  ```env-example

&nbsp;  # Discord Bot Token (from Discord Developer Portal)

&nbsp;  DISCORD\_TOKEN=<your API token>

&nbsp;  

&nbsp;  # Discord Server ID (from Discord server settings)

&nbsp;  # This is the ID of the server where the bot will operate

&nbsp;  # This is a security measure to prevent the bot from operating in other servers

&nbsp;  ALLOWED\_GUILD\_IDS=<your server ID>

&nbsp;  

&nbsp;  # Path to your Obsidian vault

&nbsp;  # For local Python deployment: Use absolute path to your vault

&nbsp;  # Example: /Users/username/Documents/ObsidianVault

&nbsp;  # For Docker deployment: leave this as /vault and map your local vault path to /vault in the container

&nbsp;  # Example: /Users/username/Documents/ObsidianVault:/vault

&nbsp;  OBSIDIAN\_VAULT\_PATH=<path to the obsidian vaul>

&nbsp;  

&nbsp;  # Channel ID of the Discord channel where the bot will operate

&nbsp;  BOT\_CHANNEL\_ID=<your channel id>

&nbsp;  

&nbsp;  # URL to Ollama instance

&nbsp;  OLLAMA\_URL=<USL to ollama instance>

&nbsp;  # Default Ollama Model. Must be installed on Ollama server.

&nbsp;  OLLAMA\_MODEL=<model to use, eg 'llama3.2:1b'>

&nbsp;  ```



\## Deployment



\### Python

1\. Install dependencies:

&nbsp;  ```bash

&nbsp;  pip install -r requirements.txt

&nbsp;  ```



2\. Run the bot:

&nbsp;  ```bash

&nbsp;  python bot.py

&nbsp;  ```



\### Docker



\#### Using Pre-built Image

1\. Pull the image:

&nbsp;  ```bash

&nbsp;  docker pull ghcr.io/leathermartini/GMBot:main

&nbsp;  ```



2\. Create a `.env` file with your configuration



3\. Run the container:

&nbsp;  ```bash

&nbsp;  docker run -d \\

&nbsp;    --name GMBot \\

&nbsp;    -v /path/to/your/vault:/vault \\

&nbsp;    --env-file .env \\

&nbsp;    ghcr.io/yourusername/obsidian-discord:latest

&nbsp;  ```



\#### Building Locally

1\. Build the container:

&nbsp;  ```bash

&nbsp;  docker build -t GMBot .

&nbsp;  ```



2\. Run the container:

&nbsp;  ```bash

&nbsp;  docker run -d \\

&nbsp;    --name GMBot \\

&nbsp;    -v /path/to/your/vault:/vault \\

&nbsp;    --env-file .env \\

&nbsp;    GMBot

&nbsp;  ```



\#### Using Docker Compose

1\. Download the `docker-compose.yml` file:

&nbsp;  ```bash

&nbsp;  curl -O https://raw.githubusercontent.com/leathermartini/GMBot/main/example.compose.yml docker-compose.yml

&nbsp;  ```



2\. Edit the `OBSIDIAN\_VAULT\_PATH` in `.env` to match your local vault path



3\. Run the bot:

&nbsp;  ```bash

&nbsp;  docker-compose up -d

&nbsp;  ```



\## Usage



1\. Send a message in your bot's channel

2\. The bot will automatically save the message to the Obsidian vault, in the current scene.



\## Coming Soon

\- Update Scene

\- Template for Obsidian file

\- Add most of .env info into Obsidian file as a "config" page



