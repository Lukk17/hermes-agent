#!/usr/bin/env python3
"""
Publish Report to Discord using discord.py
Reads discord_messages.json and sends each message to Discord channel.
"""

import asyncio
import json
import os
from pathlib import Path

import discord

PROJECT_ROOT = Path("/home/node/.openclaw/workspace/crypto-monitor")
REPORT_DIR = PROJECT_ROOT / "data" / "reports"
CONFIG_FILE = PROJECT_ROOT / "config" / "settings.json"


def load_config():
    """Load config from project config file."""
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_discord_token():
    """Load Discord token from DISCORD_BOT_TOKEN environment variable."""
    return os.environ.get("DISCORD_BOT_TOKEN", "")


async def send_messages():
    config = load_config()
    channel_id = config.get("discord", {}).get("channel_id")
    token = load_discord_token()
    
    if not token:
        print("Error: Discord token not found in openclaw.json")
        return
    
    if not channel_id:
        print("Error: Channel ID not found in report_config.json")
        return
    
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        channel = client.get_channel(channel_id)
        
        if not channel:
            print(f"Channel {channel_id} not found!")
            await client.close()
            return
        
        messages = load_messages()
        print(f"Sending {len(messages)} messages...\n")
        
        for msg in messages:
            text = msg.get("text", "")
            image = msg.get("image")
            
            try:
                if image and text:
                    file = discord.File(image)
                    await channel.send(content=text, file=file)
                elif image:
                    file = discord.File(image)
                    await channel.send(file=file)
                elif text:
                    await channel.send(content=text)
                
                print(f"  ✓ {msg['number']}/{len(messages)}")
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"  ✗ {msg['number']}: {e}")
        
        print("\nDone!")
        await client.close()
    
    await client.start(token)


def load_messages():
    messages_file = REPORT_DIR / "discord_messages.json"
    if messages_file.exists():
        with open(messages_file) as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    asyncio.run(send_messages())
