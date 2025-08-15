# HEALING_CALCULATOR.py
import discord

class HealingCalculator:
    """Handles all healing cost calculations"""
    
    HEALING_COST_PER_HP = 1000
    
    def calculate_healing_cost(self, current_health, max_health, amount=None):
        """Calculate cost for healing"""
        if amount is None:
            health_needed = max_health - current_health
        else:
            max_possible = max_health - current_health
            health_needed = min(amount, max_possible)
        
        # Ensure we don't heal negative amounts
        health_needed = max(0, health_needed)
        total_cost = health_needed * self.HEALING_COST_PER_HP
        return health_needed, total_cost
    
    def can_afford_healing(self, user_cash, healing_cost):
        """Check if user can afford healing"""
        return user_cash >= healing_cost
    
    async def show_healing_cost(self, interaction, amount=None):
        """Display healing cost information"""
        user_id = interaction.user.id
        
        # Get user stats
        stats_core = interaction.client.get_cog('StatsCore')
        if not stats_core:
            await interaction.response.send_message("❌ Stats system unavailable.", ephemeral=True)
            return
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            await interaction.response.send_message("❌ No character stats found.", ephemeral=True)
            return
        
        current_health = stats.get('health', 0)
        max_health = self._calculate_max_health(stats, stats_core)
        
        # Calculate costs
        health_needed, cost = self.calculate_healing_cost(current_health, max_health, amount)
        
        embed = discord.Embed(
            title="💰 Healing Cost Calculator",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Current Health", 
            value=f"{current_health}/{max_health} HP", 
            inline=True
        )
        
        if amount:
            embed.add_field(
                name="Requested Healing", 
                value=f"{amount} HP", 
                inline=True
            )
        
        embed.add_field(
            name="Health to Heal", 
            value=f"{health_needed} HP", 
            inline=True
        )
        embed.add_field(
            name="Total Cost", 
            value=f"{cost:,} shekels", 
            inline=True
        )
        embed.add_field(
            name="Rate", 
            value=f"{self.HEALING_COST_PER_HP:,} shekels/HP", 
            inline=True
        )
        
        if health_needed == 0:
            embed.add_field(
                name="Status", 
                value="❌ No healing needed!", 
                inline=False
            )
        else:
            from SHEKELS.BALANCE import BALANCE
            user_balance = BALANCE(interaction.user)  # Pass user object
            can_afford = self.can_afford_healing(user_balance[0], cost)  # Use cash portion
            status = "✅ You can afford this!" if can_afford else "❌ Insufficient funds!"
            embed.add_field(name="Affordability", value=status, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def _calculate_max_health(self, stats, stats_core):
        """Calculate max health from stats"""
        if hasattr(stats_core, 'calculate_health'):
            return stats_core.calculate_health(
                stats.get('constitution', 10), 
                stats.get('level', 1)
            )
        return 100  # Fallback