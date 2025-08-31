import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
from collections import deque
import logging
from typing import Optional, Dict, Any
import re
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YTDLSource(discord.PCMVolumeTransformer):
    """Audio source for YouTube-DL."""
    
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'extractaudio': True,
        'audioformat': 'mp3',
        'audioquality': 0,
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume=volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.duration = data.get('duration')
        self.uploader = data.get('uploader')
        self.webpage_url = data.get('webpage_url')

    @classmethod
    async def create_source(cls, search: str, *, loop: asyncio.AbstractEventLoop = None):
        """Create an audio source from a search query or URL."""
        loop = loop or asyncio.get_event_loop()
        
        try:
            # Handle search vs URL
            if not re.match(r'https?://', search):
                search = f"ytsearch:{search}"

            data = await loop.run_in_executor(
                None, lambda: cls.ytdl.extract_info(search, download=False)
            )

            if 'entries' in data:
                # Take first item from a playlist or search results
                data = data['entries'][0] if data['entries'] else None

            if not data:
                raise Exception("Could not retrieve track information")

            filename = data['url']
            return cls(discord.FFmpegPCMAudio(filename, **cls.FFMPEG_OPTIONS), data=data)

        except Exception as e:
            logger.error(f"Error creating source from {search}: {e}")
            raise

class MusicPlayer:
    """Music player for a guild."""
    
    def __init__(self, bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue = deque()
        self.current = None
        self.next = asyncio.Event()
        self.volume = 0.5
        self.loop_current = False
        self.loop_queue = False
        
        # Create the audio player task
        bot.loop.create_task(self.audio_player_task())

    async def audio_player_task(self):
        """Main audio player loop."""
        while True:
            self.next.clear()
            
            # Get next track
            if self.loop_current and self.current:
                # Don't change current track, just replay it
                pass
            elif self.queue:
                # Get next track from queue
                self.current = self.queue.popleft()
            else:
                # No more tracks
                self.current = None
            
            if not self.current:
                # No track to play, wait for next
                await self.next.wait()
                continue

            try:
                # Create audio source
                source = await YTDLSource.create_source(
                    self.current['search'], 
                    loop=self.bot.loop
                )
                source.volume = self.volume

                # Get voice client
                guild = self.bot.get_guild(self.guild_id)
                if not guild or not guild.voice_client:
                    break

                voice_client = guild.voice_client
                
                # Update current with actual track data
                self.current.update({
                    'title': source.title,
                    'url': source.url,
                    'thumbnail': source.thumbnail,
                    'duration': source.duration,
                    'uploader': source.uploader,
                    'webpage_url': source.webpage_url
                })

                # Send now playing message
                if 'channel' in self.current:
                    await self.send_now_playing(self.current['channel'])

                # Play the track
                voice_client.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set) if not e else logger.error(f'Player error: {e}'))
                
                # Wait for track to finish
                await self.next.wait()

                # If loop queue is enabled and no more tracks, re-add all played tracks
                if self.loop_queue and not self.queue and not self.loop_current:
                    # This is a simplified implementation - you might want to track played songs
                    pass

            except Exception as e:
                logger.error(f"Error in audio player task: {e}")
                await self.next.wait()

    async def send_now_playing(self, channel):
        """Send now playing embed."""
        if not self.current:
            return

        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"[{self.current.get('title', 'Unknown')}]({self.current.get('webpage_url', '')})",
            color=0x00FF00
        )

        if self.current.get('thumbnail'):
            embed.set_thumbnail(url=self.current['thumbnail'])

        if self.current.get('duration'):
            minutes, seconds = divmod(self.current['duration'], 60)
            embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)

        if self.current.get('uploader'):
            embed.add_field(name="Uploader", value=self.current['uploader'], inline=True)

        queue_size = len(self.queue)
        embed.add_field(
            name="Queue", 
            value=f"{queue_size} track{'s' if queue_size != 1 else ''} remaining", 
            inline=True
        )

        if self.loop_current:
            embed.add_field(name="🔂 Loop Track", value="Enabled", inline=True)
        elif self.loop_queue:
            embed.add_field(name="🔁 Loop Queue", value="Enabled", inline=True)

        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error sending now playing message: {e}")

    def add_track(self, search: str, channel, user):
        """Add a track to the queue."""
        track_info = {
            'search': search,
            'channel': channel,
            'user': user,
            'title': 'Loading...'  # Will be updated when played
        }
        self.queue.append(track_info)
        self.next.set()  # Wake up the audio player
        return len(self.queue)

    def skip(self):
        """Skip current track."""
        if self.loop_current:
            self.loop_current = False
        self.next.set()

    def clear_queue(self):
        """Clear the queue."""
        self.queue.clear()

    def toggle_loop_current(self):
        """Toggle current track loop."""
        self.loop_current = not self.loop_current
        if self.loop_current:
            self.loop_queue = False  # Can't have both
        return self.loop_current

    def toggle_loop_queue(self):
        """Toggle queue loop."""
        self.loop_queue = not self.loop_queue
        if self.loop_queue:
            self.loop_current = False  # Can't have both
        return self.loop_queue

    def set_volume(self, volume: float):
        """Set player volume."""
        self.volume = max(0.0, min(1.0, volume))

