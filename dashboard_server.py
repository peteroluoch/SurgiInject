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
import subprocess
import signal
import sys

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
        await self.register_client(websocket)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    try:
                        data = json.loads(message)
                    except Exception as e:
                        logger.error(f"Invalid JSON from client: {e} | Raw: {message}")
                        continue
                    # Handle ping messages
                    if data.get("type") == "ping":
                        try:
                            await websocket.send(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                        except Exception as e:
                            logger.error(f"Failed to send pong: {e}")
                        continue
                    # Log and ignore unknown message types
                    logger.info(f"Received unknown message type: {data.get('type')} | Data: {data}")
                except asyncio.TimeoutError:
                    try:
                        await websocket.ping()
                    except Exception as e:
                        logger.error(f"Ping failed, closing connection: {e}")
                        break
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed by client.")
                    break
                except Exception as e:
                    logger.error(f"Error in websocket_endpoint loop: {e}")
                    break
        except Exception as e:
            logger.error(f"websocket_endpoint outer error: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Start the WebSocket server with proper WebSocket upgrade handling"""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        
        async def handler(websocket, path):
            logger.info(f"WebSocket connection attempt from {getattr(websocket, 'remote_address', None)} on path: {path}")
            try:
                await self.websocket_endpoint(websocket, path)
            except Exception as e:
                logger.error(f"Error in WebSocket handler: {e}")
                try:
                    await websocket.close(1011, "Internal server error")
                except Exception as close_e:
                    logger.error(f"Error closing websocket: {close_e}")
        
        try:
            # Try to start server with port reuse
            server = await websockets.serve(
                handler,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
                reuse_address=True,
                reuse_port=True
            )
            logger.info("WebSocket server started successfully")
            await server.wait_closed()
        except OSError as e:
            if "Address already in use" in str(e) or "10048" in str(e):
                logger.error(f"Port {self.port} is already in use. Please stop any existing server first.")
                logger.info("Try: netstat -ano | findstr :8766  # to find process using port 8766")
            else:
                logger.error(f"Failed to start WebSocket server: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
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

def kill_process_on_port(port):
    """Kill process using the specified port (Windows)"""
    try:
        # Find process using the port
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/PID', pid, '/F'], check=True)
                        logger.info(f"Killed process {pid} using port {port}")
                        return True
                    except subprocess.CalledProcessError:
                        logger.warning(f"Failed to kill process {pid}")
        return False
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
        return False

def main():
    """Main function to start both servers"""
    # Check and kill any existing process on WebSocket port
    if kill_process_on_port(8766):
        logger.info("Cleared port 8766 for WebSocket server")
    
    # Start HTTP server
    http_server = DashboardHTTPServer()
    http_thread = http_server.start()
    
    # Start WebSocket server
    ws_server = DashboardWebSocketServer()
    
    # Connect injection logger to WebSocket server
    from inject_logger import injection_logger
    injection_logger.set_broadcast_callback(ws_server.broadcast_event)
    
    try:
        ws_server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 