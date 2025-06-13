#!/usr/bin/env python3
"""
Injection Logger for SurgiInject
Handles real-time event emission to dashboard
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InjectionLogger:
    def __init__(self):
        self.events = []
        self.stats = {
            "total_injections": 0,
            "successful_injections": 0,
            "failed_injections": 0,
            "escalations": 0,
            "cache_hits": 0,
            "fallbacks": 0
        }
        self._broadcast_callback = None
    
    def set_broadcast_callback(self, callback):
        """Set the callback function for broadcasting events"""
        self._broadcast_callback = callback
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event and broadcast it if callback is set"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log the event
        logger.info(f"Injection Event: {event_type} - {data.get('target_file', 'unknown')}")
        
        # Store in events list
        self.events.append(event)
        if len(self.events) > 100:  # Keep last 100 events
            self.events = self.events[-100:]
        
        # Broadcast if callback is set
        if self._broadcast_callback:
            try:
                asyncio.create_task(self._broadcast_callback(event_type, data))
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}")
    
    def emit_start(self, prompt_file: str, target_file: str, provider: str, cached: bool = False):
        """Emit injection start event"""
        self.stats["total_injections"] += 1
        self._emit_event("start", {
            "prompt_file": prompt_file,
            "target_file": target_file,
            "provider": provider,
            "cached": cached
        })
    
    def emit_success(self, target_file: str, provider: str, tokens: int, result_preview: str):
        """Emit injection success event"""
        self.stats["successful_injections"] += 1
        self._emit_event("success", {
            "target_file": target_file,
            "provider": provider,
            "tokens": tokens,
            "result_preview": result_preview
        })
    
    def emit_error(self, target_file: str, provider: str, error: str):
        """Emit injection error event"""
        self.stats["failed_injections"] += 1
        self._emit_event("error", {
            "target_file": target_file,
            "provider": provider,
            "error": error
        })
    
    def emit_escalation(self, target_file: str, provider: str, escalation_provider: str):
        """Emit escalation event"""
        self.stats["escalations"] += 1
        self._emit_event("escalation", {
            "target_file": target_file,
            "provider": provider,
            "escalation_provider": escalation_provider
        })
    
    def emit_cache_hit(self, target_file: str, provider: str):
        """Emit cache hit event"""
        self.stats["cache_hits"] += 1
        self._emit_event("cache_hit", {
            "target_file": target_file,
            "provider": provider
        })
    
    def emit_fallback(self, target_file: str, failed_provider: str, fallback_provider: str):
        """Emit fallback event"""
        self.stats["fallbacks"] += 1
        self._emit_event("fallback", {
            "target_file": target_file,
            "failed_provider": failed_provider,
            "fallback_provider": fallback_provider
        })
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events"""
        return self.events[-limit:] if self.events else []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self.stats.copy()

# Global instance
injection_logger = InjectionLogger()

# Import asyncio for async operations
import asyncio 