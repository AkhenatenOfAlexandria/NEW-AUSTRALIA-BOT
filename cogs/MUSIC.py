import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
from collections import deque
import logging
from typing import Optional, Dict, Any
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusicPlayer:
    """Represents a music player for a guild."""
    
    def __init__(self, bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue = deque()
        self.current_track = None
        self.is_looping = False
        self.volume = 0.5
        
    def add_track(self, track_info: Dict[str, Any]):
        """Add a track to the queue."""
        self.queue.append(track_info)
        
    def get_next_track(self) -> Optional[Dict[str, Any]]:
        """Get the next track from the queue."""
        if self.is_looping and self.current_track:
            return self.current_track
        return self.queue.popleft() if self.queue else None
        
    def clear_queue(self):
        """Clear the entire queue."""
        self.queue.clear()
        
    def skip_track(self):
        """Skip the current track."""
        if self.is_looping:
            self.is_looping = False
        
    def toggle_loop(self) -> bool:
        """Toggle loop mode and return the new state."""
        self.is_looping = not self.is_looping
        return self.is_looping

class Music(commands.Cog):
    """Enhanced music cog with slash commands and better functionality."""
    
    def __init__(self, bot):
        self.bot = bot
        self.players: Dict[int, MusicPlayer] = {}
        
        # YouTube-DL configuration
        self.ytdl_format_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'logtostderr': False,
        }
        
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -filter:a "volume=0.5"'
        }
        
        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_format_options)
    
    def get_player(self, guild_id: int) -> MusicPlayer:
        """Get or create a music player for a guild."""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self.bot, guild_id)
        return self.players[guild_id]
    
    async def extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract information from a URL or search query."""
        try:
            # Check if it's a URL or search query
            if not re.match(r'https?://', url):
                url = f"ytsearch:{url}"
            
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                lambda: self.ytdl.extract_info(url, download=False)
            )
            
            if 'entries' in data and data['entries']:
                return data['entries'][0]  # Get first search result
            return data
            
        except Exception as e:
            logger.error(f"Error extracting info from {url}: {e}")
            return None
    
    async def play_next(self, guild_id: int, text_channel):
        """Play the next track in the queue."""
        player = self.get_player(guild_id)
        guild = self.bot.get_guild(guild_id)
        
        if not guild or not guild.voice_client:
            return
        
        voice_client = guild.voice_client
        next_track = player.get_next_track()
        
        if not next_track:
            embed = discord.Embed(
                title="🎵 Queue Empty",
                description="No more tracks in the queue.",
                color=0x2F3136
            )
            await text_channel.send(embed=embed)
            return
        
        try:
            # Create audio source
            source = discord.FFmpegPCMAudio(
                next_track['url'], 
                **self.ffmpeg_options
            )
            
            player.current_track = next_track
            
            # Play the track
            def after_playing(error):
                if error:
                    logger.error(f'Player error: {error}')
                else:
                    # Schedule next track
                    coro = self.play_next(guild_id, text_channel)
                    future = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f'Error scheduling next track: {e}')
            
            voice_client.play(source, after=after_playing)
            
            # Send now playing message
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"[{next_track.get('title', 'Unknown')}]({next_track.get('webpage_url', '')})",
                color=0x00FF00
            )
            
            if next_track.get('duration'):
                minutes, seconds = divmod(next_track['duration'], 60)
                embed.add_field(
                    name="Duration", 
                    value=f"{minutes}:{seconds:02d}", 
                    inline=True
                )
            
            if next_track.get('uploader'):
                embed.add_field(
                    name="Uploader", 
                    value=next_track['uploader'], 
                    inline=True
                )
            
            queue_size = len(player.queue)
            embed.add_field(
                name="Queue", 
                value=f"{queue_size} track{'s' if queue_size != 1 else ''} remaining", 
                inline=True
            )
            
            if player.is_looping:
                embed.add_field(name="🔁 Loop", value="Enabled", inline=True)
            
            await text_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            embed = discord.Embed(
                title="❌ Playback Error",
                description=f"Failed to play track: {str(e)}",
                color=0xFF0000
            )
            await text_channel.send(embed=embed)
    
    # Slash command group
    music_group = app_commands.Group(name="music", description="Music player commands")
    
    @music_group.command(name="play", description="Play a song or add it to the queue")
    @app_commands.describe(query="YouTube URL or search query")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play a song or add it to the queue."""
        
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel to use this command!", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Connect to voice channel if not already connected
        voice_client = interaction.guild.voice_client
        if not voice_client:
            try:
                voice_client = await interaction.user.voice.channel.connect()
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Failed to connect to voice channel: {str(e)}", 
                    ephemeral=True
                )
                return
        
        # Extract track information
        track_info = await self.extract_info(query)
        if not track_info:
            await interaction.followup.send(
                "❌ Could not find or process that track!", 
                ephemeral=True
            )
            return
        
        player = self.get_player(interaction.guild.id)
        
        # Add to queue
        player.add_track(track_info)
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Added to Queue",
            description=f"[{track_info.get('title', 'Unknown')}]({track_info.get('webpage_url', '')})",
            color=0x00FF00
        )
        
        queue_position = len(player.queue)
        if not voice_client.is_playing():
            embed.add_field(name="Status", value="Playing now", inline=True)
        else:
            embed.add_field(name="Position in Queue", value=f"#{queue_position}", inline=True)
        
        if track_info.get('duration'):
            minutes, seconds = divmod(track_info['duration'], 60)
            embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)
        
        await interaction.followup.send(embed=embed)
        
        # Start playing if nothing is currently playing
        if not voice_client.is_playing():
            await self.play_next(interaction.guild.id, interaction.channel)
    
    @music_group.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        """Skip the current track."""
        
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message(
                "❌ Nothing is currently playing!", 
                ephemeral=True
            )
            return
        
        player = self.get_player(interaction.guild.id)
        player.skip_track()
        voice_client.stop()
        
        embed = discord.Embed(
            title="⏭️ Track Skipped",
            description="Moving to the next track...",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)
    
    @music_group.command(name="queue", description="Show the current music queue")
    async def queue(self, interaction: discord.Interaction):
        """Display the current music queue."""
        
        player = self.get_player(interaction.guild.id)
        
        if not player.current_track and not player.queue:
            await interaction.response.send_message(
                "❌ The queue is empty!", 
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎵 Music Queue",
            color=0x2F3136
        )
        
        # Current track
        if player.current_track:
            current_title = player.current_track.get('title', 'Unknown')
            embed.add_field(
                name="🎵 Now Playing",
                value=f"[{current_title}]({player.current_track.get('webpage_url', '')})",
                inline=False
            )
        
        # Queue
        if player.queue:
            queue_text = ""
            for i, track in enumerate(list(player.queue)[:10], 1):  # Show first 10
                title = track.get('title', 'Unknown')[:50]  # Truncate long titles
                queue_text += f"{i}. {title}\n"
            
            if len(player.queue) > 10:
                queue_text += f"... and {len(player.queue) - 10} more tracks"
            
            embed.add_field(
                name=f"📋 Up Next ({len(player.queue)} tracks)",
                value=queue_text or "Empty",
                inline=False
            )
        
        # Status info
        status_info = []
        if player.is_looping:
            status_info.append("🔁 Loop: ON")
        
        if status_info:
            embed.add_field(name="Status", value=" | ".join(status_info), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @music_group.command(name="clear", description="Clear the music queue")
    async def clear(self, interaction: discord.Interaction):
        """Clear the music queue."""
        
        player = self.get_player(interaction.guild.id)
        queue_size = len(player.queue)
        
        if queue_size == 0:
            await interaction.response.send_message(
                "❌ The queue is already empty!", 
                ephemeral=True
            )
            return
        
        player.clear_queue()
        
        embed = discord.Embed(
            title="🗑️ Queue Cleared",
            description=f"Removed {queue_size} track{'s' if queue_size != 1 else ''} from the queue.",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)
    
    @music_group.command(name="loop", description="Toggle loop mode for the current track")
    async def loop(self, interaction: discord.Interaction):
        """Toggle loop mode for the current track."""
        
        player = self.get_player(interaction.guild.id)
        
        if not player.current_track:
            await interaction.response.send_message(
                "❌ No track is currently playing!", 
                ephemeral=True
            )
            return
        
        is_looping = player.toggle_loop()
        
        embed = discord.Embed(
            title="🔁 Loop Mode",
            description=f"Loop is now **{'ON' if is_looping else 'OFF'}**",
            color=0x00FF00 if is_looping else 0xFF0000
        )
        
        if is_looping and player.current_track:
            embed.add_field(
                name="Looping Track",
                value=player.current_track.get('title', 'Unknown'),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @music_group.command(name="stop", description="Stop music and disconnect from voice channel")
    async def stop(self, interaction: discord.Interaction):
        """Stop music and disconnect from voice channel."""
        
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(
                "❌ Not connected to a voice channel!", 
                ephemeral=True
            )
            return
        
        player = self.get_player(interaction.guild.id)
        player.clear_queue()
        player.current_track = None
        player.is_looping = False
        
        await voice_client.disconnect()
        
        embed = discord.Embed(
            title="⏹️ Music Stopped",
            description="Disconnected from voice channel and cleared queue.",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)
    
    @music_group.command(name="nowplaying", description="Show information about the current track")
    async def nowplaying(self, interaction: discord.Interaction):
        """Show information about the current track."""
        
        player = self.get_player(interaction.guild.id)
        
        if not player.current_track:
            await interaction.response.send_message(
                "❌ No track is currently playing!", 
                ephemeral=True
            )
            return
        
        track = player.current_track
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"[{track.get('title', 'Unknown')}]({track.get('webpage_url', '')})",
            color=0x00FF00
        )
        
        if track.get('thumbnail'):
            embed.set_thumbnail(url=track['thumbnail'])
        
        if track.get('duration'):
            minutes, seconds = divmod(track['duration'], 60)
            embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)
        
        if track.get('uploader'):
            embed.add_field(name="Uploader", value=track['uploader'], inline=True)
        
        if track.get('view_count'):
            embed.add_field(name="Views", value=f"{track['view_count']:,}", inline=True)
        
        if player.is_looping:
            embed.add_field(name="🔁 Loop", value="Enabled", inline=True)
        
        queue_size = len(player.queue)
        embed.add_field(
            name="Queue", 
            value=f"{queue_size} track{'s' if queue_size != 1 else ''} remaining", 
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Setup function to add the cog to the bot."""
    cog = Music(bot)
    await bot.add_cog(cog)
    
    # Sync the slash commands to your guild
    GUILD_ID = 574731470900559872  # Replace with your server's ID
    guild = discord.Object(id=GUILD_ID)
    bot.tree.add_command(cog.music_group, guild=guild)