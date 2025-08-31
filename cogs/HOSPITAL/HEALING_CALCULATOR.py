# HEALING_CALCULATOR.py
import discord

class HealingCalculator:
    """Handles all healing cost calculations"""
    
    HEALING_COST = 5000
    
    def calculate_healing_cost(self, current_health, max_health, amount=None):
        max_possible_heal = max_health - current_health
        
        if max_possible_heal <= 0:
            return 0,0
        
        total_cost = self.HEALING_COST if max_possible_heal > 0 else 0

        return max_possible_heal, total_cost

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
            await interaction.response.send_message("❌ No user stats found.", ephemeral=True)
            return
        
        current_health = stats.get('health', 0)
        max_health = self._calculate_max_health(stats, stats_core)
        
        # Calculate costs
        health_to_heal, cost = self.calculate_healing_cost(current_health, max_health)
        
        
        embed = discord.Embed(
            title="💰 Healing Cost Calculator",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Current Health", 
            value=f"{current_health}/{max_health} HP", 
            inline=True
        )
        
        embed.add_field(
            name="Health per Heal",
            value=f"{self.HEALING_AMOUNT} HP",
            inline=True
        )
        
        embed.add_field(
            name="Will Heal", 
            value=f"{health_to_heal} HP", 
            inline=True
        )

        embed.add_field(
            name="Cost per Heal", 
            value=f"{self.HEALING_COST} shekels", 
            inline=True
        )
        embed.add_field(
            name="Rate", 
            value=f"{self.HEALING_COST_PER_HP:,} shekels/HP", 
            inline=True
        )
        
        if health_to_heal == 0:
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
        
            # Show how many heals needed for full health

        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    def _calculate_max_health(self, stats, stats_core):
        """Calculate max health from stats"""
        if hasattr(stats_core, 'calculate_health'):
            return stats_core.calculate_health(
                stats.get('constitution', 10), 
                stats.get('level', 1)
            )
        return 100  # Fallback