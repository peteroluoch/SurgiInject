#!/usr/bin/env python3
"""
Simplified Dashboard Server for SurgiInject
Fixes WebSocket connection issues and provides real-time injection monitoring
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
        self.clients = set()
        self.event_history = []
        
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send recent event history to new client
        if self.event_history:
            await websocket.send(json.dumps({
                "type": "history",
                "data": self.event_history[-50:]  # Last 50 events
            }))
    
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
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
        
        # Broadcast to all clients
        if self.clients:
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(json.dumps(event))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    disconnected.add(client)
            
            # Clean up disconnected clients
            for client in disconnected:
                await self.unregister_client(client)
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection with proper signature"""
        await self.register_client(websocket)
        
        try:
            # Keep connection alive with heartbeat
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
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        
        # Create a wrapper function for the websockets library
        async def handler(websocket, path):
            await self.handle_client(websocket, path)
        
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
    ws_server.run()

if __name__ == "__main__":
    main() 