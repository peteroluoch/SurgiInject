"""
Injection Queue for Dashboard Diff Preview
Stores pending injection results for real-time preview and approval
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

class InjectionQueue:
    """Global queue for storing pending injection diffs"""
    
    def __init__(self):
        self.pending_injections = []
        self.approved_injections = []
        self.rejected_injections = []
        self.lock = threading.Lock()
        self.queue_file = Path(".surgi_injection_queue.json")
        self._load_queue()
    
    def add_injection_result(
        self, 
        file_path: str, 
        original_content: str, 
        injected_content: str, 
        status: str = "success",
        provider: str = "unknown",
        with_context: bool = False
    ) -> Dict[str, Any]:
        """
        Add an injection result to the pending queue
        
        Args:
            file_path: Path to the injected file
            original_content: Original file content
            injected_content: Injected file content
            status: Injection status (success, weak, duplicate)
            provider: AI provider used
            with_context: Whether context was used
            
        Returns:
            Injection result dictionary
        """
        injection_result = {
            "id": self._generate_id(),
            "file_path": file_path,
            "original": original_content,
            "injected": injected_content,
            "status": status,
            "provider": provider,
            "with_context": with_context,
            "timestamp": datetime.now().isoformat(),
            "approved": False,
            "rejected": False
        }
        
        with self.lock:
            self.pending_injections.append(injection_result)
            self._save_queue()
        
        logger.info(f"Added injection result to queue: {file_path} ({status})")
        return injection_result
    
    def get_pending_injections(self) -> List[Dict[str, Any]]:
        """Get all pending injection results"""
        with self.lock:
            return self.pending_injections.copy()
    
    def approve_injection(self, injection_id: str) -> bool:
        """
        Approve an injection and move it to approved queue
        
        Args:
            injection_id: ID of the injection to approve
            
        Returns:
            True if approved successfully, False otherwise
        """
        with self.lock:
            for i, injection in enumerate(self.pending_injections):
                if injection["id"] == injection_id:
                    injection["approved"] = True
                    injection["approved_at"] = datetime.now().isoformat()
                    
                    # Move to approved queue
                    self.approved_injections.append(injection)
                    self.pending_injections.pop(i)
                    
                    # Save approved content to file
                    self._save_approved_file(injection)
                    
                    self._save_queue()
                    logger.info(f"Approved injection: {injection['file_path']}")
                    return True
        
        return False
    
    def reject_injection(self, injection_id: str) -> bool:
        """
        Reject an injection and move it to rejected queue
        
        Args:
            injection_id: ID of the injection to reject
            
        Returns:
            True if rejected successfully, False otherwise
        """
        with self.lock:
            for i, injection in enumerate(self.pending_injections):
                if injection["id"] == injection_id:
                    injection["rejected"] = True
                    injection["rejected_at"] = datetime.now().isoformat()
                    
                    # Move to rejected queue
                    self.rejected_injections.append(injection)
                    self.pending_injections.pop(i)
                    
                    self._save_queue()
                    logger.info(f"Rejected injection: {injection['file_path']}")
                    return True
        
        return False
    
    def approve_all_strong_injections(self) -> int:
        """
        Automatically approve all injections with 'success' status
        
        Returns:
            Number of injections approved
        """
        approved_count = 0
        
        with self.lock:
            # Get all success injections
            success_injections = [
                inj for inj in self.pending_injections 
                if inj["status"] == "success"
            ]
            
            for injection in success_injections:
                if self.approve_injection(injection["id"]):
                    approved_count += 1
        
        logger.info(f"Auto-approved {approved_count} strong injections")
        return approved_count
    
    def clear_queue(self, queue_type: str = "pending") -> int:
        """
        Clear a specific queue
        
        Args:
            queue_type: Type of queue to clear (pending, approved, rejected, all)
            
        Returns:
            Number of items cleared
        """
        with self.lock:
            if queue_type == "pending":
                count = len(self.pending_injections)
                self.pending_injections.clear()
            elif queue_type == "approved":
                count = len(self.approved_injections)
                self.approved_injections.clear()
            elif queue_type == "rejected":
                count = len(self.rejected_injections)
                self.rejected_injections.clear()
            elif queue_type == "all":
                count = (len(self.pending_injections) + 
                        len(self.approved_injections) + 
                        len(self.rejected_injections))
                self.pending_injections.clear()
                self.approved_injections.clear()
                self.rejected_injections.clear()
            else:
                return 0
            
            self._save_queue()
            logger.info(f"Cleared {count} items from {queue_type} queue")
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.lock:
            return {
                "pending": len(self.pending_injections),
                "approved": len(self.approved_injections),
                "rejected": len(self.rejected_injections),
                "total": (len(self.pending_injections) + 
                         len(self.approved_injections) + 
                         len(self.rejected_injections))
            }
    
    def _generate_id(self) -> str:
        """Generate a unique ID for an injection"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _save_approved_file(self, injection: Dict[str, Any]) -> None:
        """Save approved injection to .approved.surgi file"""
        try:
            file_path = Path(injection["file_path"])
            approved_path = file_path.with_suffix(file_path.suffix + ".approved.surgi")
            
            with open(approved_path, 'w', encoding='utf-8') as f:
                f.write(injection["injected"])
            
            logger.info(f"Saved approved file: {approved_path}")
        except Exception as e:
            logger.error(f"Failed to save approved file: {e}")
    
    def _save_queue(self) -> None:
        """Save queue to disk"""
        try:
            queue_data = {
                "pending": self.pending_injections,
                "approved": self.approved_injections,
                "rejected": self.rejected_injections,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")
    
    def _load_queue(self) -> None:
        """Load queue from disk"""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_data = json.load(f)
                
                self.pending_injections = queue_data.get("pending", [])
                self.approved_injections = queue_data.get("approved", [])
                self.rejected_injections = queue_data.get("rejected", [])
                
                logger.info(f"Loaded queue: {len(self.pending_injections)} pending, "
                          f"{len(self.approved_injections)} approved, "
                          f"{len(self.rejected_injections)} rejected")
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")
            # Initialize empty queues
            self.pending_injections = []
            self.approved_injections = []
            self.rejected_injections = []


# Global injection queue instance
injection_queue = InjectionQueue()


def add_injection_result(
    file_path: str, 
    original_content: str, 
    injected_content: str, 
    status: str = "success",
    provider: str = "unknown",
    with_context: bool = False
) -> Dict[str, Any]:
    """Convenience function to add injection result to queue"""
    return injection_queue.add_injection_result(
        file_path, original_content, injected_content, status, provider, with_context
    )


def get_pending_injections() -> List[Dict[str, Any]]:
    """Convenience function to get pending injections"""
    return injection_queue.get_pending_injections()


def approve_injection(injection_id: str) -> bool:
    """Convenience function to approve injection"""
    return injection_queue.approve_injection(injection_id)


def reject_injection(injection_id: str) -> bool:
    """Convenience function to reject injection"""
    return injection_queue.reject_injection(injection_id)


def get_injection_stats() -> Dict[str, Any]:
    """Convenience function to get injection statistics"""
    return injection_queue.get_stats() 