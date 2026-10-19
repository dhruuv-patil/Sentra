import subprocess
import sys
import os

def run():
    # Set up paths
    script_path = os.path.join("app", "dashboard", "dashboard_main.py")
    
    # Get port from environment (Render default is often 10000, but they provide $PORT)
    port = os.getenv("PORT", "8501")
    
    # Run streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", script_path,
        "--server.port", port,
        "--server.address", "0.0.0.0"
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    run()
