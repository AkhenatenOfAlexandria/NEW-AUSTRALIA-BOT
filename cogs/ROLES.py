import discord
from discord import app_commands
from discord.ext import commands
import json
import os

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class RoleAssignment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "UTILS/role_config.json"
        self.load_config()
    
    def load_config(self):
        """Load role configuration from JSON file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            # Default configuration
            self.config = {
                "assignable_roles": {},
                "mutual_exclusions": {}
            }
            self.save_config()
    
    def save_config(self):
        """Save role configuration to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_role_data(self, guild_id: str, role_name: str):
        """Helper method to find role data (case-insensitive)"""
        if guild_id not in self.config["assignable_roles"]:
            return None, None
        
        for name, data in self.config["assignable_roles"][guild_id].items():
            if name.lower() == role_name.lower():
                return name, data
        return None, None

    def check_mutual_exclusions(self, guild_id: str, role_name: str, user_roles):
        """Check if role conflicts with user's current roles"""
        if guild_id not in self.config["mutual_exclusions"]:
            return None
        
        for group_name, exclusive_roles in self.config["mutual_exclusions"][guild_id].items():
            if role_name in exclusive_roles:
                # Check if user has any conflicting roles
                for other_role_name in exclusive_roles:
                    if other_role_name != role_name:
                        other_role_data = self.config["assignable_roles"][guild_id].get(other_role_name)
                        if other_role_data:
                            other_role_id = other_role_data["role_id"]
                            if any(role.id == other_role_id for role in user_roles):
                                return other_role_name, group_name
        return None

    # Main role command group
    role_group = app_commands.Group(name="role", description="Self-assignable role commands", guild_ids=[GUILD_ID])

    @role_group.command(name="list", description="Show available self-assignable roles")
    async def list_roles(self, interaction: discord.Interaction):
        """Show all self-assignable roles"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config["assignable_roles"] or not self.config["assignable_roles"][guild_id]:
            embed = discord.Embed(
                title="Self-Assignable Roles",
                description="No self-assignable roles configured for this server.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        embed = discord.Embed(
            title="Self-Assignable Roles",
            color=discord.Color.green()
        )
        
        roles_info = []
        for role_name, role_data in self.config["assignable_roles"][guild_id].items():
            role = interaction.guild.get_role(role_data["role_id"])
            if role:
                description = role_data.get("description", "No description")
                roles_info.append(f"**{role_name}** - {description}")
        
        if roles_info:
            embed.description = "\n".join(roles_info)
            
            # Add mutual exclusion info
            if guild_id in self.config["mutual_exclusions"] and self.config["mutual_exclusions"][guild_id]:
                exclusions = []
                for group_name, roles in self.config["mutual_exclusions"][guild_id].items():
                    exclusions.append(f"**{group_name}**: {', '.join(roles)}")
                
                if exclusions:
                    embed.add_field(
                        name="Mutually Exclusive Groups",
                        value="\n".join(exclusions),
                        inline=False
                    )
        else:
            embed.description = "No valid roles found."
        
        await interaction.response.send_message(embed=embed)

    @role_group.command(name="add", description="Assign yourself a role")
    @app_commands.describe(role_name="The name of the role to assign")
    async def add_role(self, interaction: discord.Interaction, role_name: str):
        """Assign a role to yourself"""
        guild_id = str(interaction.guild.id)
        
        # Find the role
        actual_role_name, role_data = self.get_role_data(guild_id, role_name)
        if not role_data:
            await interaction.response.send_message(f"❌ Role `{role_name}` is not available for self-assignment.", ephemeral=True)
            return
        
        role = interaction.guild.get_role(role_data["role_id"])
        if not role:
            await interaction.response.send_message(f"❌ Role `{role_name}` no longer exists on this server.", ephemeral=True)
            return
        
        # Check if user already has the role
        if role in interaction.user.roles:
            await interaction.response.send_message(f"ℹ️ You already have the `{actual_role_name}` role.", ephemeral=True)
            return
        
        # Check mutual exclusions
        conflict = self.check_mutual_exclusions(guild_id, actual_role_name, interaction.user.roles)
        if conflict:
            conflicting_role, group_name = conflict
            await interaction.response.send_message(
                f"❌ You cannot have the `{actual_role_name}` role because you already have `{conflicting_role}`. "
                f"These roles are mutually exclusive (group: {group_name}).\n"
                f"Use `/role remove {conflicting_role}` first if you want to switch.",
                ephemeral=True
            )
            return
        
        # Assign the role
        try:
            await interaction.user.add_roles(role, reason="Self-assigned role")
            embed = discord.Embed(
                title="✅ Role Assigned",
                description=f"You have been given the `{actual_role_name}` role!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign roles. Please contact an administrator.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("❌ An error occurred while assigning the role. Please try again.", ephemeral=True)

    @role_group.command(name="remove", description="Remove a role from yourself")
    @app_commands.describe(role_name="The name of the role to remove")
    async def remove_role(self, interaction: discord.Interaction, role_name: str):
        """Remove a role from yourself"""
        guild_id = str(interaction.guild.id)
        
        # Find the role
        actual_role_name, role_data = self.get_role_data(guild_id, role_name)
        if not role_data:
            await interaction.response.send_message(f"❌ Role `{role_name}` is not available for self-assignment.", ephemeral=True)
            return
        
        role = interaction.guild.get_role(role_data["role_id"])
        if not role:
            await interaction.response.send_message(f"❌ Role `{role_name}` no longer exists on this server.", ephemeral=True)
            return
        
        # Check if user has the role
        if role not in interaction.user.roles:
            await interaction.response.send_message(f"ℹ️ You don't have the `{actual_role_name}` role.", ephemeral=True)
            return
        
        # Remove the role
        try:
            await interaction.user.remove_roles(role, reason="Self-removed role")
            embed = discord.Embed(
                title="✅ Role Removed",
                description=f"The `{actual_role_name}` role has been removed from you!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to remove roles. Please contact an administrator.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("❌ An error occurred while removing the role. Please try again.", ephemeral=True)

    @role_group.command(name="me", description="Show your current self-assignable roles")
    async def my_roles(self, interaction: discord.Interaction):
        """Show the self-assignable roles the user currently has"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config["assignable_roles"] or not self.config["assignable_roles"][guild_id]:
            await interaction.response.send_message("❌ No self-assignable roles configured for this server.", ephemeral=True)
            return
        
        user_assignable_roles = []
        for role_name, role_data in self.config["assignable_roles"][guild_id].items():
            role = interaction.guild.get_role(role_data["role_id"])
            if role and role in interaction.user.roles:
                user_assignable_roles.append(role_name)
        
        embed = discord.Embed(
            title="Your Self-Assignable Roles",
            color=discord.Color.blue() if user_assignable_roles else discord.Color.orange()
        )
        
        if user_assignable_roles:
            embed.description = f"You currently have: **{', '.join(user_assignable_roles)}**"
        else:
            embed.description = "You don't have any self-assignable roles."
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Admin subcommand group
    admin_group = app_commands.Group(name="admin", description="Role management admin commands", parent=role_group, guild_ids=[GUILD_ID])

    @admin_group.command(name="add", description="Add a role to the self-assignable list")
    @app_commands.describe(
        role_name="Name for the role in the system",
        role="The Discord role to make self-assignable",
        description="Description for the role"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def admin_add_role(self, interaction: discord.Interaction, role_name: str, role: discord.Role, description: str = "No description"):
        """Add a role to the self-assignable list"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config["assignable_roles"]:
            self.config["assignable_roles"][guild_id] = {}
        
        # Check if role name already exists
        if role_name in self.config["assignable_roles"][guild_id]:
            await interaction.response.send_message(f"❌ Role name `{role_name}` is already in use.", ephemeral=True)
            return
        
        # Check if Discord role is already assigned
        for existing_name, existing_data in self.config["assignable_roles"][guild_id].items():
            if existing_data["role_id"] == role.id:
                await interaction.response.send_message(f"❌ This Discord role is already assigned to `{existing_name}`.", ephemeral=True)
                return
        
        self.config["assignable_roles"][guild_id][role_name] = {
            "role_id": role.id,
            "description": description
        }
        
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Role Added",
            description=f"Role `{role_name}` ({role.mention}) has been added to self-assignable roles.",
            color=discord.Color.green()
        )
        embed.add_field(name="Description", value=description, inline=False)
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="remove", description="Remove a role from the self-assignable list")
    @app_commands.describe(role_name="Name of the role to remove from the system")
    @app_commands.default_permissions(manage_roles=True)
    async def admin_remove_role(self, interaction: discord.Interaction, role_name: str):
        """Remove a role from the self-assignable list"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config["assignable_roles"] or role_name not in self.config["assignable_roles"][guild_id]:
            await interaction.response.send_message(f"❌ Role `{role_name}` is not in the self-assignable list.", ephemeral=True)
            return
        
        del self.config["assignable_roles"][guild_id][role_name]
        
        # Clean up mutual exclusion groups
        if guild_id in self.config["mutual_exclusions"]:
            groups_to_remove = []
            for group_name, roles in self.config["mutual_exclusions"][guild_id].items():
                if role_name in roles:
                    roles.remove(role_name)
                    if len(roles) < 2:  # Remove group if less than 2 roles
                        groups_to_remove.append(group_name)
            
            for group_name in groups_to_remove:
                del self.config["mutual_exclusions"][guild_id][group_name]
        
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Role Removed",
            description=f"Role `{role_name}` has been removed from self-assignable roles.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="list", description="List all configured self-assignable roles")
    @app_commands.default_permissions(manage_roles=True)
    async def admin_list_roles(self, interaction: discord.Interaction):
        """List all configured self-assignable roles"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config["assignable_roles"] or not self.config["assignable_roles"][guild_id]:
            embed = discord.Embed(
                title="Self-Assignable Roles Configuration",
                description="No self-assignable roles configured for this server.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Self-Assignable Roles Configuration",
            color=discord.Color.blue()
        )
        
        for role_name, role_data in self.config["assignable_roles"][guild_id].items():
            role = interaction.guild.get_role(role_data["role_id"])
            role_mention = role.mention if role else "❌ Role Deleted"
            description = role_data.get("description", "No description")
            
            embed.add_field(
                name=role_name,
                value=f"**Role:** {role_mention}\n**Description:** {description}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="create_group", description="Create a mutually exclusive group of roles")
    @app_commands.describe(
        group_name="Name for the exclusive group",
        roles="Space-separated list of role names to make mutually exclusive"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def create_exclusive_group(self, interaction: discord.Interaction, group_name: str, roles: str):
        """Create a mutually exclusive group of roles"""
        role_names = roles.split()
        
        if len(role_names) < 2:
            await interaction.response.send_message("❌ You need at least 2 roles to create a mutually exclusive group.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        
        # Verify all roles exist in assignable roles
        if guild_id not in self.config["assignable_roles"]:
            await interaction.response.send_message("❌ No assignable roles configured for this server.", ephemeral=True)
            return
        
        invalid_roles = [role for role in role_names if role not in self.config["assignable_roles"][guild_id]]
        if invalid_roles:
            await interaction.response.send_message(f"❌ These roles are not self-assignable: {', '.join(invalid_roles)}", ephemeral=True)
            return
        
        if guild_id not in self.config["mutual_exclusions"]:
            self.config["mutual_exclusions"][guild_id] = {}
        
        # Check if group name already exists
        if group_name in self.config["mutual_exclusions"][guild_id]:
            await interaction.response.send_message(f"❌ Exclusive group `{group_name}` already exists.", ephemeral=True)
            return
        
        self.config["mutual_exclusions"][guild_id][group_name] = role_names
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Exclusive Group Created",
            description=f"Mutually exclusive group `{group_name}` created with roles: {', '.join(role_names)}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="remove_group", description="Remove a mutually exclusive group")
    @app_commands.describe(group_name="Name of the exclusive group to remove")
    @app_commands.default_permissions(manage_roles=True)
    async def remove_exclusive_group(self, interaction: discord.Interaction, group_name: str):
        """Remove a mutually exclusive group"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config["mutual_exclusions"] or group_name not in self.config["mutual_exclusions"][guild_id]:
            await interaction.response.send_message(f"❌ Exclusive group `{group_name}` does not exist.", ephemeral=True)
            return
        
        del self.config["mutual_exclusions"][guild_id][group_name]
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Exclusive Group Removed",
            description=f"Mutually exclusive group `{group_name}` has been removed.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="list_groups", description="List all mutually exclusive groups")
    @app_commands.default_permissions(manage_roles=True)
    async def list_exclusive_groups(self, interaction: discord.Interaction):
        """List all mutually exclusive groups"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.config["mutual_exclusions"] or not self.config["mutual_exclusions"][guild_id]:
            embed = discord.Embed(
                title="Mutually Exclusive Groups",
                description="No mutually exclusive groups configured for this server.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Mutually Exclusive Groups",
            color=discord.Color.blue()
        )
        
        for group_name, roles in self.config["mutual_exclusions"][guild_id].items():
            embed.add_field(
                name=group_name,
                value=", ".join(roles),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleAssignment(bot))