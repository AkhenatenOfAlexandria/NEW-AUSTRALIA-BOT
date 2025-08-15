import discord
import traceback
import logging
from discord.ext import commands

class HospitalIntegration:
    def __init__(self, bot):
        self.bot = bot
        self._register_commands()

    def _register_commands(self):
        """Register hospital-related commands"""
        @self.bot.command(name="hospital_debug")
        @commands.is_owner()
        async def hospital_debug(ctx):
            await self._hospital_debug(ctx)

        @self.bot.command(name="hospital_trigger")
        @commands.is_owner()
        async def hospital_trigger(ctx):
            await self._hospital_trigger(ctx)

        @self.bot.command(name="health_log_test")
        @commands.is_owner()
        async def health_log_test(ctx):
            await self._health_log_test(ctx)

    async def _hospital_debug(self, ctx):
        """Debug hospital system status"""
        try:
            hospital_system = self.bot.get_cog('HospitalSystem')
            
            if not hospital_system:
                await ctx.send("❌ HospitalSystem cog not found!")
                return
            
            embed = discord.Embed(
                title="🏥 Hospital System Debug",
                color=0x3498db
            )
            
            # Check components
            components = {
                "Core": hospital_system.core,
                "Financial": hospital_system.financial,
                "Treatment": hospital_system.treatment,
                "Processor": hospital_system.processor,
                "Commands": hospital_system.commands,
                "Stats Commands": hospital_system.stats_commands
            }
            
            component_status = []
            for name, component in components.items():
                status = "✅" if component else "❌"
                component_status.append(f"{status} {name}")
            
            embed.add_field(
                name="🔧 Components",
                value="\n".join(component_status),
                inline=True
            )
            
            # Check health log connectivity
            try:
                health_log = await hospital_system.core.get_health_log_channel()
                if health_log:
                    embed.add_field(
                        name="📝 Health Log",
                        value=f"✅ Connected to #{health_log.name}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="📝 Health Log",
                        value="❌ No health log channel",
                        inline=True
                    )
            except Exception as e:
                embed.add_field(
                    name="📝 Health Log",
                    value=f"❌ Error: {str(e)}",
                    inline=True
                )
            
            # Check hospital status
            try:
                status = await hospital_system.get_hospital_status()
                if status:
                    embed.add_field(
                        name="🏥 Current Status",
                        value=f"Unconscious: {status['unconscious_users']}\nIn Hospital: {status['users_in_hospital']}\nIn Combat: {status['users_in_combat']}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🏥 Current Status",
                        value="❌ Could not retrieve status",
                        inline=False
                    )
            except Exception as e:
                embed.add_field(
                    name="🏥 Current Status",
                    value=f"❌ Error: {str(e)}",
                    inline=False
                )
            
            # Check task status
            task_status = []
            task_status.append(f"{'✅' if self.bot.task_manager.hospital_update.is_running() else '❌'} Hospital Update Loop")
            task_status.append(f"{'✅' if self.bot.task_manager.stock_update.is_running() else '❌'} Stock Update Loop")
            task_status.append(f"{'✅' if self.bot.task_manager.treasury_update.is_running() else '❌'} Treasury Update Loop")
            
            embed.add_field(
                name="⚡ Tasks",
                value="\n".join(task_status),
                inline=True
            )
            
            await ctx.send(embed=embed)
            
            # Test health log
            if hospital_system:
                await hospital_system.core.send_info_to_health_log(
                    f"Hospital system debug check performed by {ctx.author.display_name}",
                    "🔍 Debug Check"
                )
            
        except Exception as e:
            await ctx.send(f"❌ Debug failed: {e}")
            logging.error(f"Hospital debug failed: {e}")
            traceback.print_exc()

    async def _hospital_trigger(self, ctx):
        """Manually trigger a hospital update for testing"""
        try:
            await ctx.send("🏥 Manually triggering hospital update...")
            
            hospital_system = self.bot.get_cog('HospitalSystem')
            if hospital_system:
                await hospital_system.core.send_info_to_health_log(
                    f"Manual hospital update triggered by {ctx.author.display_name}",
                    "🔧 Manual Trigger"
                )
            
            await self.bot.task_manager._hospital_update()
            await ctx.send("✅ Hospital update completed")
            
        except Exception as e:
            await ctx.send(f"❌ Manual hospital trigger failed: {e}")
            logging.error(f"Manual hospital trigger failed: {e}")
            traceback.print_exc()

    async def _health_log_test(self, ctx):
        """Test health log connectivity"""
        try:
            hospital_system = self.bot.get_cog('HospitalSystem')
            
            if not hospital_system:
                await ctx.send("❌ HospitalSystem cog not found!")
                return
            
            # Test health log connectivity
            health_log = await hospital_system.core.get_health_log_channel()
            
            if health_log:
                await ctx.send(f"✅ Health log connected to #{health_log.name}")
                
                # Send test messages
                await hospital_system.core.send_info_to_health_log(
                    f"Health log connectivity test initiated by {ctx.author.display_name}",
                    "🧪 Connectivity Test"
                )
                
                await hospital_system.core.send_text_to_health_log(
                    "This is a test message to verify health log functionality.",
                    "📝 Test Message"
                )
                
                await hospital_system.core.send_warning_to_health_log(
                    "This is a test warning message.",
                    "Test warning functionality"
                )
                
                await hospital_system.core.send_error_to_health_log(
                    "This is a test error message.",
                    "Test error functionality"
                )
                
                await hospital_system.core.send_info_to_health_log(
                    "Health log connectivity test completed successfully.",
                    "✅ Test Complete"
                )
                
                await ctx.send("✅ Health log test completed - check the health log channel")
            else:
                await ctx.send("❌ No health log channel available")
                
        except Exception as e:
            await ctx.send(f"❌ Health log test failed: {e}")
            logging.error(f"Health log test failed: {e}")
            traceback.print_exc()