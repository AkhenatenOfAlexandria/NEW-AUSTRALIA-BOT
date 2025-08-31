import logging
from datetime import datetime
from discord.ext import tasks

class StabilizationTasks:
    """Handles background tasks for stabilization system"""
    
    def __init__(self, bot, processor, logger):
        self.bot = bot
        self.processor = processor
        self.logger = logger
        self._tasks_started = False
    
    def start_tasks(self):
        """Start all background tasks"""
        try:
            if not self._tasks_started:
                self.stabilization_loop.start()
                self.recovery_loop.start()
                self._tasks_started = True
                logging.info("✅ Stabilization background tasks started")
            else:
                logging.warning("Stabilization tasks already running")
        except Exception as e:
            logging.error(f"Error starting stabilization tasks: {e}")
            raise
    
    def stop_tasks(self):
        """Stop all background tasks"""
        try:
            if self._tasks_started:
                if self.stabilization_loop.is_running():
                    self.stabilization_loop.cancel()
                if self.recovery_loop.is_running():
                    self.recovery_loop.cancel()
                self._tasks_started = False
                logging.info("⚠️ Stabilization background tasks stopped")
        except Exception as e:
            logging.error(f"Error stopping stabilization tasks: {e}")
    
    @tasks.loop(seconds=6)
    async def stabilization_loop(self):
        """Process pending stabilization rolls"""
        try:
            current_time = datetime.now()
            pending_users = self.processor.database.get_pending_rolls(current_time)
            
            if pending_users:
                logging.debug(f"Found {len(pending_users)} users ready for stabilization rolls")
            
            for user_data in pending_users:
                try:
                    await self._process_single_stabilization_roll(user_data)
                except Exception as e:
                    logging.error(f"Error processing stabilization roll for user {user_data.get('user_id', 'unknown')}: {e}")
        except Exception as e:
            logging.error(f"Error in stabilization loop: {e}")
    
    @tasks.loop(minutes=10)
    async def recovery_loop(self):
        """Process natural recovery for stabilized players"""
        try:
            current_time = datetime.now()
            recovery_users = self.processor.database.get_ready_for_recovery(current_time)
            
            if recovery_users:
                logging.debug(f"Processing {len(recovery_users)} potential recoveries")
            
            for user_data in recovery_users:
                try:
                    await self._process_single_recovery(user_data)
                except Exception as e:
                    logging.error(f"Error processing recovery for user {user_data.get('user_id', 'unknown')}: {e}")
        except Exception as e:
            logging.error(f"Error in recovery loop: {e}")
    
    async def _process_single_stabilization_roll(self, user_data):
        """Process a single user's stabilization roll"""
        user_id = user_data['user_id']
        current_health = user_data.get('current_health', 0)
        
        result = self.processor.process_stabilization_roll(user_id, current_health)
        
        if not result:
            logging.warning(f"No result from stabilization roll for user {user_id}")
            return
        
        user = self.bot.get_user(user_id)
        if not user:
            logging.warning(f"Could not find user object for user {user_id}")
            return
        
        embed = self.logger.create_stabilization_embed(
            user,
            result['roll_result'],
            result['process_result'],
            result['old_health'],
            result['new_health']
        )
        
        await self.logger.send_to_log_channel(embed)
        logging.info(f"Processed stabilization roll for user {user_id}: {result['process_result']['result']}")
    
    async def _process_single_recovery(self, user_data):
        """Process a single user's natural recovery"""
        user_id = user_data['user_id']
        
        new_health = self.processor.process_recovery(user_id)
        
        if new_health is None:
            return
        
        user = self.bot.get_user(user_id)
        if not user:
            logging.warning(f"Could not find user object for user {user_id}")
            return
        
        embed = self.logger.create_recovery_embed(user, new_health)
        await self.logger.send_to_log_channel(embed)
        logging.info(f"Processed natural recovery for user {user_id}: recovered to {new_health} HP")
    
    @stabilization_loop.before_loop
    async def before_stabilization_loop(self):
        await self.bot.wait_until_ready()
        logging.info("🎲 Stabilization loop starting...")
    
    @recovery_loop.before_loop
    async def before_recovery_loop(self):
        await self.bot.wait_until_ready()
        logging.info("🏥 Recovery loop starting...")