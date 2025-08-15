import discord
import logging
import json
import os
import asyncio
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class WelcomeView(discord.ui.View):
    def __init__(self, cog, member):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.cog = cog
        self.member = member
        self.agreed = False

    @discord.ui.button(label='✅ I Agree to the Terms', style=discord.ButtonStyle.green)
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return

        self.agreed = True
        
        # Disable the button
        button.disabled = True
        button.label = '✅ Terms Accepted!'
        
        await interaction.response.edit_message(view=self)
        
        # Process the agreement
        await self.cog.process_agreement(self.member, interaction)

    @discord.ui.button(label='❌ I Do Not Agree', style=discord.ButtonStyle.red)
    async def disagree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return

        embed = discord.Embed(
            colour=discord.Colour.red(),
            title="❌ Terms Declined",
            description="You must agree to the server terms to participate. You can try again anytime by clicking the agree button.",
            timestamp=interaction.created_at
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        # Disable all buttons when view times out
        for item in self.children:
            item.disabled = True
        
        try:
            # Try to edit the original message
            embed = discord.Embed(
                colour=discord.Colour.orange(),
                title="⏰ Agreement Timed Out",
                description="This agreement prompt has expired. Please contact a moderator if you'd like to join the server.",
                timestamp=discord.utils.utcnow()
            )
            # Note: We can't easily edit the message here without storing the message reference
        except:
            pass

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "welcome_config.json"
        self.pending_file = "pending_users.json"
        self.load_config()
        self.load_pending_users()

    def load_config(self):
        """Load welcome system configuration"""
        default_config = {
            "enabled": False,
            "welcome_channel_id": None,
            "welcome_message": "Welcome to {server_name}, {user_mention}! 🎉\n\nPlease check your DMs to agree to our server terms and get your roles assigned!",
            "dm_message": "Welcome to **{server_name}**! 🎉\n\nTo participate in our server, you need to agree to our Rules and our Privacy Policy:\n\n**📋 Server Rules:**\n• Follow the Discord Terms of Service and Community Guidelines.\n• No vandalism or abuse of Administrator powers.\n• No gore, sexual content, or creepy behaviour.\n• Do not promote the killing or unlawful harm of anyone.\n\n• Our Privacy Policy can be found here: https://docs.google.com/document/d/1uNpbYUOb-CpW2eL2YoFB0VZPV2XYVpj44pPpUGW6kXE/edit?usp=sharing \n\n**🔒 By clicking 'I Agree', you confirm that you:**\n• Have read and understand the Rules\n• Will follow all server Rules\n• Agree to the Privacy Policy\n\nClick the button below to agree and get access to the server!",
            "success_message": "🎉 **Welcome to {server_name}!**\n\nYou've been successfully verified and given access to the server. Enjoy your stay!",
            "roles_to_assign": [],
            "require_agreement": True,
            "delete_welcome_after": 0,  # 0 = don't delete, time in minutes
            "log_channel_id": None
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_config.update(loaded_config)
            self.config = default_config
        except Exception as e:
            logging.error(f"Error loading welcome config: {e}")
            self.config = default_config

    def save_config(self):
        """Save welcome system configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving welcome config: {e}")

    def load_pending_users(self):
        """Load pending users data"""
        try:
            if os.path.exists(self.pending_file):
                with open(self.pending_file, 'r') as f:
                    self.pending_users = json.load(f)
            else:
                self.pending_users = {}
        except Exception as e:
            logging.error(f"Error loading pending users: {e}")
            self.pending_users = {}

    def save_pending_users(self):
        """Save pending users data"""
        try:
            with open(self.pending_file, 'w') as f:
                json.dump(self.pending_users, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving pending users: {e}")

    async def admin_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has Administrator role"""
        if not any(role.name == "Administrator" for role in interaction.user.roles):
            await interaction.response.send_message("You need the Administrator role to use this command.", ephemeral=True)
            return False
        return True

    async def process_agreement(self, member, interaction):
        """Process when a user agrees to terms"""
        try:
            # Assign roles
            roles_to_add = []
            if self.config["roles_to_assign"]:
                for role_id in self.config["roles_to_assign"]:
                    role = member.guild.get_role(role_id)
                    if role and role < member.guild.me.top_role and not role.managed:
                        roles_to_add.append(role)

            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Welcome system - user agreed to terms")
                logging.info(f"Assigned {len(roles_to_add)} roles to {member}")

            # Send success message
            success_msg = self.config["success_message"].format(
                server_name=member.guild.name,
                user_mention=member.mention,
                username=member.name
            )
            
            success_embed = discord.Embed(
                colour=discord.Colour.green(),
                title="🎉 Welcome Complete!",
                description=success_msg,
                timestamp=interaction.created_at
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Remove from pending users
            user_id = str(member.id)
            if user_id in self.pending_users:
                del self.pending_users[user_id]
                self.save_pending_users()

            # Log to log channel if configured
            if self.config["log_channel_id"]:
                log_channel = self.bot.get_channel(self.config["log_channel_id"])
                if log_channel:
                    log_embed = discord.Embed(
                        colour=discord.Colour.green(),
                        title="✅ User Verified",
                        description=f"{member.mention} has agreed to the terms and been verified.",
                        timestamp=interaction.created_at
                    )
                    log_embed.add_field(name="Roles Assigned", value=f"{len(roles_to_add)} roles", inline=True)
                    await log_channel.send(embed=log_embed)

        except Exception as e:
            logging.error(f"Error processing agreement for {member}: {e}")
            await interaction.followup.send("❌ An error occurred while processing your agreement. Please contact a moderator.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle new member joins"""
        if not self.config["enabled"] or member.bot:
            return

        try:
            # Send welcome message to channel if configured
            if self.config["welcome_channel_id"]:
                welcome_channel = self.bot.get_channel(self.config["welcome_channel_id"])
                if welcome_channel:
                    welcome_msg = self.config["welcome_message"].format(
                        server_name=member.guild.name,
                        user_mention=member.mention,
                        username=member.name
                    )
                    
                    welcome_embed = discord.Embed(
                        colour=discord.Colour.blue(),
                        title="👋 New Member!",
                        description=welcome_msg,
                        timestamp=member.joined_at
                    )
                    welcome_embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    
                    welcome_message = await welcome_channel.send(embed=welcome_embed)
                    
                    # Schedule deletion if configured
                    if self.config["delete_welcome_after"] > 0:
                        await asyncio.sleep(self.config["delete_welcome_after"] * 60)
                        try:
                            await welcome_message.delete()
                        except:
                            pass

            # Send DM with agreement if required
            if self.config["require_agreement"]:
                try:
                    dm_msg = self.config["dm_message"].format(
                        server_name=member.guild.name,
                        user_mention=member.mention,
                        username=member.name
                    )
                    
                    dm_embed = discord.Embed(
                        colour=discord.Colour.gold(),
                        title=f"Welcome to {member.guild.name}!",
                        description=dm_msg,
                        timestamp=member.joined_at
                    )
                    
                    view = WelcomeView(self, member)
                    await member.send(embed=dm_embed, view=view)
                    
                    # Add to pending users
                    user_id = str(member.id)
                    self.pending_users[user_id] = {
                        "username": str(member),
                        "joined_at": member.joined_at.isoformat(),
                        "dm_sent": True
                    }
                    self.save_pending_users()
                    
                    logging.info(f"Sent welcome DM to {member}")
                    
                except discord.Forbidden:
                    logging.warning(f"Could not send DM to {member}, trying welcome channel instead")
                    
                    # Try to send agreement message in welcome channel instead
                    if self.config["welcome_channel_id"]:
                        welcome_channel = self.bot.get_channel(self.config["welcome_channel_id"])
                        if welcome_channel:
                            try:
                                dm_msg = self.config["dm_message"].format(
                                    server_name=member.guild.name,
                                    user_mention=member.mention,
                                    username=member.name
                                )
                                
                                fallback_embed = discord.Embed(
                                    colour=discord.Colour.gold(),
                                    title=f"📬 Welcome {member.display_name}!",
                                    description=f"{member.mention}, we couldn't send you a DM, so here's your welcome message:\n\n{dm_msg}",
                                    timestamp=member.joined_at
                                )
                                fallback_embed.set_footer(text="Please interact with the buttons below to agree to our terms!")
                                
                                view = WelcomeView(self, member)
                                fallback_message = await welcome_channel.send(embed=fallback_embed, view=view)
                                
                                # Add to pending users
                                user_id = str(member.id)
                                self.pending_users[user_id] = {
                                    "username": str(member),
                                    "joined_at": member.joined_at.isoformat(),
                                    "dm_sent": False,
                                    "channel_fallback": True,
                                    "message_id": fallback_message.id
                                }
                                self.save_pending_users()
                                
                                logging.info(f"Sent welcome agreement to {member} in channel fallback")
                                
                                # Schedule deletion if configured
                                if self.config["delete_welcome_after"] > 0:
                                    await asyncio.sleep(self.config["delete_welcome_after"] * 60)
                                    try:
                                        await fallback_message.delete()
                                    except:
                                        pass
                                        
                            except Exception as e:
                                logging.error(f"Failed to send welcome message to channel for {member}: {e}")
                                # Log that both DM and channel failed if log channel is configured
                                if self.config["log_channel_id"]:
                                    log_channel = self.bot.get_channel(self.config["log_channel_id"])
                                    if log_channel:
                                        log_embed = discord.Embed(
                                            colour=discord.Colour.red(),
                                            title="❌ Welcome Failed",
                                            description=f"Could not send welcome message to {member.mention} via DM or channel. Manual verification required.",
                                            timestamp=member.joined_at
                                        )
                                        await log_channel.send(embed=log_embed)
                        else:
                            # No welcome channel configured, log the failure
                            logging.error(f"No welcome channel configured for DM fallback for {member}")
                            if self.config["log_channel_id"]:
                                log_channel = self.bot.get_channel(self.config["log_channel_id"])
                                if log_channel:
                                    log_embed = discord.Embed(
                                        colour=discord.Colour.red(),
                                        title="❌ Welcome Failed",
                                        description=f"Could not send DM to {member.mention} and no welcome channel configured for fallback.",
                                        timestamp=member.joined_at
                                    )
                                    await log_channel.send(embed=log_embed)
                    else:
                        # No welcome channel configured, log the failure
                        logging.error(f"No welcome channel configured for DM fallback for {member}")
                        if self.config["log_channel_id"]:
                            log_channel = self.bot.get_channel(self.config["log_channel_id"])
                            if log_channel:
                                log_embed = discord.Embed(
                                    colour=discord.Colour.red(),
                                    title="❌ Welcome Failed",
                                    description=f"Could not send DM to {member.mention} and no welcome channel configured for fallback.",
                                    timestamp=member.joined_at
                                )
                                await log_channel.send(embed=log_embed)

        except Exception as e:
            logging.error(f"Error in welcome system for {member}: {e}")

    @app_commands.command(name="welcome_toggle", description="[ADMIN] Enable or disable the welcome system")
    @app_commands.guilds(GUILD)
    async def welcome_toggle(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction):
            return

        self.config["enabled"] = not self.config["enabled"]
        self.save_config()

        status = "enabled" if self.config["enabled"] else "disabled"
        colour = discord.Colour.green() if self.config["enabled"] else discord.Colour.red()

        embed = discord.Embed(
            colour=colour,
            title=f"👋 Welcome System {status.title()}",
            description=f"Welcome system is now **{status}**.",
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=f"Changed by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)
        logging.info(f"Welcome system {status} by {interaction.user}")

    @app_commands.command(name="welcome_channel", description="[ADMIN] Set the welcome channel")
    @app_commands.describe(channel="Channel to send welcome messages (leave empty to disable)")
    @app_commands.guilds(GUILD)
    async def welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not await self.admin_check(interaction):
            return

        if channel:
            self.config["welcome_channel_id"] = channel.id
            message = f"Welcome channel set to {channel.mention}"
        else:
            self.config["welcome_channel_id"] = None
            message = "Welcome channel disabled"

        self.save_config()

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="📢 Welcome Channel Updated",
            description=message,
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=f"Updated by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="welcome_roles", description="[ADMIN] Set roles to assign to new verified members")
    @app_commands.describe(roles="Roles to assign (separate multiple roles with spaces)")
    @app_commands.guilds(GUILD)
    async def welcome_roles(self, interaction: discord.Interaction, roles: str = ""):
        if not await self.admin_check(interaction):
            return

        if not roles.strip():
            self.config["roles_to_assign"] = []
            self.save_config()
            
            embed = discord.Embed(
                colour=discord.Colour.orange(),
                title="🎭 Welcome Roles Cleared",
                description="No roles will be assigned to new members.",
                timestamp=interaction.created_at
            )
            await interaction.response.send_message(embed=embed)
            return

        # Parse role mentions/names/IDs
        role_objects = []
        role_ids = []
        
        # Split by spaces and clean up
        role_parts = roles.split()
        
        for part in role_parts:
            role = None
            
            # Try as mention first
            if part.startswith('<@&') and part.endswith('>'):
                role_id = int(part[3:-1])
                role = interaction.guild.get_role(role_id)
            # Try as ID
            elif part.isdigit():
                role = interaction.guild.get_role(int(part))
            # Try as name
            else:
                role = discord.utils.get(interaction.guild.roles, name=part)
            
            if role:
                role_objects.append(role)
                role_ids.append(role.id)

        self.config["roles_to_assign"] = role_ids
        self.save_config()

        if role_objects:
            role_list = ", ".join([role.mention for role in role_objects])
            embed = discord.Embed(
                colour=discord.Colour.green(),
                title="🎭 Welcome Roles Updated",
                description=f"New verified members will receive: {role_list}",
                timestamp=interaction.created_at
            )
        else:
            embed = discord.Embed(
                colour=discord.Colour.red(),
                title="❌ No Valid Roles Found",
                description="Please provide valid role names, IDs, or mentions.",
                timestamp=interaction.created_at
            )

        embed.set_author(
            name=f"Updated by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="welcome_config", description="[ADMIN] View current welcome system configuration")
    @app_commands.guilds(GUILD)
    async def welcome_config(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction):
            return

        status = "Enabled" if self.config["enabled"] else "Disabled"
        colour = discord.Colour.green() if self.config["enabled"] else discord.Colour.red()

        embed = discord.Embed(
            colour=colour,
            title="👋 Welcome System Configuration",
            timestamp=interaction.created_at
        )

        # Basic settings
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Require Agreement", value="Yes" if self.config["require_agreement"] else "No", inline=True)
        embed.add_field(name="Pending Users", value=str(len(self.pending_users)), inline=True)

        # Channel settings
        welcome_channel = "None"
        if self.config["welcome_channel_id"]:
            channel = self.bot.get_channel(self.config["welcome_channel_id"])
            welcome_channel = channel.mention if channel else "Invalid Channel"

        log_channel = "None"
        if self.config["log_channel_id"]:
            channel = self.bot.get_channel(self.config["log_channel_id"])
            log_channel = channel.mention if channel else "Invalid Channel"

        embed.add_field(name="Welcome Channel", value=welcome_channel, inline=True)
        embed.add_field(name="Log Channel", value=log_channel, inline=True)
        embed.add_field(name="Delete After", value=f"{self.config['delete_welcome_after']} min" if self.config['delete_welcome_after'] > 0 else "Never", inline=True)

        # Role settings
        if self.config["roles_to_assign"]:
            roles = []
            for role_id in self.config["roles_to_assign"]:
                role = interaction.guild.get_role(role_id)
                if role:
                    roles.append(role.mention)
                else:
                    roles.append(f"Invalid Role (ID: {role_id})")
            role_text = ", ".join(roles) if roles else "None"
        else:
            role_text = "None"

        embed.add_field(name="Assigned Roles", value=role_text, inline=False)

        embed.set_author(
            name=f"Requested by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="welcome_pending", description="[ADMIN] View users pending agreement")
    @app_commands.guilds(GUILD)
    async def welcome_pending(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction):
            return

        if not self.pending_users:
            embed = discord.Embed(
                colour=discord.Colour.green(),
                title="✅ No Pending Users",
                description="All users have completed the welcome process.",
                timestamp=interaction.created_at
            )
        else:
            pending_text = ""
            for user_id, data in list(self.pending_users.items())[:10]:  # Show max 10
                user = interaction.guild.get_member(int(user_id))
                if user:
                    joined_time = datetime.fromisoformat(data["joined_at"]).strftime("%Y-%m-%d %H:%M")
                    dm_status = "✅ DM" if data.get("dm_sent", True) else "📢 Channel"
                    pending_text += f"• {user.mention} - Joined: {joined_time} ({dm_status})\n"
                else:
                    # User left, remove from pending
                    del self.pending_users[user_id]

            if pending_text:
                embed = discord.Embed(
                    colour=discord.Colour.orange(),
                    title="⏳ Pending Agreement",
                    description=pending_text,
                    timestamp=interaction.created_at
                )
                embed.set_footer(text=f"Total pending: {len(self.pending_users)} | Showing most recent 10")
            else:
                embed = discord.Embed(
                    colour=discord.Colour.green(),
                    title="✅ No Pending Users",
                    description="All users have completed the welcome process.",
                    timestamp=interaction.created_at
                )

            self.save_pending_users()  # Save after cleanup

        embed.set_author(
            name=f"Requested by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="welcome_messages", description="[ADMIN] Customize welcome messages")
    @app_commands.describe(
        message_type="Which message to customize",
        content="New message content (use {server_name}, {user_mention}, {username} as placeholders)"
    )
    @app_commands.choices(message_type=[
        app_commands.Choice(name="Welcome Channel Message", value="welcome_message"),
        app_commands.Choice(name="DM Agreement Message", value="dm_message"),
        app_commands.Choice(name="Success Message", value="success_message")
    ])
    @app_commands.guilds(GUILD)
    async def welcome_messages(self, interaction: discord.Interaction, message_type: str, content: str):
        if not await self.admin_check(interaction):
            return

        if len(content) > 2000:
            await interaction.response.send_message("❌ Message content is too long (max 2000 characters).", ephemeral=True)
            return

        self.config[message_type] = content
        self.save_config()

        type_names = {
            "welcome_message": "Welcome Channel Message",
            "dm_message": "DM Agreement Message", 
            "success_message": "Success Message"
        }

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="💬 Message Updated",
            description=f"**{type_names[message_type]}** has been updated.",
            timestamp=interaction.created_at
        )
        embed.add_field(name="New Content", value=content[:1000] + ("..." if len(content) > 1000 else ""), inline=False)
        embed.set_author(
            name=f"Updated by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))