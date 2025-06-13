from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
import logging
from pathlib import Path

# Import the new API routers
from api.preview import router as preview_router
from api.apply import router as apply_router

app = FastAPI(title="SurgiInject Dashboard", version="1.0.0")

# Get the directory where this server file is located
SERVER_DIR = Path(__file__).parent
FRONTEND_DIR = SERVER_DIR / "frontend"

# Add the new API routes
app.include_router(preview_router, prefix="/api/preview", tags=["preview"])
app.include_router(apply_router, prefix="/api/apply", tags=["apply"])

# Mount static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/")
async def get_dashboard():
    """Serve the main dashboard page"""
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": asyncio.get_event_loop().time()}),
                    websocket
                )
            elif message.get("type") == "preview_request":
                # Handle preview requests
                await manager.send_personal_message(
                    json.dumps({
                        "type": "preview_response",
                        "data": {"status": "processing", "message": "Preview request received"}
                    }),
                    websocket
                )
            elif message.get("type") == "apply_request":
                # Handle apply requests
                await manager.send_personal_message(
                    json.dumps({
                        "type": "apply_response",
                        "data": {"status": "processing", "message": "Apply request received"}
                    }),
                    websocket
                )
            else:
                # Echo back unknown messages
                await manager.send_personal_message(
                    json.dumps({"type": "echo", "data": message}),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "surgiinject-dashboard",
        "websocket_connections": len(manager.active_connections)
    }

@app.get("/api/files/discover")
async def discover_files(root: str = ".", extensions: str = None):
    """Discover files in the project directory"""
    try:
        root_path = Path(root)
        if not root_path.exists():
            return {"files": [], "error": "Directory not found"}
        
        if extensions:
            ext_list = extensions.split(',')
        else:
            ext_list = ['.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css']
        
        files = []
        for ext in ext_list:
            files.extend([str(f.relative_to(root_path)) for f in root_path.rglob(f"*{ext}")])
        
        return {"files": sorted(files)}
    except Exception as e:
        return {"files": [], "error": str(e)}

@app.get("/api/prompts/list")
async def list_prompts():
    """List available prompt templates"""
    try:
        prompts_dir = Path("prompts")
        if not prompts_dir.exists():
            return {"prompts": []}
        
        prompt_files = [f.name for f in prompts_dir.glob("*.txt")]
        return {"prompts": sorted(prompt_files)}
    except Exception as e:
        return {"prompts": [], "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 