class Music(commands.Cog):
    """Enhanced music cog with slash commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        """Get or create a music player for a guild."""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self.bot, guild_id)
        return self.players[guild_id]

    def cleanup_player(self, guild_id: int):
        """Clean up a player when no longer needed."""
        if guild_id in self.players:
            del self.players[guild_id]

    # Slash command group
    music = app_commands.Group(name="music", description="Music player commands")

    @music.command(name="play", description="Play a song or add it to the queue")
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
                    f"❌ Failed to connect to voice channel: {str(e)}"
                )
                return

        # Get player and add track
        player = self.get_player(interaction.guild.id)
        queue_position = player.add_track(query, interaction.channel, interaction.user)

        # Send confirmation
        embed = discord.Embed(
            title="✅ Added to Queue",
            description=f"Search: `{query}`",
            color=0x00FF00
        )

        if player.current:
            embed.add_field(name="Position in Queue", value=f"#{queue_position}", inline=True)
        else:
            embed.add_field(name="Status", value="Playing now", inline=True)

        await interaction.followup.send(embed=embed)

    @music.command(name="skip", description="Skip the current track")
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
        player.skip()

        embed = discord.Embed(
            title="⏭️ Track Skipped",
            description="Moving to the next track...",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)

    @music.command(name="queue", description="Show the current music queue")
    async def queue(self, interaction: discord.Interaction):
        """Display the current music queue."""
        
        player = self.get_player(interaction.guild.id)

        if not player.current and not player.queue:
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
        if player.current:
            current_title = player.current.get('title', 'Loading...')
            embed.add_field(
                name="🎵 Now Playing",
                value=current_title,
                inline=False
            )

        # Queue
        if player.queue:
            queue_text = ""
            for i, track in enumerate(list(player.queue)[:10], 1):
                title = track.get('title', track['search'])[:50]
                queue_text += f"{i}. {title}\n"

            if len(player.queue) > 10:
                queue_text += f"... and {len(player.queue) - 10} more tracks"

            embed.add_field(
                name=f"📋 Up Next ({len(player.queue)} tracks)",
                value=queue_text,
                inline=False
            )

        # Status info
        status_info = []
        if player.loop_current:
            status_info.append("🔂 Loop Track: ON")
        elif player.loop_queue:
            status_info.append("🔁 Loop Queue: ON")

        if status_info:
            embed.add_field(name="Status", value=" | ".join(status_info), inline=False)

        await interaction.response.send_message(embed=embed)

    @music.command(name="clear", description="Clear the music queue")
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

    @music.command(name="loop", description="Toggle loop mode")
    @app_commands.describe(mode="Choose loop mode: track or queue")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Track", value="track"),
        app_commands.Choice(name="Queue", value="queue"),
        app_commands.Choice(name="Off", value="off")
    ])
    async def loop(self, interaction: discord.Interaction, mode: str):
        """Toggle loop mode."""
        
        player = self.get_player(interaction.guild.id)

        if mode == "track":
            if not player.current:
                await interaction.response.send_message(
                    "❌ No track is currently playing!", 
                    ephemeral=True
                )
                return
            
            player.loop_current = True
            player.loop_queue = False
            status = "🔂 Loop Track: ON"
            color = 0x00FF00
            
        elif mode == "queue":
            player.loop_queue = True
            player.loop_current = False
            status = "🔁 Loop Queue: ON"
            color = 0x00FF00
            
        else:  # off
            player.loop_current = False
            player.loop_queue = False
            status = "🔁 Loop: OFF"
            color = 0xFF0000

        embed = discord.Embed(
            title="🔁 Loop Mode",
            description=status,
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @music.command(name="stop", description="Stop music and disconnect from voice channel")
    async def stop(self, interaction: discord.Interaction):
        """Stop music and disconnect from voice channel."""
        
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(
                "❌ Not connected to a voice channel!", 
                ephemeral=True
            )
            return

        # Clean up player
        self.cleanup_player(interaction.guild.id)
        
        # Disconnect
        await voice_client.disconnect()

        embed = discord.Embed(
            title="⏹️ Music Stopped",
            description="Disconnected from voice channel and cleared queue.",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)

    @music.command(name="nowplaying", description="Show information about the current track")
    async def nowplaying(self, interaction: discord.Interaction):
        """Show information about the current track."""
        
        player = self.get_player(interaction.guild.id)

        if not player.current:
            await interaction.response.send_message(
                "❌ No track is currently playing!", 
                ephemeral=True
            )
            return

        track = player.current
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"[{track.get('title', 'Loading...')}]({track.get('webpage_url', '')})",
            color=0x00FF00
        )

        if track.get('thumbnail'):
            embed.set_thumbnail(url=track['thumbnail'])

        if track.get('duration'):
            minutes, seconds = divmod(track['duration'], 60)
            embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)

        if track.get('uploader'):
            embed.add_field(name="Uploader", value=track['uploader'], inline=True)

        if player.loop_current:
            embed.add_field(name="🔂 Loop", value="Track", inline=True)
        elif player.loop_queue:
            embed.add_field(name="🔁 Loop", value="Queue", inline=True)

        queue_size = len(player.queue)
        embed.add_field(
            name="Queue", 
            value=f"{queue_size} track{'s' if queue_size != 1 else ''} remaining", 
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @music.command(name="volume", description="Set the player volume")
    @app_commands.describe(volume="Volume level (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Set the player volume."""
        
        if volume < 0 or volume > 100:
            await interaction.response.send_message(
                "❌ Volume must be between 0 and 100!", 
                ephemeral=True
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.source:
            await interaction.response.send_message(
                "❌ Nothing is currently playing!", 
                ephemeral=True
            )
            return

        player = self.get_player(interaction.guild.id)
        volume_float = volume / 100.0
        player.set_volume(volume_float)

        # Update current source volume if playing
        if hasattr(voice_client.source, 'volume'):
            voice_client.source.volume = volume_float

        embed = discord.Embed(
            title="🔊 Volume Changed",
            description=f"Volume set to {volume}%",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates."""
        # Clean up if bot is disconnected
        if member == self.bot.user and before.channel and not after.channel:
            # Bot was disconnected from voice channel
            guild_id = before.channel.guild.id
            self.cleanup_player(guild_id)

async def setup(bot):
    """Setup function to add the cog to the bot."""
    cog = Music(bot)
    await bot.add_cog(cog)
    
    # Optional: Sync commands to a specific guild for faster testing
    # GUILD_ID = 574731470900559872  # Replace with your server's ID
    # guild = discord.Object(id=GUILD_ID)
    # bot.tree.add_command(cog.music, guild=guild)
    
    print(f"Loaded {cog.__class__.__name__} cog")