import os
import subprocess
import sys


def run():
    """
    Launches the production-grade Next.js frontend (replacing legacy Streamlit).
    Preserves optional --streamlit flag if legacy dashboard is desired.
    """
    if "--streamlit" in sys.argv:
        script_path = os.path.join("app", "dashboard", "dashboard_main.py")
        port = os.getenv("DASHBOARD_PORT", "8501")
        cmd = [
            sys.executable, "-m", "streamlit", "run", script_path,
            "--server.port", port,
            "--server.address", "0.0.0.0"
        ]
        subprocess.run(cmd)
        return

    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    port = os.getenv("PORT", os.getenv("FRONTEND_PORT", "3000"))

    print("=" * 60)
    print("🛡️  Starting Production Next.js LLM Security Dashboard")
    print(f"🌐 Dashboard URL: http://localhost:{port}")
    print("⚡ Design System: Vantis / F5 AI Guardrail (Dark Luxury Console)")
    print("=" * 60)

    # Check if built, else run dev
    build_dir = os.path.join(frontend_dir, ".next")
    if os.path.exists(build_dir):
        cmd = ["npm", "run", "start", "--", "-p", str(port)]
    else:
        cmd = ["npm", "run", "dev", "--", "-p", str(port)]

    subprocess.run(cmd, cwd=frontend_dir)

if __name__ == "__main__":
    run()
