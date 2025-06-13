from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="SurgiInject Dashboard", version="1.0.0")

# Get the directory where this server file is located
SERVER_DIR = Path(__file__).parent
FRONTEND_DIR = SERVER_DIR / "frontend"

print(f"Server directory: {SERVER_DIR}")
print(f"Frontend directory: {FRONTEND_DIR}")
print(f"Frontend exists: {FRONTEND_DIR.exists()}")

# Mount static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def get_dashboard():
    """Serve the main dashboard page"""
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "surgiinject-dashboard"
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting minimal server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 