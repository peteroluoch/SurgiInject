#!/usr/bin/env python3
"""
Unified Dashboard Server for SurgiInject
FastAPI-style WebSocket handler for persistent real-time logging
"""

import asyncio
import json
import logging
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DashboardWebSocketServer:
    def __init__(self, host='localhost', port=8766):
        self.host = host
        self.port = port
        self.connected_clients = set()
        self.event_history = []
        
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.connected_clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")
        
        # Send recent event history to new client
        if self.event_history:
            await websocket.send(json.dumps({
                "type": "history",
                "data": self.event_history[-50:]  # Last 50 events
            }))
    
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.connected_clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")
    
    async def broadcast_log_event(self, data: dict):
        """Broadcast log event to all connected clients (FastAPI style)"""
        stale_clients = []
        for client in self.connected_clients:
            try:
                await client.send_json(data)
            except:
                stale_clients.append(client)
        
        # Clean up stale clients
        for dead in stale_clients:
            await self.unregister_client(dead)
    
    async def broadcast_event(self, event_type, data):
        """Broadcast an event to all connected clients"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > 100:  # Keep last 100 events
            self.event_history = self.event_history[-100:]
        
        # Broadcast using FastAPI-style method
        await self.broadcast_log_event(event)
    
    async def websocket_endpoint(self, websocket, path):
        """FastAPI-style WebSocket endpoint for persistent real-time logging"""
        await self.register_client(websocket)
        
        try:
            # Keep connection alive and ready to send messages
            while True:
                try:
                    # Wait for messages with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    
                    # Handle ping messages
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                        
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    try:
                        await websocket.ping()
                    except:
                        break
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from client")
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Start the WebSocket server with FastAPI-style handler"""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        
        # Create a wrapper function for the websockets library that properly handles the path
        async def handler(websocket, path):
            # Call our websocket endpoint with both websocket and path
            await self.websocket_endpoint(websocket, path)
        
        async with websockets.serve(handler, self.host, self.port):
            logger.info("WebSocket server started successfully")
            await asyncio.Future()  # Run forever
    
    def run(self):
        """Run the server"""
        try:
            asyncio.run(self.start_server())
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")

class DashboardHTTPServer:
    def __init__(self, host='localhost', port=8081):
        self.host = host
        self.port = port
        
    def start(self):
        """Start the HTTP server in a separate thread"""
        def run_server():
            try:
                # Change to dashboard directory
                os.chdir('dashboard')
                
                # Create server
                server = HTTPServer((self.host, self.port), SimpleHTTPRequestHandler)
                logger.info(f"HTTP server started on http://{self.host}:{self.port}")
                server.serve_forever()
            except Exception as e:
                logger.error(f"HTTP server error: {e}")
        
        # Start HTTP server in background thread
        http_thread = Thread(target=run_server, daemon=True)
        http_thread.start()
        return http_thread

def main():
    """Main function to start both servers"""
    # Start HTTP server
    http_server = DashboardHTTPServer()
    http_thread = http_server.start()
    
    # Start WebSocket server
    ws_server = DashboardWebSocketServer()
    
    # Connect injection logger to WebSocket server
    from inject_logger import injection_logger
    injection_logger.set_broadcast_callback(ws_server.broadcast_event)
    
    ws_server.run()

if __name__ == "__main__":
    main() 