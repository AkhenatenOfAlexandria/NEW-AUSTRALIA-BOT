import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

class States(commands.Cog):
    """A cog for managing fictional state roles with cooldowns using slash commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "states_data.json"
        self.cooldown_data = self.load_cooldown_data()
        
        # Define your state roles here - UPDATE THESE TO MATCH YOUR SERVER ROLES
        self.states = {
            "Port Arthur, NK": "The District of New Kekistan is the confederal district containing the capital city of Port Arthur.",
            "Waffledonia": "The Kingdom of Waffledonia.",
            "Whyoming": "The ASS Sultanate of Whyoming.",
            "Holy Josephite Empire": "The whole Confederacy is in the Empire, but constitutionally it has to have its own residencies."
        }
    
    def get_stats_core(self):
        """Get the StatsCore cog for accessing core functionality"""
        return self.bot.get_cog('StatsCore')
    
    def is_user_conscious(self, user_id):
        """Check if user is conscious (health > 0)"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return True  # Assume conscious if stats unavailable
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            return True  # Assume conscious if no stats
        
        return stats['health'] > 0
    
    async def check_consciousness(self, interaction):
        """Check if user is conscious, send error if not"""
        if not self.is_user_conscious(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are unconscious and cannot participate in state affairs! "
                "Focus on survival - seek medical attention or wait for stabilization.",
                ephemeral=True
            )
            return False
        return True
    
    def load_cooldown_data(self) -> Dict[str, Any]:
        """Load cooldown data from JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_cooldown_data(self):
        """Save cooldown data to JSON file."""
        with open(self.data_file, 'w') as f:
            json.dump(self.cooldown_data, f, indent=2)
    
    def get_user_cooldown(self, user_id: int) -> Optional[datetime]:
        """Get the cooldown end time for a user."""
        user_data = self.cooldown_data.get(str(user_id))
        if user_data and 'cooldown_until' in user_data:
            return datetime.fromisoformat(user_data['cooldown_until'])
        return None
    
    def set_user_cooldown(self, user_id: int, state: str):
        """Set a one-month cooldown for a user."""
        cooldown_end = datetime.now() + timedelta(days=30)  # 30 days = ~1 month
        
        if str(user_id) not in self.cooldown_data:
            self.cooldown_data[str(user_id)] = {}
        
        self.cooldown_data[str(user_id)]['cooldown_until'] = cooldown_end.isoformat()
        self.cooldown_data[str(user_id)]['current_state'] = state
        self.cooldown_data[str(user_id)]['last_change'] = datetime.now().isoformat()
        self.save_cooldown_data()
    
    def get_user_current_state(self, user_id: int) -> Optional[str]:
        """Get the user's current state."""
        user_data = self.cooldown_data.get(str(user_id))
        return user_data.get('current_state') if user_data else None
    
    async def get_state_role(self, guild: discord.Guild, state_name: str) -> Optional[discord.Role]:
        """Get the existing state role."""
        # Look for existing role
        existing_role = discord.utils.get(guild.roles, name=state_name)
        if existing_role:
            return existing_role
        
        # If role doesn't exist, return None
        return None
    
    async def remove_all_state_roles(self, member: discord.Member):
        """Remove all state roles from a member."""
        # Find state roles the member has
        state_roles_to_remove = []
        for role in member.roles:
            if role.name in self.states.keys():
                state_roles_to_remove.append(role)
        
        if state_roles_to_remove:
            await member.remove_roles(*state_roles_to_remove, reason="Changing states")

    async def state_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for state names."""
        return [
            app_commands.Choice(name=f"🏛️ {state}", value=state)
            for state in self.states.keys()
            if current.lower() in state.lower()
        ][:25]  # Discord limits to 25 choices
    
    # Slash command group
    state_group = app_commands.Group(name="state", description="Manage your state membership")
    
    @state_group.command(name="list", description="List all available states")
    async def list_states(self, interaction: discord.Interaction):
        """List all available states - allowed while unconscious"""
        embed = discord.Embed(
            title="🏛️ Available States",
            description="Choose your allegiance! Every member must be in a state. Use `/state join` to join a state.",
            color=0x2F3136
        )
        
        for state_name, description in self.states.items():
            embed.add_field(
                name=f"🏛️ {state_name}",
                value=description,
                inline=False
            )
        
        embed.set_footer(text="⚠️ You can only change states once per month!")
        await interaction.response.send_message(embed=embed)
    
    @state_group.command(name="join", description="Join a state (adds the corresponding role)")
    @app_commands.describe(state="The state you want to join")
    @app_commands.autocomplete(state=state_autocomplete)
    async def join_state(self, interaction: discord.Interaction, state: str):
        """Join a state (adds the corresponding role)."""
        
        # Check consciousness
        if not await self.check_consciousness(interaction):
            return
        
        # Find matching state (case-insensitive)
        matching_state = None
        for state_key in self.states.keys():
            if state_key.lower() == state.lower():
                matching_state = state_key
                break
        
        if not matching_state:
            await interaction.response.send_message(
                f"❌ State '{state}' not found! Use `/state list` to see available states.", 
                ephemeral=True
            )
            return
        
        # Check if user is already in this state
        current_state = self.get_user_current_state(interaction.user.id)
        if current_state == matching_state:
            await interaction.response.send_message(
                f"❌ You're already a citizen of {matching_state}!", 
                ephemeral=True
            )
            return
        
        # Check cooldown
        cooldown_end = self.get_user_cooldown(interaction.user.id)
        if cooldown_end and datetime.now() < cooldown_end:
            time_left = cooldown_end - datetime.now()
            days_left = time_left.days
            hours_left = time_left.seconds // 3600
            
            await interaction.response.send_message(
                f"⏰ You're still on cooldown! You can change states again in "
                f"**{days_left} days and {hours_left} hours**.",
                ephemeral=True
            )
            return
        
        try:
            # Remove existing state roles
            await self.remove_all_state_roles(interaction.user)
            
            # Get the existing state role
            role = await self.get_state_role(interaction.guild, matching_state)
            
            if not role:
                await interaction.response.send_message(
                    f"❌ The role for {matching_state} doesn't exist on this server! Please contact an admin.", 
                    ephemeral=True
                )
                return
            
            # Add the new role
            await interaction.user.add_roles(role, reason=f"Joined state: {matching_state}")
            
            # Set cooldown
            self.set_user_cooldown(interaction.user.id, matching_state)
            
            # Send confirmation
            embed = discord.Embed(
                title=f"🎉 Welcome to {matching_state}!",
                description=f"🏛️ {self.states[matching_state]}",
                color=role.color.value if role.color.value != 0 else 0x2F3136
            )
            embed.add_field(
                name="⏰ Next Change Available",
                value=f"<t:{int((datetime.now() + timedelta(days=30)).timestamp())}:R>",
                inline=False
            )
            embed.set_footer(text=f"You are now a citizen of {matching_state}!")
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to manage roles!", 
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {e}", 
                ephemeral=True
            )
    
    @state_group.command(name="info", description="Check state status and cooldown information")
    @app_commands.describe(member="The member to check (optional, defaults to yourself)")
    async def state_info(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """Check your current state and cooldown status - allowed for others while unconscious"""
        target = member or interaction.user
        
        # Only check consciousness if checking own status
        if not member and not await self.check_consciousness(interaction):
            return
        
        current_state = self.get_user_current_state(target.id)
        cooldown_end = self.get_user_cooldown(target.id)
        
        embed = discord.Embed(
            title=f"🏛️ State Information for {target.display_name}",
            color=0x2F3136
        )
        
        if current_state:
            description = self.states.get(current_state)
            if description:
                # Try to get the actual role for color
                role = await self.get_state_role(interaction.guild, current_state)
                role_color = role.color.value if role and role.color.value != 0 else 0x2F3136
                
                embed.add_field(
                    name="Current State",
                    value=f"🏛️ **{current_state}**\n{description}",
                    inline=False
                )
                embed.color = role_color
            else:
                # State exists in data but not in our predefined states
                embed.add_field(
                    name="Current State",
                    value=f"🏛️ **{current_state}**\n*Custom state*",
                    inline=False
                )
        else:
            embed.add_field(
                name="Current State",
                value="❌ **No State**\nYou must join a state! Use `/state join` to select one.",
                inline=False
            )
        
        if cooldown_end:
            if datetime.now() < cooldown_end:
                embed.add_field(
                    name="⏰ Next Change Available",
                    value=f"<t:{int(cooldown_end.timestamp())}:R>",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Change Status",
                    value="You can change states now!",
                    inline=False
                )
        else:
            embed.add_field(
                name="✅ Change Status",
                value="You can join a state anytime! Everyone must be in a state.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @state_group.command(name="reset_cooldown", description="Reset a user's state change cooldown (Admin only)")
    @app_commands.describe(member="The member whose cooldown to reset")
    @app_commands.default_permissions(administrator=True)
    async def reset_cooldown(self, interaction: discord.Interaction, member: discord.Member):
        """Reset a user's state change cooldown (Admin only)."""
        if str(member.id) in self.cooldown_data:
            self.cooldown_data[str(member.id)]['cooldown_until'] = datetime.now().isoformat()
            self.save_cooldown_data()
            await interaction.response.send_message(
                f"✅ Reset state change cooldown for {member.display_name}"
            )
        else:
            await interaction.response.send_message(
                f"❌ {member.display_name} has no cooldown data.", 
                ephemeral=True
            )

async def setup(bot):
    """Setup function to add the cog to the bot."""
    cog = States(bot)
    await bot.add_cog(cog)
    
    # Sync the slash commands to your guild
    GUILD_ID = 574731470900559872  # Your server's ID from main.py
    guild = discord.Object(id=GUILD_ID)
    bot.tree.add_command(cog.state_group, guild=guild)