import discord
from discord.ext import commands
import logging

from UTILS.CONFIGURATION import GUILD_ID

# Import all hospital components
from cogs.HOSPITAL.HOSPITAL_CORE import HospitalCore
from cogs.HOSPITAL.HOSPITAL_FINANCIAL import HospitalFinancial
from cogs.HOSPITAL.HOSPITAL_TREATMENT import HospitalTreatment
from cogs.HOSPITAL.HOSPITAL_PROCESSOR import HospitalProcessor
from cogs.HOSPITAL.HOSPITAL_COMMANDS import HospitalCommands
from cogs.HOSPITAL.HOSPITAL_STATISTICS_COMMANDS import HospitalStatsCommands

GUILD = discord.Object(id=GUILD_ID)


class HospitalSystem(commands.Cog):
    """
    Main Hospital System cog that coordinates all hospital components.
    
    This system provides:
    - Automatic transport for unconscious users
    - Comprehensive healing until conscious or funds exhausted
    - Multiple healing sessions per cycle
    - Detailed logging and statistics (retained indefinitely by default)
    - Financial management with no taxes
    - Discord commands for management and monitoring
    - Database optimization and backup capabilities
    - Complete Health Log integration
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize all components
        self.core = HospitalCore(bot)
        self.financial = HospitalFinancial(self.core)
        self.treatment = HospitalTreatment(self.core, self.financial)
        self.processor = HospitalProcessor(self.core, self.treatment)
        
        # Add command cogs
        self.commands = HospitalCommands(bot, self.core, self.treatment)
        self.stats_commands = HospitalStatsCommands(bot, self.core, self.treatment)
        
        # Initialize the cog commands list
        self.__cog_app_commands__ = []
        
        # Add commands to this cog
        self._add_commands()
        
        logging.info("✅ Hospital System initialized with all components (indefinite log retention)")
    
    def _add_commands(self):
        """Add all commands from component cogs to this main cog"""
        # Add basic hospital commands
        for command in self.commands.get_app_commands():
            self.__cog_app_commands__.append(command)
        
        # Add statistics commands
        for command in self.stats_commands.get_app_commands():
            self.__cog_app_commands__.append(command)
    
    # Public interface methods for other systems to use
    
    def is_in_hospital(self, user_id):
        """Check if user is currently in hospital"""
        return self.core.is_in_hospital(user_id)
    
    def is_user_in_combat(self, user_id):
        """Check if user is in combat (used by other systems)"""
        return self.core.is_user_in_combat(user_id)
    
    async def process_unconscious_users(self):
        """Main processing function called by the bot's timer"""
        await self.processor.process_unconscious_users()
    
    async def get_hospital_status(self):
        """Get current hospital system status"""
        return await self.processor.get_current_hospital_status()
    
    async def manual_transport(self, user_id):
        """Manually transport a user (for admin use)"""
        return await self.treatment.transport_to_hospital(user_id)
    
    async def manual_healing(self, user_id):
        """Manually trigger healing for a user (for admin use)"""
        return await self.treatment.attempt_maximum_healing(user_id)
    
    def get_service_costs(self):
        """Get current service costs"""
        return self.financial.get_service_costs()
    
    def log_external_action(self, user_id, username, action_type, **kwargs):
        """Allow external systems to log hospital-related actions"""
        return self.core.log_hospital_action(user_id, username, action_type, **kwargs)
    
    def get_log_statistics(self):
        """Get hospital log statistics"""
        return self.core.get_log_statistics()
    
    def perform_maintenance(self, force_backup=False):
        """Perform log maintenance (backup, optimization, etc.)"""
        return self.core.perform_maintenance(force_backup)
    
    # Cog lifecycle methods
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        logging.info("🏥 Hospital System cog loaded successfully")
        
        # Send startup message to health log
        await self.core.send_info_to_health_log(
            "Hospital System has been loaded and is now operational. All medical services are available.",
            "🏥 Hospital System Online"
        )
    
    async def cog_unload(self):
        """Called when the cog is unloaded"""
        logging.info("🏥 Hospital System cog unloaded")
        
        # Send shutdown message to health log
        await self.core.send_warning_to_health_log(
            "Hospital System is being unloaded. Medical services will be temporarily unavailable.",
            "🏥 Hospital System Offline"
        )
    
    # Emergency admin commands that bypass normal restrictions
    
    @commands.command(name="hospital_emergency_status")
    @commands.is_owner()
    async def emergency_status(self, ctx):
        """Emergency status check for bot owner"""
        try:
            await self.core.send_info_to_health_log(
                f"Emergency status check initiated by {ctx.author.display_name}",
                "🚨 Emergency Status Check"
            )
            
            status = await self.get_hospital_status()
            if status:
                embed = discord.Embed(
                    title="🚨 Emergency Hospital Status",
                    color=0xff0000
                )
                
                embed.add_field(
                    name="📊 Current Status",
                    value=f"Total Users: {status['total_users']}\n"
                          f"Unconscious: {status['unconscious_users']}\n"
                          f"In Hospital: {status['users_in_hospital']}\n"
                          f"In Combat: {status['users_in_combat']}\n"
                          f"Conscious in Hospital: {status['conscious_in_hospital']}",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
                # Also send to health log
                await self.core.send_info_to_health_log(
                    f"Emergency status: {status['unconscious_users']} unconscious, {status['users_in_hospital']} in hospital, {status['users_in_combat']} in combat",
                    "📊 Emergency Status Results"
                )
            else:
                await ctx.send("❌ Failed to get hospital status")
                await self.core.send_error_to_health_log(
                    "Emergency status check failed - could not retrieve hospital status",
                    "System may be experiencing issues"
                )
        
        except Exception as e:
            await ctx.send(f"❌ Emergency status check failed: {e}")
            logging.error(f"❌ Emergency status check failed: {e}")
            await self.core.send_error_to_health_log(
                f"Emergency status check failed: {str(e)}",
                "Exception occurred during emergency status check"
            )
    
    @commands.command(name="hospital_force_cycle")
    @commands.is_owner()
    async def force_cycle(self, ctx):
        """Force a hospital processing cycle"""
        try:
            await ctx.send("🏥 Starting forced hospital cycle...")
            
            await self.core.send_info_to_health_log(
                f"Forced hospital cycle initiated by {ctx.author.display_name}",
                "🔧 Manual Cycle Override"
            )
            
            await self.process_unconscious_users()
            await ctx.send("✅ Hospital cycle completed")
            
            await self.core.send_info_to_health_log(
                f"Forced hospital cycle completed successfully by {ctx.author.display_name}",
                "✅ Manual Cycle Complete"
            )
            
        except Exception as e:
            await ctx.send(f"❌ Forced cycle failed: {e}")
            logging.error(f"❌ Forced hospital cycle failed: {e}")
            await self.core.send_error_to_health_log(
                f"Forced hospital cycle failed: {str(e)}",
                f"Manual cycle initiated by {ctx.author.display_name} encountered an error"
            )
    
    @commands.command(name="hospital_system_info")
    @commands.is_owner()
    async def system_info(self, ctx):
        """Get detailed system information"""
        try:
            await self.core.send_info_to_health_log(
                f"System information requested by {ctx.author.display_name}",
                "📋 System Info Request"
            )
            
            embed = discord.Embed(
                title="🏥 Hospital System Information",
                color=0x3498db
            )
            
            # Component status
            embed.add_field(
                name="🔧 Components",
                value=f"Core: {'✅' if self.core else '❌'}\n"
                      f"Financial: {'✅' if self.financial else '❌'}\n"
                      f"Treatment: {'✅' if self.treatment else '❌'}\n"
                      f"Processor: {'✅' if self.processor else '❌'}\n"
                      f"Commands: {'✅' if self.commands else '❌'}\n"
                      f"Stats Commands: {'✅' if self.stats_commands else '❌'}\n"
                      f"Maintenance: {'✅' if hasattr(self.core, 'maintenance') and self.core.maintenance else '❌'}",
                inline=True
            )
            
            # Service costs
            costs = self.get_service_costs()
            embed.add_field(
                name="💰 Service Costs",
                value=f"Transport: ₪{costs['transport']:,}\n"
                      f"Healing per HP: ₪{costs['healing_per_hp']:,}",
                inline=True
            )
            
            # Log statistics
            log_stats = self.get_log_statistics()
            if log_stats:
                embed.add_field(
                    name="📊 Log Statistics",
                    value=f"Total Logs: {log_stats['total_logs']:,}\n"
                          f"Size: {log_stats['estimated_size_mb']} MB\n"
                          f"Recent Activity: {log_stats['recent_activity_7d']} (7d)",
                    inline=True
                )
            
            # System capabilities
            embed.add_field(
                name="⚙️ Capabilities",
                value="• Automatic transport\n"
                      "• Comprehensive healing\n"
                      "• Multiple sessions per cycle\n"
                      "• Indefinite log retention\n"
                      "• Database optimization\n"
                      "• Automatic backups\n"
                      "• Financial management\n"
                      "• Statistics tracking\n"
                      "• Health Log integration",
                inline=False
            )
            
            # Health Log status
            health_log_channel = await self.core.get_health_log_channel()
            if health_log_channel:
                embed.add_field(
                    name="📝 Health Log",
                    value=f"✅ Connected to #{health_log_channel.name}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📝 Health Log",
                    value="❌ No health log channel available",
                    inline=True
                )
            
            # Maintenance info
            if hasattr(self.core, 'maintenance') and self.core.maintenance:
                maintenance_status = self.core.maintenance.get_maintenance_status()
                retention_text = 'Indefinite' if not maintenance_status['retention_enabled'] else f'{maintenance_status["retention_days"]} days'
                embed.add_field(
                    name="🛠️ Maintenance Status",
                    value=f"Log Retention: {retention_text}\n"
                          f"Backups: {'Enabled' if maintenance_status['backup_enabled'] else 'Disabled'}\n"
                          f"Indexes: {'Optimized' if maintenance_status['indexes_enabled'] else 'Basic'}",
                    inline=True
                )
            
            embed.set_footer(text="Hospital System - Enhanced Modular Architecture with Health Log Integration")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ System info failed: {e}")
            logging.error(f"❌ Hospital system info failed: {e}")
            await self.core.send_error_to_health_log(
                f"System info request failed: {str(e)}",
                f"Error occurred while processing info request from {ctx.author.display_name}"
            )
    
    @commands.command(name="hospital_maintenance")
    @commands.is_owner()
    async def perform_maintenance_command(self, ctx, force_backup: bool = False):
        """Perform hospital system maintenance"""
        try:
            await ctx.send("🛠️ Starting hospital system maintenance...")
            
            await self.core.send_info_to_health_log(
                f"System maintenance initiated by {ctx.author.display_name} (force_backup: {force_backup})",
                "🛠️ Maintenance Started"
            )
            
            if hasattr(self.core, 'maintenance') and self.core.maintenance:
                result = self.perform_maintenance(force_backup)
                if result:
                    await ctx.send("✅ Hospital maintenance completed successfully")
                    
                    await self.core.send_info_to_health_log(
                        "System maintenance completed successfully",
                        "✅ Maintenance Complete"
                    )
                    
                    # Show updated statistics
                    stats = self.get_log_statistics()
                    if stats:
                        embed = discord.Embed(
                            title="📊 Post-Maintenance Statistics",
                            color=0x2ecc71
                        )
                        embed.add_field(
                            name="Log Stats",
                            value=f"Total Entries: {stats['total_logs']:,}\n"
                                  f"Estimated Size: {stats['estimated_size_mb']} MB\n"
                                  f"Date Range: {stats['oldest_log']} to {stats['newest_log']}",
                            inline=False
                        )
                        await ctx.send(embed=embed)
                        
                        # Also send to health log
                        await self.core.send_info_to_health_log(
                            f"Post-maintenance statistics: {stats['total_logs']:,} entries, {stats['estimated_size_mb']} MB",
                            "📊 Maintenance Statistics"
                        )
                else:
                    await ctx.send("ℹ️ No maintenance was needed")
                    await self.core.send_info_to_health_log(
                        "No maintenance was required at this time",
                        "ℹ️ Maintenance Skipped"
                    )
            else:
                await ctx.send("❌ Maintenance system not available")
                await self.core.send_error_to_health_log(
                    "Maintenance system not available - maintenance component not loaded",
                    "System may be running in reduced functionality mode"
                )
                
        except Exception as e:
            await ctx.send(f"❌ Maintenance failed: {e}")
            logging.error(f"❌ Hospital maintenance failed: {e}")
            await self.core.send_error_to_health_log(
                f"System maintenance failed: {str(e)}",
                f"Maintenance initiated by {ctx.author.display_name} encountered an error"
            )
    
    @commands.command(name="hospital_log_stats")
    @commands.is_owner()
    async def log_statistics(self, ctx):
        """Get detailed log statistics"""
        try:
            await self.core.send_info_to_health_log(
                f"Log statistics requested by {ctx.author.display_name}",
                "📊 Log Statistics Request"
            )
            
            stats = self.get_log_statistics()
            if not stats:
                await ctx.send("❌ Could not retrieve log statistics")
                await self.core.send_error_to_health_log(
                    "Could not retrieve log statistics - database may be unavailable",
                    "Log statistics request failed"
                )
                return
            
            embed = discord.Embed(
                title="📊 Hospital Log Statistics",
                color=0x3498db
            )
            
            embed.add_field(
                name="📈 Overview",
                value=f"Total Log Entries: {stats['total_logs']:,}\n"
                      f"Estimated Size: {stats['estimated_size_mb']} MB\n"
                      f"Recent Activity (7d): {stats['recent_activity_7d']:,}",
                inline=False
            )
            
            if stats['oldest_log'] and stats['newest_log']:
                embed.add_field(
                    name="📅 Date Range",
                    value=f"Oldest: {stats['oldest_log']}\n"
                          f"Newest: {stats['newest_log']}",
                    inline=True
                )
            
            # Action breakdown
            if stats['action_breakdown']:
                action_text = []
                for action_type, count in stats['action_breakdown'][:10]:  # Top 10
                    action_text.append(f"{action_type}: {count:,}")
                
                embed.add_field(
                    name="🎯 Action Types (Top 10)",
                    value="\n".join(action_text),
                    inline=True
                )
            
            # Maintenance status
            if hasattr(self.core, 'maintenance') and self.core.maintenance:
                maintenance_status = self.core.maintenance.get_maintenance_status()
                retention_text = 'Indefinite retention' if not maintenance_status['retention_enabled'] else f'Cleanup after {maintenance_status["retention_days"]} days'
                embed.add_field(
                    name="🛠️ Retention Policy",
                    value=f"{retention_text}\n"
                          f"Backups: {'Enabled' if maintenance_status['backup_enabled'] else 'Disabled'}",
                    inline=False
                )
            
            embed.set_footer(text="Hospital logs are retained indefinitely by default")
            await ctx.send(embed=embed)
            
            # Send summary to health log
            await self.core.send_info_to_health_log(
                f"Log statistics: {stats['total_logs']:,} entries, {stats['estimated_size_mb']} MB, {stats['recent_activity_7d']:,} recent actions",
                "📊 Current Log Statistics"
            )
            
        except Exception as e:
            await ctx.send(f"❌ Failed to get log statistics: {e}")
            logging.error(f"❌ Failed to get hospital log statistics: {e}")
            await self.core.send_error_to_health_log(
                f"Log statistics request failed: {str(e)}",
                f"Error occurred while processing statistics request from {ctx.author.display_name}"
            )
    
    @commands.command(name="hospital_test_log")
    @commands.is_owner()
    async def test_health_log(self, ctx):
        """Test health log connectivity"""
        try:
            health_log_channel = await self.core.get_health_log_channel()
            
            if health_log_channel:
                await self.core.send_info_to_health_log(
                    f"Health log connectivity test initiated by {ctx.author.display_name}",
                    "🧪 Health Log Test"
                )
                
                await ctx.send(f"✅ Health log test successful! Connected to #{health_log_channel.name}")
                
                # Test different message types
                await self.core.send_text_to_health_log(
                    "This is a test of the standard text logging function.",
                    "📝 Text Log Test"
                )
                
                await self.core.send_warning_to_health_log(
                    "This is a test warning message.",
                    "Warning log functionality test"
                )
                
                await self.core.send_error_to_health_log(
                    "This is a test error message.",
                    "Error log functionality test"
                )
                
                await self.core.send_info_to_health_log(
                    "Health log connectivity test completed successfully. All message types are working.",
                    "✅ Health Log Test Complete"
                )
                
            else:
                await ctx.send("❌ Health log test failed - no health log channel available")
                
        except Exception as e:
            await ctx.send(f"❌ Health log test failed: {e}")
            logging.error(f"❌ Health log test failed: {e}")


async def setup(bot):
    """Setup function for the hospital system cog"""
    await bot.add_cog(HospitalSystem(bot))
    logging.info("✅ Enhanced Hospital System cog loaded successfully with complete Health Log integration")