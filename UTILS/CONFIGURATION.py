import discord

DEBUG_MODE = False

GUILD_ID = 574731470900559872

ANNOUNCEMENTS_ID = 1110265000876052490
GAMES_ID = 824436480180092969
GENERAL_ID = 574731470900559874
MONEY_LOG_ID = 636723720387428392
HEALTH_LOG_ID = 1404033603620442184

# Hospital System Configuration
HOSPITAL_TRANSPORT_COST = 1000  # Cost in shekels for emergency transport
HOSPITAL_HEALING_COST_PER_HP = 1000  # Cost in shekels per health point healed

# Hospital System Settings
HOSPITAL_CYCLE_INTERVAL = 300  # Seconds between hospital cycles (default: 5 minutes)
HOSPITAL_MAX_HEALING_SESSIONS = 10  # Maximum healing sessions per user per cycle

# Hospital Log Retention Settings
HOSPITAL_LOG_RETENTION_DAYS = None  # Set to None for indefinite retention, or number of days
HOSPITAL_ENABLE_LOG_CLEANUP = False  # Set to True to enable automatic log cleanup
HOSPITAL_LOG_CLEANUP_INTERVAL_DAYS = 7  # How often to run cleanup (if enabled)

# Database Performance Settings (for indefinite logs)
HOSPITAL_LOG_INDEX_OPTIMIZATION = True  # Create database indexes for better performance
HOSPITAL_LOG_BATCH_SIZE = 1000  # Batch size for bulk operations

# Backup Settings (recommended for indefinite retention)
HOSPITAL_ENABLE_LOG_BACKUP = True  # Enable periodic log backups
HOSPITAL_BACKUP_INTERVAL_DAYS = 30  # Days between backups
HOSPITAL_BACKUP_LOCATION = "backups/hospital_logs/"  # Directory for log backups

# Define intents
intents = discord.Intents.all()
intents.messages = True  # This enables the 'messages' intent, required for most commands
intents.message_content = True
intents.members = True
intents.typing = True
intents.presences = True