import discord
import logging
from typing import Dict, Any, Optional

# Import configurations
try:
    from UTILS.CONFIGURATION import HEALTH_LOG_ID
except ImportError:
    # Fallback - replace with your actual health log channel ID
    HEALTH_LOG_ID = 123456789

class StabilizationLogger:
    """Handles Discord embeds and logging for stabilization system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.health_log_id = HEALTH_LOG_ID
    
    def create_stabilization_embed(
           self, 
        user: discord.User, 
        roll_result: Dict[str, Any], 
        process_result: Dict[str, Any], 
        old_health: int, 
        new_health: int
    ) -> discord.Embed:
        """Create embed for stabilization roll results"""
        
        # Determine embed color based on result
        result_type = process_result.get('result', 'unknown')
        if result_type in ['stabilized']:
            color = discord.Color.green()
        elif result_type in ['three_failures_restart']:
            color = discord.Color.dark_orange()  # Orange for restart
        elif roll_result['success']:
            color = discord.Color.blue()
        else:
            color = discord.Color.red()
        
        embed = discord.Embed(
            title="🎲 Stabilization Roll",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        # Basic info
        embed.add_field(
            name="Player",
            value=f"{user.display_name} ({user.mention})",
            inline=True
        )
        
        embed.add_field(
            name="Roll",
            value=f"🎲 {roll_result['roll']}/20",
            inline=True
        )
        
        # Result based on process outcome
        result_messages = {
            'success': f"✅ Success ({process_result.get('successes', 0)}/3)",
            'failure': f"❌ Failure ({process_result.get('failures', 0)}/3)",
            'stabilized': "🌟 **STABILIZED!**",
            'three_failures_restart': "⚠️ **3 FAILURES! Lost 1 HP, restarting...**"
        }
        
        embed.add_field(
            name="Result",
            value=result_messages.get(result_type, "❓ Unknown"),
            inline=True
        )
        
        # Health changes
        if old_health != new_health:
            health_change = new_health - old_health
            health_symbol = "+" if health_change > 0 else ""
            embed.add_field(
                name="Health Change",
                value=f"{old_health} → {new_health} ({health_symbol}{health_change})",
                inline=True
            )
        else:
            embed.add_field(
                name="Health",
                value=f"{new_health} HP",
                inline=True
            )
        
        # Progress tracker for ongoing stabilization
        if result_type in ['success', 'failure']:
            embed.add_field(
                name="Progress",
                value=f"Successes: {process_result.get('successes', 0)}/3\nFailures: {process_result.get('failures', 0)}/3",
                inline=True
            )
        elif result_type == 'three_failures_restart':
            embed.add_field(
                name="Progress",
                value="Reset to 0/3 successes, 0/3 failures\nStabilization continues...",
                inline=True
            )
        
        # Special effects
        if roll_result.get('special_effect'):
            effect_descriptions = {
                'natural_20_stabilize': '🌟 **Natural 20!** Stabilized and healed 1 HP',
                'natural_20_restore': '✨ **Natural 20!** Restored 2 HP', 
                'natural_1_critical': '💀 **Natural 1!** Critical failure, lost 2 HP'
            }
            
            effect_desc = effect_descriptions.get(
                roll_result['special_effect'], 
                f"Special effect: {roll_result['special_effect']}"
            )
            
            embed.add_field(
                name="Special Effect",
                value=effect_desc,
                inline=False
            )
    
        embed.set_footer(text="Stabilization System")
        return embed
    
    def create_recovery_embed(self, user: discord.User, new_health: int) -> discord.Embed:
        """Create embed for natural recovery"""
        embed = discord.Embed(
            title="🏥 Natural Recovery",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="Player",
            value=f"{user.display_name} ({user.mention})",
            inline=True
        )
        
        embed.add_field(
            name="Recovery",
            value=f"Recovered to {new_health} HP",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="✅ Stabilized and conscious",
            inline=True
        )
        
        embed.add_field(
            name="Info",
            value="After 1 hour of being stable at 0 HP, you naturally recover 1 HP",
            inline=False
        )
        
        embed.set_footer(text="Stabilization System - Natural Recovery")
        return embed
    
    def create_status_embed(
        self, 
        user: discord.User, 
        current_health: int, 
        max_health: int, 
        status: Optional[Dict[str, Any]]
    ) -> discord.Embed:
        """Create status embed for commands"""
        embed = discord.Embed(
            title="📊 Stabilization Status",
            color=self._get_health_color(current_health),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="Player",
            value=f"{user.display_name} ({user.mention})",
            inline=True
        )
        
        embed.add_field(
            name="Health",
            value=f"{current_health}/{max_health} HP",
            inline=True
        )
        
        # Determine and show status
        if status and status.get('is_unstable'):
            embed.add_field(
                name="Status",
                value="⚠️ **Unconscious and Unstable**",
                inline=True
            )
            
            embed.add_field(
                name="Stabilization Progress",
                value=f"✅ Successes: {status.get('successes', 0)}/3\n❌ Failures: {status.get('failures', 0)}/3",
                inline=True
            )
            
            if status.get('next_roll_time'):
                embed.add_field(
                    name="Next Roll",
                    value=f"<t:{int(status['next_roll_time'].timestamp())}:R>",
                    inline=True
                )
            
            embed.add_field(
                name="Stabilization Rules",
                value="• 3 successes = stabilized\n• 3 failures = death\n• Rolls every 6 seconds",
                inline=False
            )
            
        else:
            if current_health > 0:
                embed.add_field(
                    name="Status", 
                    value="✅ **Stable and Conscious**", 
                    inline=True
                )
            elif current_health == 0:
                embed.add_field(
                    name="Status", 
                    value="💤 **Unconscious but Stable**", 
                    inline=True
                )
                embed.add_field(
                    name="Recovery",
                    value="Will naturally recover 1 HP after 1 hour",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Status", 
                    value="💀 **Unstable**", 
                    inline=True
                )
        
        embed.set_footer(text="Stabilization System")
        return embed
    
    def _get_health_color(self, health: int) -> discord.Color:
        """Get color based on health value"""
        if health > 0:
            return discord.Color.green()
        elif health == 0:
            return discord.Color.orange()
        else:
            return discord.Color.red()
    
    async def send_to_log_channel(self, embed: discord.Embed):
        """Send embed to health log channel with comprehensive fallback"""
        try:
            logging.debug(f"Attempting to send to health log channel ID: {self.health_log_id}")
            
            # Validate channel ID
            if not self.health_log_id or self.health_log_id == 123456789:
                logging.error("Health log channel ID not properly configured!")
                await self._fallback_logging(embed)
                return False
                
            health_log_channel = self.bot.get_channel(self.health_log_id)
            
            if health_log_channel:
                await health_log_channel.send(embed=embed)
                logging.debug(f"Stabilization log sent to {health_log_channel.name}")
                return True
            else:
                logging.warning(f"Health log channel (ID: {self.health_log_id}) not found")
                
        except Exception as e:
            logging.error(f"Error sending to health log channel: {e}")
            
        await self._fallback_logging(embed)
        return False
    
    async def _fallback_logging(self, embed: discord.Embed):
        """Fallback logging methods when primary channel fails"""
        # Log to console as structured data
        embed_text = self._embed_to_text(embed)
        logging.info(f"STABILIZATION_LOG: {embed_text}")
        
        # Try to find any available text channel as last resort
        # (You could implement additional fallback logic here)
        
    def _embed_to_text(self, embed: discord.Embed) -> str:
        """Convert embed to structured text for logging"""
        parts = []
        
        if embed.title:
            parts.append(f"Title='{embed.title}'")
        
        for field in embed.fields:
            # Clean up field values for logging
            clean_value = field.value.replace('\n', ' | ').replace('**', '')
            parts.append(f"{field.name}='{clean_value}'")
        
        if embed.footer and embed.footer.text:
            parts.append(f"Footer='{embed.footer.text}'")
        
        return " || ".join(parts)