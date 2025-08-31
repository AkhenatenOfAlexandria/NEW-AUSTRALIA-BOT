# HEALING_SERVICE.py - WITH DEBUG LOGGING
import discord
import random
import logging
from datetime import datetime

from SHEKELS.BALANCE import BALANCE
from SHEKELS.TRANSFERS import UPDATE_BALANCE
from .HEALING_CALCULATOR import HealingCalculator
from .HEALING_LOGGER import HealingLogger
from .HEALING_DATABASE import HealingDatabase
from .HEALING_VALIDATORS import HealingValidators

HEALING_COST = 5000

class HealingService:
    """Core healing business logic"""
    
    def __init__(self, bot):
        self.bot = bot
        self.calculator = HealingCalculator()
        self.logger = HealingLogger(bot)
        self.database = HealingDatabase()
        self.validators = HealingValidators(bot)
    
    async def process_healing_request(self, interaction, amount=None):
        """Main healing logic"""
        user_id = interaction.user.id

        if amount is not None:
            embed = discord.Embed(
                title="ℹ️ Fixed Healing System",
                description=f"This system now uses fixed healing costs. Each heal costs **{HEALING_COST:,}** shekels.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Validation
        validation_result = await self._validate_healing_request(interaction)
        if not validation_result['valid']:
            embed = discord.Embed(
                title="❌ Cannot Heal",
                description=validation_result['reason'],
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Calculate healing needs
        healing_data = await self._calculate_healing_needs(interaction)
        if not healing_data:
            return
        
        # Check if user can afford healing
        user_balance = BALANCE(interaction.user)  # Pass user object, not user_id
        logging.info(f"🏥 Healing: User {interaction.user.display_name} balance: {user_balance}")
        
        if not self.calculator.can_afford_healing(user_balance[0], healing_data['cost']):  # Use cash portion
            embed = discord.Embed(
                title="💸 Insufficient Funds",
                description=f"You need **{healing_data['cost']:,}** shekels but only have **{user_balance[0]:,}** shekels in cash.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Process payment and healing
        await self._execute_healing(interaction, healing_data)
    
    async def _validate_healing_request(self, interaction):
        """Validate if user can be healed"""
        user_id = interaction.user.id
        
        # Check if user is in combat
        '''if self.validators.is_user_in_combat(user_id):
            return {'valid': False, 'reason': "You cannot heal while in combat!"}'''
        
        # Validate user stats exist
        stats, error = self.validators.validate_user_stats(user_id)
        if not stats:
            return {'valid': False, 'reason': error or "Unable to retrieve your stats."}
        
        # Check if user is conscious
        if stats.get('health', 0) <= 0:
            return {'valid': False, 'reason': "You must be conscious to heal yourself!"}
        
        # Check if user is already at full health
        current_health = stats.get('health', 0)
        max_health = self._calculate_max_health(stats)
        
        if current_health >= max_health:
            return {'valid': False, 'reason': "You are already at full health!"}
        
        return {'valid': True, 'stats': stats}
    
    def _calculate_max_health(self, stats):
        """Calculate max health from stats"""
        stats_core = self.bot.get_cog('StatsCore')
        if stats_core and hasattr(stats_core, 'calculate_health'):
            return stats_core.calculate_health(
                stats.get('constitution', 10), 
                stats.get('level', 1)
            )
        return 100  # Fallback
    
    async def _calculate_healing_needs(self, interaction):
        """Calculate what healing is needed and costs"""
        user_id = interaction.user.id
        
        # Get user stats
        stats_core = self.bot.get_cog('StatsCore')
        if not stats_core:
            await interaction.response.send_message("❌ Stats system unavailable.", ephemeral=True)
            return None
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            await interaction.response.send_message("❌ No user stats found.", ephemeral=True)
            return None
        
        current_health = stats.get('health', 0)
        max_health = self._calculate_max_health(stats)
        
        # Calculate healing amount and cost
        _h, total_cost = self.calculator.calculate_healing_cost(
            current_health, max_health
        )
        
        if _h <= 0:
            embed = discord.Embed(
                title="❌ No Healing Needed",
                description="You don't need any healing!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None
        
        health_to_heal = random.randint(1,4) + random.randint(1,4) + 2
        health_to_heal = min(health_to_heal, max_health)

        return {
            'user_id': user_id,
            'current_health': current_health,
            'max_health': max_health,
            'health_to_heal': health_to_heal,
            'cost': total_cost,
            'new_health': current_health + health_to_heal
        }
    
    async def _execute_healing(self, interaction, healing_data):
        """Execute the actual healing transaction"""
        user_id = healing_data['user_id']
        cost = healing_data['cost']
        new_health = healing_data['new_health']
        health_healed = healing_data['health_to_heal']
        
        # Debug logging
        logging.info(f"🏥 Attempting to charge {interaction.user.display_name} {cost} shekels for {health_healed} HP")
        
        # Check balance one more time before payment
        pre_balance = BALANCE(interaction.user)
        logging.info(f"🏥 Pre-payment balance: Cash={pre_balance[0]}, Bank={pre_balance[1]}")
        
        # Deduct payment
        try:
            payment_success = UPDATE_BALANCE(interaction.user, -cost, "CASH")
            logging.info(f"🏥 UPDATE_BALANCE returned: {payment_success}")
            
            # Check balance after payment attempt
            post_balance = BALANCE(interaction.user)
            logging.info(f"🏥 Post-payment balance: Cash={post_balance[0]}, Bank={post_balance[1]}")
            
        except Exception as e:
            logging.error(f"🏥 UPDATE_BALANCE failed with exception: {e}")
            payment_success = False
        
        if not payment_success:
            embed = discord.Embed(
                title="❌ Payment Failed",
                description="Unable to process payment. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update health in database
        health_update_success = self.database.restore_health_to_database(user_id, new_health)
        if not health_update_success:
            # Refund payment if health update failed
            logging.warning(f"🏥 Health update failed, refunding {cost} shekels")
            refund_success = UPDATE_BALANCE(interaction.user, cost, "CASH")
            logging.info(f"🏥 Refund successful: {refund_success}")
            
            embed = discord.Embed(
                title="❌ Healing Failed",
                description="Unable to update your health. Payment has been refunded.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Log the transaction
        self.database.log_healing_transaction(user_id, health_healed, cost, True)
        
        # Create success embed
        embed = discord.Embed(
            title="🏥 Healing Successful",
            description=f"You have been healed for **{cost:,}** shekels!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Health Restored", 
            value=f"{health_healed} HP", 
            inline=True
        )
        embed.add_field(
            name="New Health", 
            value=f"{new_health}/{healing_data['max_health']} HP", 
            inline=True
        )
        embed.add_field(
            name="Cost", 
            value=f"{cost:,} shekels", 
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log to healing system
        await self.logger.log_healing_action(
            interaction.user, 
            "healing",
            health_healed=health_healed,
            cost=cost,
            new_health=new_health,
            max_health=healing_data['max_health']
        )
    
    async def show_infirmary_info(self, interaction):
        """Show infirmary information"""
        user_id = interaction.user.id
        
        # Get user stats
        stats_core = self.bot.get_cog('StatsCore')
        if not stats_core:
            await interaction.response.send_message("❌ Stats system unavailable.", ephemeral=True)
            return
        
        stats = stats_core.get_user_stats(user_id)
        user_balance = BALANCE(interaction.user)  # Pass user object
        
        embed = discord.Embed(
            title="🏥 Infirmary Information",
            description="Welcome to the ASTRIFER Co. Infirmary! Here you can restore your health for shekels.",
            color=discord.Color.blue()
        )
        
        if stats:
            current_health = stats.get('health', 0)
            max_health = self._calculate_max_health(stats)
            health_needed = max_health - current_health

            embed.add_field(
                name="Your Health", 
                value=f"{current_health}/{max_health} HP", 
                inline=True
            )
            embed.add_field(
                name="Your Balance", 
                value=f"{user_balance[0]:,} shekels", 
                inline=True
            )
        
        embed.add_field(
            name="Healing System", 
            value=f"**Cost:** {HEALING_COST:,} shekels per heal", 
            inline=False
        )
        embed.add_field(
            name="Commands", 
            value=f"• `/heal` - Heal for {HEALING_COST} shekels\n `/healing_cost` - Check healing costs", 
            inline=False
        )
        embed.set_footer(text="Note: You cannot heal while unconscious.")
        
        await interaction.response.send_message(embed=embed)