import os
import shutil
import time
import uuid
import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Optional, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import uvicorn

# Import configuration and agents
from config import Config
from agents.compliance_agent import ComplianceAgent

# Import telemetry
from telemetry import init_tracing

# Import Pydantic models
from models.api_models import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    HealthCheckResponse,
    ErrorResponse
)
from models.common_models import ComplianceEvaluationModel

# Global variables to store system components
compliance_agent = None

# WebSocket session management
active_sessions: Dict[str, asyncio.Queue] = {}
cancel_events: Dict[str, threading.Event] = {}

# Initialize system components
def initialize_system():
    """Initialize system components"""
    try:
        # Initialize Phoenix tracing if enabled
        if Config.PHOENIX_ENABLED:
            print("Initializing Phoenix tracing...")
            tracer_provider = init_tracing()
            if tracer_provider:
                print(f"Note: Traces will be sent to {Config.PHOENIX_ENDPOINT}")
            else:
                print("Phoenix tracing initialization failed, continuing without tracing")
        else:
            print("Phoenix tracing disabled in configuration")

        # Validate configuration
        Config.validate()

        # Initialize compliance agent
        agent = ComplianceAgent()

        return agent
        
    except Exception as e:
        print(f"System initialization failed: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler"""
    global compliance_agent

    # Startup
    try:
        print("Initializing building code compliance check system ...")
        compliance_agent = initialize_system()
        print("System initialization completed!")
    except Exception as e:
        print(f"System initialization failed: {e}")
        # Create default components to avoid startup failure
        compliance_agent = ComplianceAgent()

    yield

    # Shutdown
    print("Shutting down building code compliance check system...")

# Create FastAPI application with lifespan
app = FastAPI(
    title="Building Code Compliance Check System",
    description="Multi-agent IFC file building code compliance check system",
    version="1.0.0",
    lifespan=lifespan
)

# Enable gzip to speed up large text responses like IFC files.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Configure templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root path, returns web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/assets/{file_path:path}")
async def serve_assets(file_path: str):
    """Serve static assets"""
    print(f"[ASSETS] Request for: {file_path}")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    asset_file = os.path.join(base_dir, "templates", "assets", file_path)
    print(f"[ASSETS] Looking for file at: {asset_file}")
    print(f"[ASSETS] File exists: {os.path.exists(asset_file)}")
    if os.path.exists(asset_file):
        print(f"[ASSETS] Serving file: {asset_file}")
        return FileResponse(asset_file)
    print(f"[ASSETS] File not found!")
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/wasm/{file_path:path}")
async def serve_wasm(file_path: str):
    """Serve WASM files for IFC loader"""
    print(f"[WASM] Request for: {file_path}")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    wasm_file = os.path.join(base_dir, "templates", "wasm", file_path)
    print(f"[WASM] Looking for file at: {wasm_file}")
    if os.path.exists(wasm_file):
        print(f"[WASM] Serving file: {wasm_file}")
        return FileResponse(wasm_file, media_type="application/wasm")
    print(f"[WASM] File not found!")
    raise HTTPException(status_code=404, detail="WASM file not found")

@app.get("/examples/ifc/{file_name}")
async def serve_example_ifc(file_name: str):
    """Serve example IFC models"""
    if file_name != "M02_no_space.ifc":
        raise HTTPException(status_code=404, detail="Example IFC not found")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    example_file = os.path.join(base_dir, "dataset", "ifc_models", file_name)
    if os.path.exists(example_file):
        return FileResponse(example_file, media_type="application/octet-stream", filename=file_name)

    raise HTTPException(status_code=404, detail="Example IFC not found")

@app.post("/check/start")
async def start_compliance_check(
    regulation: str = Form(..., description="Building code text"),
    ifc_file: UploadFile = File(..., description="IFC file"),
    api_key: Optional[str] = Form(None, description="Optional API key override")
):
    """Start compliance check and return session ID for WebSocket connection"""
    try:
        # Validate request data using Pydantic
        try:
            request_data = ComplianceCheckRequest(regulation=regulation)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid regulation text: {str(e)}")

        # Validate file type
        if not ifc_file.filename.lower().endswith('.ifc'):
            raise HTTPException(status_code=400, detail="Only IFC file format is supported")

        api_key = api_key.strip() if api_key and api_key.strip() else None

        # Save uploaded file
        file_path = os.path.join(Config.UPLOAD_DIR, ifc_file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(ifc_file.file, buffer)

        print(f"File saved: {file_path}")
        print(f"Code text: {request_data.regulation[:100]}...")

        # Generate unique session ID
        session_id = str(uuid.uuid4())[:8]
        print(f"[Session] Created session: {session_id}")

        # Create message queue for this session
        message_queue = asyncio.Queue(maxsize=1000)
        active_sessions[session_id] = message_queue
        cancel_event = threading.Event()
        cancel_events[session_id] = cancel_event

        # Get event loop reference BEFORE creating callback
        event_loop = asyncio.get_event_loop()

        # Define callback for ComplianceAgent to send real-time updates
        def iteration_callback(data: Dict):
            """Thread-safe callback from sync agent to async queue"""
            try:
                # Add timestamp if not present
                if "timestamp" not in data:
                    data["timestamp"] = datetime.now().isoformat()

                # Use saved event loop reference (not get_event_loop() which fails in executor thread)
                asyncio.run_coroutine_threadsafe(
                    message_queue.put(data),
                    event_loop
                )
            except Exception as e:
                print(f"[Callback Error] {e}")

        # Run agent in background
        async def run_agent_background():
            """Background task to run compliance check"""
            try:
                print(f"[Session {session_id}] Starting compliance check...")
                start_time = time.time()

                # Create agent instance with callback
                agent = ComplianceAgent(
                    iteration_callback=iteration_callback,
                    api_key=api_key,
                    cancel_event=cancel_event
                )

                # Run agent in executor (non-blocking)
                loop = asyncio.get_event_loop()
                agent_result = await loop.run_in_executor(
                    None,
                    agent.execute_compliance_check,
                    request_data.regulation,
                    file_path
                )

                runtime = time.time() - start_time
                print(f"[Session {session_id}] Compliance check finished (runtime: {runtime:.2f}s)")

                # Send completion message
                completion_message = {
                    "type": "completion",
                    "status": agent_result.status,
                    "compliance_result": agent_result.compliance_result.model_dump() if agent_result.compliance_result else None,
                    "error": agent_result.error,
                    "timestamp": datetime.now().isoformat()
                }
                await message_queue.put(completion_message)

            except Exception as e:
                print(f"[Session {session_id}] Agent error: {e}")
                error_message = {
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                await message_queue.put(error_message)

            finally:
                # Cleanup temporary file
                try:
                    os.remove(file_path)
                    print(f"[Session {session_id}] Cleaned up file: {file_path}")
                except Exception as e:
                    print(f"[Session {session_id}] File cleanup error: {e}")

        # Start background task
        asyncio.create_task(run_agent_background())

        # Return session ID immediately
        return {"session_id": session_id}

    except Exception as e:
        print(f"Error starting check: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start check: {str(e)}")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time compliance check updates"""
    await websocket.accept()
    print(f"[WebSocket] Client connected: {session_id}")

    # Get or create message queue for this session
    if session_id not in active_sessions:
        active_sessions[session_id] = asyncio.Queue()

    message_queue = active_sessions[session_id]

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })

        # Send queued messages to client
        while True:
            message = await message_queue.get()
            await websocket.send_json(message)

            # Stop after final message
            if message.get("type") in ["completion", "error"]:
                print(f"[WebSocket] Final message sent for session: {session_id}")
                await asyncio.sleep(0.5)  # Allow client to process
                break

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[WebSocket] Error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
    finally:
        # Cleanup session after delay
        asyncio.create_task(cleanup_session(session_id, delay=60))

@app.post("/check/stop")
async def stop_compliance_check(session_id: str = Form(..., description="Session ID")):
    """Request to stop a running compliance check session."""
    cancel_event = cancel_events.get(session_id)
    if not cancel_event:
        raise HTTPException(status_code=404, detail="Session not found")

    cancel_event.set()
    return {"status": "cancel_requested", "session_id": session_id}


async def cleanup_session(session_id: str, delay: int = 60):
    """Remove session after delay to prevent memory leaks"""
    await asyncio.sleep(delay)
    if session_id in active_sessions:
        print(f"[Cleanup] Removing session: {session_id}")
        active_sessions.pop(session_id)
    cancel_events.pop(session_id, None)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check interface"""
    return HealthCheckResponse(
        status="healthy",
        system="Building Code Compliance Check System",
        version="3.0.0",
        components={
            "compliance_agent": "ready",
            "agent_tools": "ready"
        }
    )

if __name__ == "__main__":
    # Start server
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        reload_excludes=["ifc_tools/generated/**/*.py"],  # Exclude dynamically generated tools from hot reload
        log_level="info"
    ) 
