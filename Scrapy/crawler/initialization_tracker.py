"""Initialization tracker stored in MongoDB.

Allows the Webapp to display a loading page until initial scraping
steps are completed.
"""

import os
from datetime import datetime
from typing import Any, Optional

from pymongo import MongoClient

class InitializationTracker:
    """Gère l'état d'initialisation du projet dans MongoDB."""

    def __init__(self) -> None:
        """Initialise la connexion MongoDB et la collection de statut."""
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
        self.client = MongoClient(mongo_uri)
        self.db = self.client['flashscore']
        self.collection = self.db['initialization_status']
        
    def init_status(self) -> None:
        """Reset the status document and start at 0%.

        Returns:
            None
        """
        self.collection.delete_many({})
        self.collection.insert_one({
            "status": "initializing",
            "started_at": datetime.utcnow().isoformat(),
            "current_step": "Démarrage...",
            "steps": {
                "mongodb_setup": {"status": "pending", "progress": 0},
                "classements": {"status": "pending", "progress": 0},
                "top5_leagues": {"status": "pending", "progress": 0},
                "other_leagues_upcoming": {"status": "pending", "progress": 0},
                "finished_matches": {"status": "pending", "progress": 0},
                "season_history": {"status": "pending", "progress": 0},
                "smart_catalog": {"status": "pending", "progress": 0}
            },
            "overall_progress": 0,
            "completed_at": None
        })
    
    def update_step(
        self,
        step_name: str,
        status: str,
        progress: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        """Update a step and recalculate overall progress.

        Args:
            step_name (str): Step name (e.g., "top5_leagues").
            status (str): Step status (pending/running/completed/failed).
            progress (Optional[int]): Step progress (0-100).
            details (Optional[str]): Displayable text for UI.

        Returns:
            None
        """
        update = {
            f"steps.{step_name}.status": status,
            "current_step": details or step_name
        }
        
        if progress is not None:
            update[f"steps.{step_name}.progress"] = progress
        
        # Calculate overall progress
        doc: Optional[dict[str, Any]] = self.collection.find_one({})
        if doc:
            steps = doc.get("steps", {})
            total_progress = sum(s.get("progress", 0) for s in steps.values())
            overall = int(total_progress / len(steps))
            update["overall_progress"] = overall
        
        self.collection.update_one({}, {"$set": update})
    
    def mark_completed(self) -> None:
        """Mark initialization as completed (100%).

        Returns:
            None
        """
        self.collection.update_one({}, {
            "$set": {
                "status": "completed",
                "current_step": "Initialization completed",
                "overall_progress": 100,
                "completed_at": datetime.utcnow().isoformat()
            }
        })
    
    def get_status(self) -> Optional[dict[str, Any]]:
        """Return the status document without MongoDB ID.

        Returns:
            Optional[dict[str, Any]]: Status document, or None if absent.
        """
        return self.collection.find_one({}, {"_id": 0})
    
    def is_initialized(self) -> bool:
        """Indicate if initialization is completed.

        Returns:
            bool: True if `status == "completed"`, False otherwise.
        """
        doc = self.collection.find_one({})
        return bool(doc and doc.get("status") == "completed")
    
    def close(self) -> None:
        """Close the MongoDB client.

        Returns:
            None
        """
        self.client.close()
