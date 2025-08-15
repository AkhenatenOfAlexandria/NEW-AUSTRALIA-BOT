import discord
import logging
import csv
import io
from discord import app_commands
from discord.ext import commands
from datetime import datetime

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class UtilityCommands(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has Administrator role for utility commands"""
        if not any(role.name == "Administrator" for role in interaction.user.roles):
            await interaction.response.send_message("You need the Administrator role to use this command.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="log_messages", description="[ADMIN] Log all messages in a channel between two dates")
    @app_commands.describe(
        channel="Channel to log messages from",
        start_date="Start date in YYYY-MM-DDTHH:MM:SS format",
        end_date="End date in YYYY-MM-DDTHH:MM:SS format"
    )
    @app_commands.guilds(GUILD)
    async def log_messages(self, interaction: discord.Interaction, channel: discord.TextChannel, start_date: str, end_date: str):
        """
        Logs all messages in the specified channel between the given start and end datetimes.
        Datetime format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-08-01T12:00:00)
        """
        # Parse input datetimes
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            await interaction.response.send_message("❌ Invalid datetime format. Please use ISO 8601: YYYY-MM-DDTHH:MM:SS", ephemeral=True)
            return
        
        await interaction.response.send_message(f"Logging messages from {channel.mention}...")
        
        # Fetch messages within the period
        messages = []
        async for message in channel.history(limit=None, after=start_dt, before=end_dt, oldest_first=True):
            messages.append({
                "channel": str(channel),
                "datetime": message.created_at.isoformat(),
                "user_id": message.author.id,
                "user": str(message.author),
                "is_bot": message.author.bot,
                "content": message.content.replace('\n', ' '),
                "has_attachment": bool(message.attachments)
            })
            if not len(messages) % 100:
                logging.debug(f"Logged {len(messages)} messages...")
            if len(messages) >= 10000:
                await interaction.edit_original_response(content="Maximum 10,000 messages logged! Data incomplete!")
                break

        if not messages:
            await interaction.edit_original_response(content=f"No messages found in {channel.mention} from {start_dt} to {end_dt}.")
            return

        # Write to CSV in-memory
        buffer = io.StringIO()
        fieldnames = ["channel", "datetime", "user_id", "user", "is_bot", "has_attachment", "content"]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for msg in messages:
            writer.writerow(msg)
        buffer.seek(0)

        # Send CSV file back to Discord
        file_name = f"{channel.name}_{start_dt.date()}_{end_dt.date()}.csv"
        csv_file = discord.File(fp=io.BytesIO(buffer.getvalue().encode()), filename=file_name)
        await interaction.edit_original_response(content=f"✅ Logged {len(messages)} messages.", attachments=[csv_file])

    @app_commands.command(name="test", description="Test slash command")
    @app_commands.guilds(GUILD)
    async def test_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Slash commands are working!")

async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))