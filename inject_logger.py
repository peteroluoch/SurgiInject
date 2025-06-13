"""
Real-time injection logger for SurgiInject dashboard

Handles emission of injection events to WebSocket clients for live dashboard updates.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class InjectionEvent:
    """Data class for injection events"""
    status: str  # start, success, error, cache_hit, escalation
    timestamp: str
    prompt_file: Optional[str] = None
    target_file: Optional[str] = None
    provider: Optional[str] = None
    tokens: Optional[int] = None
    cached: Optional[bool] = None
    result_preview: Optional[str] = None
    error: Optional[str] = None
    escalation_triggered: Optional[bool] = None
    cache_hit: Optional[bool] = None
    fallback_used: Optional[bool] = None

class InjectionLogger:
    """Real-time injection event logger"""
    
    def __init__(self):
        self.events = []
        self.max_events = 100  # Keep last 100 events in memory
        self.websocket_clients = []
    
    def emit_event(self, event_data: Dict[str, Any]) -> None:
        """
        Emit an injection event to all connected clients
        
        Args:
            event_data: Dictionary containing event data
        """
        # Create event with timestamp
        event = InjectionEvent(
            timestamp=datetime.utcnow().isoformat(),
            **event_data
        )
        
        # Add to events list (FIFO)
        self.events.append(asdict(event))
        if len(self.events) > self.max_events:
            self.events.pop(0)
        
        # Log to file
        logger.info(f"Injection Event: {event.status} - {event.target_file or 'N/A'}")
        
        # Broadcast to WebSocket clients
        self._broadcast_to_clients(asdict(event))
    
    def emit_start(self, prompt_file: str, target_file: str, provider: str, cached: bool = False) -> None:
        """Emit injection start event"""
        self.emit_event({
            "status": "start",
            "prompt_file": prompt_file,
            "target_file": target_file,
            "provider": provider,
            "cached": cached
        })
    
    def emit_cache_hit(self, target_file: str, provider: str) -> None:
        """Emit cache hit event"""
        self.emit_event({
            "status": "cache_hit",
            "target_file": target_file,
            "provider": provider,
            "cache_hit": True
        })
    
    def emit_success(self, target_file: str, provider: str, tokens: int, result_preview: str) -> None:
        """Emit successful injection event"""
        self.emit_event({
            "status": "success",
            "target_file": target_file,
            "provider": provider,
            "tokens": tokens,
            "result_preview": result_preview[:120] + "..." if len(result_preview) > 120 else result_preview
        })
    
    def emit_escalation(self, target_file: str, provider: str, escalation_provider: str) -> None:
        """Emit escalation event"""
        self.emit_event({
            "status": "escalation",
            "target_file": target_file,
            "provider": provider,
            "escalation_triggered": True,
            "result_preview": f"Escalated to {escalation_provider}"
        })
    
    def emit_fallback(self, target_file: str, failed_provider: str, fallback_provider: str) -> None:
        """Emit fallback event"""
        self.emit_event({
            "status": "fallback",
            "target_file": target_file,
            "provider": fallback_provider,
            "fallback_used": True,
            "result_preview": f"Fell back from {failed_provider} to {fallback_provider}"
        })
    
    def emit_error(self, target_file: str, provider: str, error: str) -> None:
        """Emit error event"""
        self.emit_event({
            "status": "error",
            "target_file": target_file,
            "provider": provider,
            "error": str(error)
        })
    
    def get_recent_events(self, limit: int = 50) -> list:
        """Get recent injection events"""
        return self.events[-limit:] if self.events else []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get injection statistics"""
        if not self.events:
            return {
                "total_injections": 0,
                "successful_injections": 0,
                "failed_injections": 0,
                "cache_hits": 0,
                "escalations": 0,
                "fallbacks": 0,
                "total_tokens": 0,
                "providers_used": {}
            }
        
        stats = {
            "total_injections": len([e for e in self.events if e["status"] == "start"]),
            "successful_injections": len([e for e in self.events if e["status"] == "success"]),
            "failed_injections": len([e for e in self.events if e["status"] == "error"]),
            "cache_hits": len([e for e in self.events if e["status"] == "cache_hit"]),
            "escalations": len([e for e in self.events if e["status"] == "escalation"]),
            "fallbacks": len([e for e in self.events if e["status"] == "fallback"]),
            "total_tokens": sum([e.get("tokens", 0) for e in self.events if e.get("tokens")]),
            "providers_used": {}
        }
        
        # Count provider usage
        for event in self.events:
            provider = event.get("provider")
            if provider:
                stats["providers_used"][provider] = stats["providers_used"].get(provider, 0) + 1
        
        return stats
    
    def _broadcast_to_clients(self, event_data: Dict[str, Any]) -> None:
        """Broadcast event to all connected WebSocket clients"""
        # This will be implemented when we add WebSocket support
        # For now, just log the event
        logger.debug(f"Broadcasting event: {event_data}")
    
    def add_websocket_client(self, client) -> None:
        """Add a WebSocket client for real-time updates"""
        self.websocket_clients.append(client)
    
    def remove_websocket_client(self, client) -> None:
        """Remove a WebSocket client"""
        if client in self.websocket_clients:
            self.websocket_clients.remove(client)

# Global injection logger instance
injection_logger = InjectionLogger() 