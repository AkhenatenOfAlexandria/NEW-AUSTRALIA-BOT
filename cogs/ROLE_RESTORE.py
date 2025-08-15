import discord
import logging
import json
import os
from discord import app_commands
from discord.ext import commands
from datetime import datetime

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class RoleRestore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles_file = "user_roles.json"
        self.enabled_file = "UTILS/role_restore_enabled.json"
        self.load_data()

    def load_data(self):
        """Load user roles and enabled status from files"""
        try:
            # Load user roles
            if os.path.exists(self.roles_file):
                with open(self.roles_file, 'r') as f:
                    self.user_roles = json.load(f)
            else:
                self.user_roles = {}
            
            # Load enabled status
            if os.path.exists(self.enabled_file):
                with open(self.enabled_file, 'r') as f:
                    data = json.load(f)
                    self.enabled = data.get('enabled', False)
            else:
                self.enabled = False
                
        except Exception as e:
            logging.error(f"Error loading role restore data: {e}")
            self.user_roles = {}
            self.enabled = False

    def save_user_roles(self):
        """Save user roles to file"""
        try:
            with open(self.roles_file, 'w') as f:
                json.dump(self.user_roles, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving user roles: {e}")

    def save_enabled_status(self):
        """Save enabled status to file"""
        try:
            with open(self.enabled_file, 'w') as f:
                json.dump({'enabled': self.enabled}, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving enabled status: {e}")

    def store_user_roles(self, member):
        """Store a user's roles when he leaves"""
        if not self.enabled:
            return
            
        user_id = str(member.id)
        # Get all roles except @everyone
        roles = [role.id for role in member.roles if role.name != "@everyone"]
        
        if roles:  # Only store if user has roles
            self.user_roles[user_id] = {
                'roles': roles,
                'username': str(member),
                'left_at': datetime.now().isoformat()
            }
            self.save_user_roles()
            logging.info(f"Stored {len(roles)} roles for {member} ({user_id})")

    async def restore_user_roles(self, member):
        """Restore a user's roles when they rejoin"""
        if not self.enabled:
            return 0, []
            
        user_id = str(member.id)
        
        if user_id not in self.user_roles:
            return 0, []  # No stored roles for this user
        
        stored_data = self.user_roles[user_id]
        role_ids = stored_data['roles']
        
        # Get role objects that still exist
        roles_to_add = []
        missing_roles = []
        
        for role_id in role_ids:
            role = member.guild.get_role(role_id)
            if role:
                # Check if bot can assign this role (bot's highest role must be higher)
                if role < member.guild.me.top_role and not role.managed:
                    roles_to_add.append(role)
                else:
                    missing_roles.append(f"{role.name} (can't assign)")
            else:
                missing_roles.append(f"Unknown Role (ID: {role_id})")
        
        # Add the roles
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Role restoration system")
                logging.info(f"Restored {len(roles_to_add)} roles to {member}")
                
                # Clean up stored data after successful restoration
                del self.user_roles[user_id]
                self.save_user_roles()
                
                return len(roles_to_add), missing_roles
            except discord.Forbidden:
                logging.error(f"No permission to add roles to {member}")
                return 0, ["Permission denied"]
            except Exception as e:
                logging.error(f"Error restoring roles to {member}: {e}")
                return 0, [f"Error: {str(e)}"]
        
        return 0, missing_roles

    def log_all_user_roles(self, guild):
        """Log all current user roles in the server"""
        if not self.enabled:
            return 0
            
        logged_count = 0
        for member in guild.members:
            if not member.bot:  # Skip bots
                roles = [role.id for role in member.roles if role.name != "@everyone"]
                if roles:  # Only store if user has roles
                    user_id = str(member.id)
                    self.user_roles[user_id] = {
                        'roles': roles,
                        'username': str(member),
                        'logged_at': datetime.now().isoformat()
                    }
                    logged_count += 1
        
        self.save_user_roles()
        return logged_count

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Event triggered when a member leaves the server"""
        self.store_user_roles(member)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Event triggered when a member joins the server"""
        if not self.enabled:
            return
            
        # Wait a moment for Discord to fully process the join
        await discord.utils.sleep_until(discord.utils.utcnow().replace(second=5))
        
        restored_count, missing_roles = await self.restore_user_roles(member)
        
        if restored_count > 0:
            # Send a log message about the restoration
            try:
                # Try to find a logging channel or use general
                log_channel = None
                for channel in member.guild.text_channels:
                    if 'log' in channel.name.lower() or 'mod' in channel.name.lower():
                        log_channel = channel
                        break
                
                if log_channel:
                    embed = discord.Embed(
                        colour=discord.Colour.green(),
                        title="🔄 Roles Restored",
                        description=f"Restored {restored_count} role(s) to {member.mention}",
                        timestamp=discord.utils.utcnow()
                    )
                    
                    if missing_roles:
                        embed.add_field(
                            name="⚠️ Could Not Restore",
                            value="\n".join(missing_roles[:10]),  # Limit to 10 to avoid embed limits
                            inline=False
                        )
                    
                    await log_channel.send(embed=embed)
            except Exception as e:
                logging.error(f"Error sending role restoration log: {e}")

    async def admin_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has Administrator role"""
        if not any(role.name == "Administrator" for role in interaction.user.roles):
            await interaction.response.send_message("You need the Administrator role to use this command.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="role_restore_toggle", description="[ADMIN] Enable or disable the role restoration system")
    @app_commands.guilds(GUILD)
    async def role_restore_toggle(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction):
            return
            
        self.enabled = not self.enabled
        self.save_enabled_status()
        
        status = "enabled" if self.enabled else "disabled"
        colour = discord.Colour.green() if self.enabled else discord.Colour.red()
        
        embed = discord.Embed(
            colour=colour,
            title=f"🔄 Role Restoration {status.title()}",
            description=f"Role restoration system is now **{status}**.",
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=f"Changed by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        
        await interaction.response.send_message(embed=embed)
        logging.info(f"Role restoration system {status} by {interaction.user}")

    @app_commands.command(name="log_all_roles", description="[ADMIN] Log all current user roles in the server")
    @app_commands.guilds(GUILD)
    async def log_all_roles(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction):
            return
            
        if not self.enabled:
            await interaction.response.send_message("❌ Role restoration system is disabled. Enable it first with `/role_restore_toggle`.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        logged_count = self.log_all_user_roles(interaction.guild)
        
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="📝 Server Roles Logged",
            description=f"Successfully logged roles for **{logged_count}** users.",
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=f"Logged by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        embed.add_field(
            name="ℹ️ Note",
            value="These roles will be restored if users leave and rejoin the server.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        logging.info(f"Logged roles for {logged_count} users by {interaction.user}")

    @app_commands.command(name="role_restore_status", description="[ADMIN] Check the status of the role restoration system")
    @app_commands.guilds(GUILD)
    async def role_restore_status(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction):
            return
            
        status = "Enabled" if self.enabled else "Disabled"
        colour = discord.Colour.green() if self.enabled else discord.Colour.red()
        
        embed = discord.Embed(
            colour=colour,
            title="🔄 Role Restoration Status",
            timestamp=interaction.created_at
        )
        
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Stored Users", value=str(len(self.user_roles)), inline=True)
        
        if self.user_roles:
            # Show some recent entries
            recent_users = list(self.user_roles.items())[-5:]  # Last 5 users
            recent_text = ""
            for user_id, data in recent_users:
                username = data.get('username', f'ID: {user_id}')
                role_count = len(data.get('roles', []))
                recent_text += f"• {username} ({role_count} roles)\n"
            
            embed.add_field(
                name="Recent Stored Users",
                value=recent_text if recent_text else "None",
                inline=False
            )
        
        embed.set_author(
            name=f"Requested by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear_role_data", description="[ADMIN] Clear all stored role data")
    @app_commands.guilds(GUILD)
    async def clear_role_data(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction):
            return
            
        stored_count = len(self.user_roles)
        self.user_roles = {}
        self.save_user_roles()
        
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title="🗑️ Role Data Cleared",
            description=f"Cleared stored role data for **{stored_count}** users.",
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=f"Cleared by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        
        await interaction.response.send_message(embed=embed)
        logging.info(f"Role data cleared by {interaction.user} ({stored_count} users)")

async def setup(bot):
    await bot.add_cog(RoleRestore(bot))