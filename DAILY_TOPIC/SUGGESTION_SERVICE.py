from datetime import datetime
from typing import Dict, Any, List
from .DAILY_TOPIC_MODEL import DailyTopicData

class SuggestionService:
    """Handles topic suggestions, approvals, and rejections."""
    
    def __init__(self, data_manager: DailyTopicData):
        self.data_manager = data_manager
    
    def add_suggestion(self, guild_id: int, topic: str, user_id: int) -> Dict[str, Any]:
        """Add a new topic suggestion."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        
        # Check if topic already exists
        if topic.lower() in [t.lower() for t in guild_data["topics"]]:
            return {"success": False, "error": "Topic already exists"}
        
        # Check if already suggested
        if topic.lower() in [s["topic"].lower() for s in guild_data["pending_suggestions"]]:
            return {"success": False, "error": "Topic already suggested"}
        
        suggestion = {
            "topic": topic,
            "suggested_by": user_id,
            "suggested_at": datetime.now().isoformat(),
            "status": "pending"
        }
        guild_data["pending_suggestions"].append(suggestion)
        self.data_manager.save_data()
        
        return {"success": True, "suggestion": suggestion}
    
    def get_pending_suggestions(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all pending suggestions."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        return [s for s in guild_data["pending_suggestions"] if s["status"] == "pending"]
    
    def approve_suggestion(self, guild_id: int, topic: str, approver_id: int) -> Dict[str, Any]:
        """Approve a suggestion."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        
        suggestion = None
        for s in guild_data["pending_suggestions"]:
            if s["topic"].lower() == topic.lower() and s["status"] == "pending":
                suggestion = s
                break
        
        if not suggestion:
            return {"success": False, "error": "Suggestion not found"}
        
        guild_data["topics"].append(suggestion["topic"])
        suggestion["status"] = "approved"
        suggestion["approved_by"] = approver_id
        suggestion["approved_at"] = datetime.now().isoformat()
        
        self.data_manager.save_data()
        return {"success": True, "suggestion": suggestion}
    
    def reject_suggestion(self, guild_id: int, topic: str, rejector_id: int, reason: str = None) -> Dict[str, Any]:
        """Reject a suggestion."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        
        suggestion = None
        for s in guild_data["pending_suggestions"]:
            if s["topic"].lower() == topic.lower() and s["status"] == "pending":
                suggestion = s
                break
        
        if not suggestion:
            return {"success": False, "error": "Suggestion not found"}
        
        suggestion["status"] = "rejected"
        suggestion["rejected_by"] = rejector_id
        suggestion["rejected_at"] = datetime.now().isoformat()
        if reason:
            suggestion["rejection_reason"] = reason
        
        self.data_manager.save_data()
        return {"success": True, "suggestion": suggestion}