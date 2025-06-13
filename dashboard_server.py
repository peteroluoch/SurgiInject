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
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InjectionDiffsHandler(SimpleHTTPRequestHandler):
    """Enhanced HTTP handler with injection diffs API endpoints"""
    
    def do_GET(self):
        """Handle GET requests for injection diffs API"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Handle injection diffs API endpoints
        if path == '/api/injection-diffs':
            self.handle_injection_diffs()
            return
        elif path == '/api/injection-stats':
            self.handle_injection_stats()
            return
        elif path.startswith('/api/approve-injection/'):
            injection_id = path.split('/')[-1]
            self.handle_approve_injection(injection_id)
            return
        elif path.startswith('/api/reject-injection/'):
            injection_id = path.split('/')[-1]
            self.handle_reject_injection(injection_id)
            return
        elif path == '/api/approve-all-strong':
            self.handle_approve_all_strong()
            return
        elif path == '/api/clear-queue':
            params = parse_qs(parsed_url.query)
            queue_type = params.get('type', ['pending'])[0]
            self.handle_clear_queue(queue_type)
            return
        
        # Default to serving static files
        super().do_GET()
    
    def handle_injection_diffs(self):
        """Handle GET /api/injection-diffs"""
        try:
            from engine.injection_queue import get_pending_injections
            
            injections = get_pending_injections()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response = {
                "status": "success",
                "data": injections,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling injection diffs: {e}")
            self.send_error_response(500, f"Internal server error: {str(e)}")
    
    def handle_injection_stats(self):
        """Handle GET /api/injection-stats"""
        try:
            from engine.injection_queue import get_injection_stats
            
            stats = get_injection_stats()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "success",
                "data": stats,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling injection stats: {e}")
            self.send_error_response(500, f"Internal server error: {str(e)}")
    
    def handle_approve_injection(self, injection_id):
        """Handle GET /api/approve-injection/{id}"""
        try:
            from engine.injection_queue import approve_injection
            
            success = approve_injection(injection_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "success" if success else "error",
                "message": f"Injection {'approved' if success else 'not found'}",
                "injection_id": injection_id,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error approving injection: {e}")
            self.send_error_response(500, f"Internal server error: {str(e)}")
    
    def handle_reject_injection(self, injection_id):
        """Handle GET /api/reject-injection/{id}"""
        try:
            from engine.injection_queue import reject_injection
            
            success = reject_injection(injection_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "success" if success else "error",
                "message": f"Injection {'rejected' if success else 'not found'}",
                "injection_id": injection_id,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error rejecting injection: {e}")
            self.send_error_response(500, f"Internal server error: {str(e)}")
    
    def handle_approve_all_strong(self):
        """Handle GET /api/approve-all-strong"""
        try:
            from engine.injection_queue import approve_all_strong_injections
            
            approved_count = approve_all_strong_injections()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "success",
                "message": f"Approved {approved_count} strong injections",
                "approved_count": approved_count,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error approving all strong injections: {e}")
            self.send_error_response(500, f"Internal server error: {str(e)}")
    
    def handle_clear_queue(self, queue_type):
        """Handle GET /api/clear-queue?type={queue_type}"""
        try:
            from engine.injection_queue import injection_queue
            
            cleared_count = injection_queue.clear_queue(queue_type)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "success",
                "message": f"Cleared {cleared_count} items from {queue_type} queue",
                "cleared_count": cleared_count,
                "queue_type": queue_type,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            self.send_error_response(500, f"Internal server error: {str(e)}")
    
    def send_error_response(self, status_code, message):
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "status": "error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

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
        # Accept all connections regardless of path
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
        
        # Create a wrapper function for the websockets library that accepts all paths
        async def handler(websocket, path):
            # Accept all paths - no validation
            await self.websocket_endpoint(websocket, path)
        
        # Start server with no path restrictions
        server = await websockets.serve(handler, self.host, self.port)
        logger.info("WebSocket server started successfully")
        
        # Keep server running
        await server.wait_closed()
    
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
                server = HTTPServer((self.host, self.port), InjectionDiffsHandler)
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