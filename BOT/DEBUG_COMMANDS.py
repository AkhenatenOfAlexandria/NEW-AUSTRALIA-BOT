import discord
import traceback
import logging
from pathlib import Path
from discord.ext import commands

class DebugCommands:
    def __init__(self, bot):
        self.bot = bot
        self._register_commands()

    def _register_commands(self):
        """Register all debug commands"""
        @self.bot.command(name="debug_tree")
        @commands.is_owner()
        async def debug_tree(ctx):
            await self._debug_tree(ctx)

        @self.bot.command(name="force_sync")
        @commands.is_owner()
        async def force_sync(ctx):
            await self._force_sync(ctx)

        @self.bot.command(name="reload_cogs")
        @commands.is_owner()
        async def reload_cogs(ctx):
            await self._reload_cogs(ctx)

        @self.bot.command(name="check_cog_commands")
        @commands.is_owner()
        async def check_cog_commands(ctx):
            await self._check_cog_commands(ctx)

        @self.bot.command(name="clear_commands")
        @commands.is_owner()
        async def clear_commands(ctx):
            await self._clear_commands(ctx)

    async def _debug_tree(self, ctx):
        """Debug command tree contents"""
        guild_commands = self.bot.tree.get_commands(guild=self.bot.config.GUILD)
        global_commands = self.bot.tree.get_commands()
        
        embed = discord.Embed(title="Command Tree Debug", color=0x00ff00)
        
        # Guild commands
        if guild_commands:
            guild_names = []
            for cmd in guild_commands:
                if hasattr(cmd, 'name'):
                    guild_names.append(f"{cmd.name} ({type(cmd).__name__})")
            embed.add_field(
                name=f"Guild Commands ({len(guild_commands)})", 
                value="\n".join(guild_names) or "None", 
                inline=False
            )
        else:
            embed.add_field(name="Guild Commands", value="None found", inline=False)
        
        # Global commands  
        if global_commands:
            global_names = []
            for cmd in global_commands:
                if hasattr(cmd, 'name'):
                    global_names.append(f"{cmd.name} ({type(cmd).__name__})")
            embed.add_field(
                name=f"Global Commands ({len(global_commands)})", 
                value="\n".join(global_names) or "None", 
                inline=False
            )
        else:
            embed.add_field(name="Global Commands", value="None found", inline=False)
        
        # Loaded cogs
        embed.add_field(
            name="Loaded Cogs", 
            value="\n".join(self.bot.cogs.keys()) or "None", 
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def _force_sync(self, ctx):
        """Force sync commands"""
        try:
            guild_commands = self.bot.tree.get_commands(guild=self.bot.config.GUILD)
            await ctx.send(f"Commands in tree before sync: {len(guild_commands)}")
            
            if guild_commands:
                cmd_names = [cmd.name for cmd in guild_commands]
                await ctx.send(f"Command names: {', '.join(cmd_names)}")
            
            self.bot.tree.clear_commands(guild=self.bot.config.GUILD)
            await ctx.send("Cleared guild commands...")
            
            synced = await self.bot.tree.sync(guild=self.bot.config.GUILD)
            await ctx.send(f"Synced {len(synced)} guild commands!")
            
            if synced:
                cmd_list = [cmd.name for cmd in synced]
                await ctx.send(f"Commands: {', '.join(cmd_list)}")
            else:
                await ctx.send("⚠️ No commands were synced! This means no commands are in the tree.")
            
        except Exception as e:
            await ctx.send(f"Sync failed: {e}")
            traceback.print_exc()

    async def _reload_cogs(self, ctx):
        """Reload all cogs and re-register commands"""
        try:
            cog_names = list(self.bot.cogs.keys())
            await ctx.send(f"Reloading {len(cog_names)} cogs...")
            
            # Unload all cogs
            for cog_name in cog_names:
                try:
                    await self.bot.unload_extension(f"cogs.{cog_name}")
                    await ctx.send(f"✅ Unloaded {cog_name}")
                except Exception as e:
                    await ctx.send(f"❌ Failed to unload {cog_name}: {e}")
            
            # Clear commands
            self.bot.tree.clear_commands(guild=self.bot.config.GUILD)
            
            # Reload all cogs
            cog_files = list((Path(__file__).parent.parent/"cogs").glob("*.py"))
            for file in cog_files:
                if not file.name.startswith("_"):
                    try:
                        await self.bot.load_extension(f"cogs.{file.stem}")
                        await ctx.send(f"✅ Reloaded {file.stem}")
                    except Exception as e:
                        await ctx.send(f"❌ Failed to reload {file.stem}: {e}")
            
            # Check what's in the tree now
            guild_commands = self.bot.tree.get_commands(guild=self.bot.config.GUILD)
            await ctx.send(f"Commands in tree after reload: {len(guild_commands)}")
            
            # Sync
            synced = await self.bot.tree.sync(guild=self.bot.config.GUILD)
            await ctx.send(f"Final sync result: {len(synced)} commands")
            
        except Exception as e:
            await ctx.send(f"Reload failed: {e}")
            traceback.print_exc()

    async def _check_cog_commands(self, ctx):
        """Check what commands each cog should have"""
        for cog_name, cog in self.bot.cogs.items():
            commands = []
            
            # Check for app_commands
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__discord_app_commands_checks__'):
                    commands.append(f"/{attr_name}")
                elif hasattr(attr, 'name') and hasattr(attr, 'callback'):
                    commands.append(f"/{attr.name}")
            
            # Check for command groups
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if hasattr(attr, 'name') and hasattr(attr, 'commands'):
                    commands.append(f"Group: {attr.name}")
            
            if commands:
                await ctx.send(f"**{cog_name}**: {', '.join(commands)}")
            else:
                await ctx.send(f"**{cog_name}**: No commands found")

    async def _clear_commands(self, ctx):
        """Owner-only command to manually clear all slash commands"""
        try:
            # This would need to be implemented in the bot class
            # await self.bot.clear_all_commands()
            await ctx.send("✅ All commands cleared. Restart the bot to re-sync.")
        except Exception as e:
            await ctx.send(f"❌ Error clearing commands: {e}")