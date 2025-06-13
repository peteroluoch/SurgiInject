# SurgiInject Dashboard Usage Guide

## Overview

The SurgiInject dashboard provides real-time monitoring of injection events, including:
- Live injection events (start, success, error, escalation, cache hits, fallbacks)
- Real-time statistics
- Event history
- WebSocket-based real-time updates

## Quick Start

### 1. Start the Dashboard Server

```bash
python dashboard_server.py
```

This starts both:
- **HTTP Server**: `http://localhost:8081` (serves the dashboard UI)
- **WebSocket Server**: `ws://localhost:8766` (real-time events)

### 2. Open the Dashboard

Navigate to: `http://localhost:8081`

### 3. Run Injections

In another terminal, run your injections:

```bash
python cli.py inject -f your_file.py -p "your prompt" --debug
```

Watch real-time events appear in the dashboard!

## Dashboard Features

### Real-Time Events
- **Start**: Injection process begins
- **Success**: Injection completed successfully
- **Error**: Injection failed with error details
- **Escalation**: Weak response triggered escalation
- **Cache Hit**: Used cached result
- **Fallback**: Provider fallback occurred

### Statistics
- Total injections
- Successful injections
- Failed injections
- Escalations
- Cache hits
- Fallbacks

### Event History
- Last 100 events stored in memory
- New clients receive last 50 events on connection
- Real-time updates for all connected clients

## Technical Details

### Server Architecture
- **Single Process**: One Python process handles both HTTP and WebSocket
- **Threaded HTTP**: HTTP server runs in background thread
- **Async WebSocket**: WebSocket server runs in main async loop
- **Event Broadcasting**: All injection events broadcast to connected clients

### Connection Management
- **Automatic Reconnection**: Client automatically reconnects on disconnect
- **Heartbeat**: 30-second ping/pong to keep connections alive
- **Client Cleanup**: Disconnected clients automatically removed

### Event Flow
1. Injection starts → `emit_start()` → Dashboard shows start event
2. Injection succeeds → `emit_success()` → Dashboard shows success
3. Errors occur → `emit_error()` → Dashboard shows error details
4. Escalations → `emit_escalation()` → Dashboard shows escalation
5. Cache hits → `emit_cache_hit()` → Dashboard shows cache usage
6. Fallbacks → `emit_fallback()` → Dashboard shows provider changes

## Troubleshooting

### WebSocket Connection Issues
- Check if server is running: `python dashboard_server.py`
- Verify ports are free: `netstat -an | findstr ":8081\|:8766"`
- Kill existing processes: `taskkill /f /im python.exe`

### No Events Showing
- Ensure `--debug` flag is used: `python cli.py inject --debug`
- Check server logs for connection messages
- Verify injection logger is properly connected

### Dashboard Not Loading
- Check HTTP server: `curl http://localhost:8081`
- Verify dashboard files exist in `dashboard/` directory
- Check browser console for JavaScript errors

## Advanced Usage

### Custom Event Types
Add custom events in your code:

```python
from inject_logger import injection_logger

# Emit custom event
injection_logger._emit_event("custom_type", {
    "message": "Custom event data",
    "timestamp": datetime.now().isoformat()
})
```

### Multiple Dashboard Instances
Run multiple dashboards on different ports:

```python
# Modify dashboard_server.py
http_server = DashboardHTTPServer(port=8082)
ws_server = DashboardWebSocketServer(port=8767)
```

### Event Filtering
Filter events in the dashboard JavaScript:

```javascript
// In dashboard/index.html
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'success') {
        // Handle only success events
    }
};
```

## Performance Notes

- **Memory Usage**: ~1MB for 100 events in history
- **Network**: Minimal WebSocket traffic (JSON events)
- **CPU**: Low overhead for event broadcasting
- **Scalability**: Supports multiple concurrent clients

## Security Considerations

- **Local Only**: Server binds to localhost only
- **No Authentication**: Intended for local development
- **Event Data**: Contains file paths and code snippets
- **Logging**: Events logged to console and injection.log

## Next Steps

- Add authentication for production use
- Implement event persistence to database
- Add event filtering and search
- Create mobile-responsive dashboard
- Add real-time charts and graphs 