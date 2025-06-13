"""
WebSocket server for real-time SurgiInject dashboard

Serves injection events and statistics to connected dashboard clients.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Set
import websockets
from websockets.server import WebSocketServerProtocol

from inject_logger import injection_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardWebSocketServer:
    """WebSocket server for real-time dashboard updates"""
    
    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
    
    async def register_client(self, websocket: WebSocketServerProtocol):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        injection_logger.add_websocket_client(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send initial data
        await self.send_initial_data(websocket)
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        injection_logger.remove_websocket_client(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def send_initial_data(self, websocket: WebSocketServerProtocol):
        """Send initial data to a new client"""
        data = {
            "type": "initial_data",
            "recent_events": injection_logger.get_recent_events(),
            "stats": injection_logger.get_stats()
        }
        await websocket.send(json.dumps(data))
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast an event to all connected clients"""
        if not self.clients:
            return
        
        message = {
            "type": "injection_event",
            "data": event_data
        }
        
        # Send to all connected clients
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket client connection"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from client")
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle incoming messages from clients"""
        message_type = data.get("type")
        
        if message_type == "get_stats":
            response = {
                "type": "stats_update",
                "data": injection_logger.get_stats()
            }
            await websocket.send(json.dumps(response))
        
        elif message_type == "get_recent_events":
            limit = data.get("limit", 50)
            response = {
                "type": "events_update",
                "data": injection_logger.get_recent_events(limit)
            }
            await websocket.send(json.dumps(response))
        
        elif message_type == "ping":
            response = {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(response))
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        
        # Update the injection logger to use our broadcast method
        injection_logger._broadcast_to_clients = self.broadcast_event
        
        # Create a wrapper function for the websockets library
        async def handler(websocket, path):
            await self.handle_client(websocket)
        
        async with websockets.serve(handler, self.host, self.port):
            logger.info("WebSocket server started successfully")
            await asyncio.Future()  # run forever
    
    def run(self):
        """Run the server in the current event loop"""
        asyncio.run(self.start_server())

# HTTP server for serving the dashboard
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os

class DashboardHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP handler for serving the dashboard"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def start_http_server(port: int = 8081):
    """Start HTTP server for dashboard"""
    os.chdir("dashboard")  # Serve from dashboard directory
    httpd = HTTPServer(("localhost", port), DashboardHTTPHandler)
    logger.info(f"HTTP server started on http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Start WebSocket server
    server = DashboardWebSocketServer()
    server.run() 