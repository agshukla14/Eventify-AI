import os
import sys
import subprocess
import time
import socket
from pathlib import Path

# Safe UTF-8 reconfiguration for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
DB_FILE = BASE_DIR / "celebration_planner.db"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a given port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def ensure_frontend_build():
    """Ensures frontend is built. If missing, attempts to build using npm."""
    if FRONTEND_INDEX.is_file():
        print("[OK] Frontend production build found in frontend/dist.")
        return True

    print("[INFO] Frontend production build (frontend/dist) not found.")
    print("[INFO] Attempting to build frontend automatically...")

    # Check for npm
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        subprocess.run([npm_cmd, "--version"], capture_output=True, check=True, cwd=str(FRONTEND_DIR))
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[WARN] Node.js / npm is not installed or not in PATH.")
        print("[WARN] The backend will start, but frontend assets must be built manually:")
        print("       cd frontend && npm install && npm run build")
        return False

    # Check node_modules
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.is_dir():
        print("[INFO] Installing frontend dependencies (npm install)...")
        try:
            subprocess.run([npm_cmd, "install"], check=True, cwd=str(FRONTEND_DIR))
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] npm install failed: {e}")
            return False

    # Run npm run build
    print("[INFO] Compiling frontend (npm run build)...")
    try:
        subprocess.run([npm_cmd, "run", "build"], check=True, cwd=str(FRONTEND_DIR))
        if FRONTEND_INDEX.is_file():
            print("[OK] Frontend compiled successfully!")
            return True
        else:
            print("[WARN] npm run build completed, but frontend/dist/index.html is missing.")
            return False
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] npm run build failed: {e}")
        return False


def ensure_seed_data():
    """Seeds the database if empty so demo data is instantly available."""
    try:
        from backend.app.database import SessionLocal, Base, engine
        from backend.app.models import EventModel
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        count = db.query(EventModel).count()
        db.close()
        if count == 0:
            print("[INFO] Database has 0 events. Seeding demo events...")
            from backend.app.seed_data import seed_all
            seed_all()
        else:
            print(f"[OK] Database connected with {count} saved celebration(s).")
    except Exception as e:
        print(f"[WARN] Database initialization notice: {e}")


def main():
    print("=" * 66)
    print("Celebration & Event Planner Assistant (FastAPI + React UI)")
    print("=" * 66)

    # 1. Check frontend build
    ensure_frontend_build()

    # 2. Check & seed database
    ensure_seed_data()

    # 3. Port check
    port = 8000
    if is_port_in_use(port):
        print(f"[WARN] Port {port} appears to be in use.")
        print(f"       If another instance is running, you can access it at http://localhost:{port}")
        print(f"       Otherwise, please terminate the process using port {port} or wait a moment.")

    print("=" * 66)
    print("  Website URL:       http://localhost:8000")
    print("  Backend API:       http://localhost:8000/api/health")
    print("  Interactive Docs:  http://localhost:8000/docs")
    print("=" * 66)
    print("Starting server... Press Ctrl+C to stop.")
    print("=" * 66)

    try:
        import uvicorn
        uvicorn.run(
            "backend.app.main:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user.")
    except Exception as e:
        print(f"\n[ERROR] Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
