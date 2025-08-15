#!/bin/bash

# Bot Management Script for New Australia Bot

case "$1" in
    start)
        echo "Starting Australia Bot service..."
        sudo systemctl start australia-bot.service
        sudo systemctl status australia-bot.service
        ;;
    stop)
        echo "Stopping Australia Bot service..."
        sudo systemctl stop australia-bot.service
        sudo systemctl status australia-bot.service
        ;;
    restart)
        echo "Restarting Australia Bot service..."
        sudo systemctl restart australia-bot.service
        sudo systemctl status australia-bot.service
        ;;
    status)
        echo "Checking Australia Bot service status..."
        sudo systemctl status australia-bot.service
        ;;
    logs)
        echo "Showing live logs (Ctrl+C to exit)..."
        sudo journalctl -u australia-bot.service -f
        ;;
    recent)
        echo "Showing recent logs..."
        sudo journalctl -u australia-bot.service -n 30
        ;;
    setup)
        echo "Setting up systemd service..."
        sudo systemctl daemon-reload
        sudo systemctl enable australia-bot.service
        sudo systemctl start australia-bot.service
        sudo systemctl status australia-bot.service
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|recent|setup}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the bot service"
        echo "  stop    - Stop the bot service"
        echo "  restart - Restart the bot service"
        echo "  status  - Check service status"
        echo "  logs    - Show live logs"
        echo "  recent  - Show recent logs"
        echo "  setup   - Initial setup of systemd service"
        exit 1
        ;;
esac
