# 🖥️ Desktop Deployment Guide — AND9 / JARVIS PCOS

This guide provides step-by-step instructions for deploying and running **AND9 / JARVIS PCOS** on a desktop environment (Linux, macOS, or Windows WSL2), both **with Docker** and **without Docker**.

---

## 📋 Prerequisites & Requirements

Before starting, ensure your system meets the basic requirements:

- **OS**: Linux (Ubuntu/Debian recommended), macOS, or Windows with WSL2.
- **Git**: Installed on system.
- **Port 8000**: Ensure port `8000` (or your configured port) is available.
- **API Keys**: Groq API key (Required for LLM processing). Obtain from [Groq Console](https://console.groq.com/).

---

## 🐳 Option 1: Deploying & Running WITH Docker (Recommended)

Docker provides an isolated, reliable environment with pre-configured Python dependencies and data persistence.

### Step 1: Install Docker & Docker Compose
Ensure Docker Engine / Docker Desktop and Docker Compose are installed:
```bash
docker --version
docker compose version
```

### Step 2: Configure Environment Variables
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` to include your API keys:
   ```env
   GROQ_API_KEY=gsk_your_actual_groq_api_key
   SECRET_KEY=your-random-secret-key
   FLASK_ENV=production
   ```

### Step 3: Build and Start Container
Run Docker Compose in detached mode to build and start the service:
```bash
docker compose up --build -d
```

### Step 4: Verify Container Health
1. Check container status:
   ```bash
   docker compose ps
   ```
2. Test the health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```
   *Expected Response:* `{"request_id":"...","status":"ok"}`

### Step 5: View Logs & Stop Service
- **View live logs**:
  ```bash
  docker compose logs -f jarvis
  ```
- **Stop containers**:
  ```bash
  docker compose down
  ```

---

## 🐍 Option 2: Deploying & Running WITHOUT Docker (Native Python)

Running natively is ideal for local development, debugging, and environments without Docker support.

### Step 1: Install Python 3.11+
Verify Python 3.11 or higher is installed:
```bash
python3 --version
```

### Step 2: Set Up Virtual Environment
1. Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   ```
2. Activate the virtual environment:
   - **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```

### Step 3: Install Dependencies
Upgrade `pip` and install all required Python packages:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
1. Copy the example `.env` file:
   ```bash
   cp .env.example .env
   ```
2. Set your environment variables inside `.env`:
   ```env
   GROQ_API_KEY=gsk_your_actual_groq_api_key
   SECRET_KEY=your-secret-key-here
   FLASK_ENV=development
   ```

### Step 5: Run the Server

#### A. Development Mode (Built-in Flask Server)
```bash
python3 -m app.main
```
*Server will start on `http://0.0.0.0:8000` with hot-reloading if debug mode is enabled.*

#### B. Production Mode (Gunicorn - Linux / macOS)
```bash
gunicorn app.main:app --workers 2 --threads 4 --bind 0.0.0.0:8000
```

### Step 6: Verify Server Execution
Open your browser or terminal and test:
```bash
curl http://localhost:8000/health
```

---

## 📱 Connecting Android Client to Desktop Server

To connect your Android device or emulator to the local desktop server:

### Option A: Local Wi-Fi Network (Same Wi-Fi)
1. Find your desktop's local IP address (`ip a` or `ifconfig` or `ipconfig`). Example: `192.168.1.50`.
2. Set the base URL in your Android client (`android/local.properties`):
   ```properties
   JARVIS_BASE_URL=http://192.168.1.50:8000/api
   ```

### Option B: USB Debugging / ADB Port Forwarding (Emulator / Connected Phone)
Forward port `8000` from Android device to desktop:
```bash
adb reverse tcp:8000 tcp:8000
```
Then set in `android/local.properties`:
```properties
JARVIS_BASE_URL=http://localhost:8000/api
```

---

## 🛠️ Troubleshooting & Frequently Asked Questions

| Issue | Cause | Solution |
|-------|-------|----------|
| `Address already in use: 8000` | Another process is using port 8000 | Change `PORT` in `.env` or kill existing process (`lsof -i :8000 \| xargs kill -9`) |
| `GROQ_API_KEY missing` | API key not set in `.env` | Ensure `.env` exists in root and contains `GROQ_API_KEY=gsk_...` |
| `Permission denied: /app/.jarvis_data` | Docker volume permission issue | Delete Docker volume `docker volume rm and9_jarvis_data` and restart |
| `ModuleNotFoundError: No module named 'app'` | Running outside virtualenv or wrong directory | Run commands from repository root with `venv` activated (`python3 -m app.main`) |
