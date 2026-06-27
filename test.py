CURRENT_VERSION = '0.3.4'
import os
import json
import discord
import requests
import frontmatter
import re
from ollama import Client
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

if __name__ == "__main__":
    char_path = Path('C:\\Users\\leath\\Obsidian\\GMBot\\Characters')
    characters = os.listdir(char_path)
    for char in characters:
        if (char_path / char).is_file():
            with open(char_path / char, 'r', encoding='utf-8') as cf:
                print(char)
                print(cf.read())
    
