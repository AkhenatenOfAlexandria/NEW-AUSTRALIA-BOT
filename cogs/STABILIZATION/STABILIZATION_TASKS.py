import logging
from datetime import datetime
from discord.ext import tasks
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .STABILIZATION_PROCESSOR import StabilizationProcessor
    from .STABILIZATION_LOGGER import StabilizationLogger

class StabilizationTasks:
    """Handles background tasks for stabilization system"""
    
    def __init__(self, bot, processor, logger):
        self.bot = bot
        self.processor = processor
        self.logger = logger
        self._tasks_started = False
        
        # Create the task loops as attributes
        self.stabilization_loop = self._create_stabilization_loop()
        self.recovery_loop = self._create_recovery_loop()

    def _create_stabilization_loop(self):
        @tasks.loop(seconds=6)
        async def stabilization_loop():
            # Move the existing stabilization_loop code here
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
        
        return stabilization_loop

    def _create_recovery_loop(self):
        @tasks.loop(minutes=10)
        async def recovery_loop():
            # Move the existing recovery_loop code here
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
        
        return recovery_loop
    
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
    
    def restart_tasks(self):
        """Restart tasks - useful after bot restart"""
        try:
            logging.info("🔄 Restarting stabilization tasks...")
            self.stop_tasks()
            # Small delay to ensure clean shutdown
            import asyncio
            asyncio.create_task(self._delayed_start())
        except Exception as e:
            logging.error(f"Error restarting stabilization tasks: {e}")
    
    async def _delayed_start(self):
        """Start tasks after a small delay"""
        import asyncio
        await asyncio.sleep(1)
        self.start_tasks()
    
    @tasks.loop(seconds=6)  # Check every 6 seconds for stabilization rolls
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
            # Try to restart the loop if it fails
            if not self.stabilization_loop.is_running():
                logging.info("Attempting to restart stabilization loop...")
                try:
                    self.stabilization_loop.restart()
                except:
                    logging.error("Failed to restart stabilization loop")
    
    async def _process_single_stabilization_roll(self, user_data):
        """Process a single user's stabilization roll"""
        user_id = user_data['user_id']
        current_health = user_data.get('current_health', 0)
        
        # Process the stabilization roll
        result = self.processor.process_stabilization_roll(user_id, current_health)
        
        if not result:
            logging.warning(f"No result from stabilization roll for user {user_id}")
            return
        
        # Get user object for logging
        user = self.bot.get_user(user_id)
        if not user:
            logging.warning(f"Could not find user object for user {user_id}")
            return
        
        # Create and send log embed
        embed = self.logger.create_stabilization_embed(
            user,
            result['roll_result'],
            result['process_result'],
            result['old_health'],
            result['new_health']
        )
        
        await self.logger.send_to_log_channel(embed)
        logging.info(f"Processed stabilization roll for user {user_id}: {result['process_result']['result']}")
    
    @tasks.loop(minutes=10)  # Check every 10 minutes for recoveries
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
            # Try to restart the loop if it fails
            if not self.recovery_loop.is_running():
                logging.info("Attempting to restart recovery loop...")
                try:
                    self.recovery_loop.restart()
                except:
                    logging.error("Failed to restart recovery loop")
    
    async def _process_single_recovery(self, user_data):
        """Process a single user's natural recovery"""
        user_id = user_data['user_id']
        
        # Process recovery
        new_health = self.processor.process_recovery(user_id)
        
        if new_health is None:
            return  # No recovery occurred
        
        # Get user object for logging
        user = self.bot.get_user(user_id)
        if not user:
            logging.warning(f"Could not find user object for user {user_id}")
            return
        
        # Create and send recovery embed
        embed = self.logger.create_recovery_embed(user, new_health)
        await self.logger.send_to_log_channel(embed)
        logging.info(f"Processed natural recovery for user {user_id}: recovered to {new_health} HP")
    
    @stabilization_loop.before_loop
    async def before_stabilization_loop(self):
        """Wait for bot to be ready before starting stabilization loop"""
        await self.bot.wait_until_ready()
        logging.info("🎲 Stabilization loop starting...")
    
    @recovery_loop.before_loop
    async def before_recovery_loop(self):
        """Wait for bot to be ready before starting recovery loop"""
        await self.bot.wait_until_ready()
        logging.info("🏥 Recovery loop starting...")
    
    @stabilization_loop.error
    async def stabilization_loop_error(self, exception):
        """Handle errors in stabilization loop"""
        logging.error(f"Stabilization loop error: {exception}")
        # Optionally restart the loop
        # await asyncio.sleep(5)
        # self.stabilization_loop.restart()
    
    @recovery_loop.error
    async def recovery_loop_error(self, exception):
        """Handle errors in recovery loop"""
        logging.error(f"Recovery loop error: {exception}")
        # Optionally restart the loop
        # await asyncio.sleep(5)
        # self.recovery_loop.restart()