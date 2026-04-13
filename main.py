import pickle
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import os

# Use the correct import based on your logic file's name
# If your file is named 'simulate.py', use this:
from simulate import run_simulation
# If your file is named 'simulation_logic.py', use this:
# from simulation_logic import run_simulation


# --- Pydantic Models for Request/Response ---

class SimulationRequest(BaseModel):
    driver_name: str
    race_name: str
    pit_stop_loss: float
    grid_position: int = 0  # Optional: driver's grid position (0 = pole, field_size = last)
    weather: str = 'DRY'    # Optional: weather condition
    use_ga_optimizer: bool = True  # Optional: use Genetic Algorithm (default) or brute force
    use_monte_carlo: bool = True   # Optional: enable Monte Carlo analysis
    sc_laps: List[List[int]] = []  # Optional: safety car info [[start_lap, duration], ...]

class LapsResponse(BaseModel):
    total_laps: int

class APIDataResponse(BaseModel):
    drivers: List[str]
    races: List[str]

# --- Load Database on Startup ---

DB_FILE = "strategy_database.pkl"
strategy_database: Dict = {}

def load_database():
    """Loads the strategy database from the .pkl file."""
    global strategy_database
    try:
        with open(DB_FILE, 'rb') as f:
            strategy_database = pickle.load(f)
        print(f"[OK] Master database loaded successfully from {DB_FILE}")
    except FileNotFoundError:
        print(f"[ERROR] '{DB_FILE}' not found.")
        print("Please ensure 'precompute.py' has run and the file is in the same directory.")
        strategy_database = {} # Ensure it's an empty dict
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred loading the database: {e}")
        strategy_database = {}

# --- FastAPI App Initialization ---

app = FastAPI(title="F1 Strategy Simulator API")

# Add CORS middleware to allow the frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (good for local dev)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Serve Static Files (Lap Visualizer Component) ---
@app.get("/lap-visualizer.js", response_class=FileResponse)
async def get_lap_visualizer_js():
    """Serves the lap visualizer JavaScript component."""
    if os.path.exists("lap-visualizer.js"):
        return FileResponse("lap-visualizer.js", media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="lap-visualizer.js not found")

@app.get("/lap-visualizer.css", response_class=FileResponse)
async def get_lap_visualizer_css():
    """Serves the lap visualizer CSS styling."""
    if os.path.exists("lap-visualizer.css"):
        return FileResponse("lap-visualizer.css", media_type="text/css")
    else:
        raise HTTPException(status_code=404, detail="lap-visualizer.css not found")

@app.on_event("startup")
async def startup_event():
    """Run on server startup."""
    load_database()

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_frontend(request: Request):
    """Serves the main index.html file."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>index.html not found</h1><p>Please add the frontend file to your project directory.</p>", status_code=404)

@app.get("/api-data", response_model=APIDataResponse)
async def get_api_data():
    """Provides the lists of available drivers and races for dropdowns."""
    if not strategy_database:
        raise HTTPException(status_code=503, detail="Database not loaded. Run precompute.py and restart server.")
    
    try:
        drivers = sorted([driver for driver in strategy_database['driver_performance'].keys() if driver != 'GRID_AVG'])
        races = sorted(strategy_database['track_models'].keys())
        
        return APIDataResponse(drivers=drivers, races=races)
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Database is missing expected key: {e}")

@app.get("/get-laps/{race_name}", response_model=LapsResponse)
async def get_laps_for_race(race_name: str):
    """Provides the total lap count for a selected race."""
    if not strategy_database:
        raise HTTPException(status_code=503, detail="Database not loaded.")
        
    try:
        total_laps = strategy_database['track_models'][race_name]['total_laps']
        
        # --- FIX: Convert numpy.int64 to standard Python int ---
        return LapsResponse(total_laps=int(total_laps))
    
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Race '{race_name}' not found in database.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@app.post("/simulate")
async def simulate_strategy_endpoint(request: SimulationRequest):
    """Runs the main simulation logic with advanced features."""
    if not strategy_database:
        raise HTTPException(status_code=503, detail="Database not loaded. Run precompute.py and restart server.")

    print(f"--- Simulating for {request.driver_name} at {request.race_name} ---")
    print(f"    Weather: {request.weather}, Grid Position: {request.grid_position}")
    print(f"    GA Optimizer: {request.use_ga_optimizer}, Monte Carlo: {request.use_monte_carlo}")

    try:
        # Convert safety car laps from list to tuple format
        sc_laps = [(sc[0], sc[1]) for sc in request.sc_laps] if request.sc_laps else None

        results = run_simulation(
            driver_name=request.driver_name,
            race_name=request.race_name,
            pit_stop_loss=request.pit_stop_loss,
            db=strategy_database,
            use_ga_optimizer=request.use_ga_optimizer,
            use_monte_carlo=request.use_monte_carlo,
            grid_position=request.grid_position,
            weather=request.weather,
            sc_laps=sc_laps
        )

        if "error" in results:
            raise HTTPException(status_code=404, detail=results["error"])

        return results

    except Exception as e:
        print(f"❌ ERROR during simulation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- Uvicorn runner (for local testing) ---
if __name__ == "__main__":
    import uvicorn
    print("--- Starting F1 Strategy Simulator API ---")
    print("Access the frontend at: http://127.0.0.1:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

