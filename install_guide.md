# 🛠️ ALT Kiosk Installation Guide (Raspberry Pi 5)

This guide covers the system preparation, backend setup, and frontend deployment for the Alcohol Testing Kiosk.

---

## 1. System Preparation
Update your system and install necessary core dependencies.

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python & Build Tools
sudo apt install -y python3 python3-pip python3-venv build-essential libusb-1.0-0-dev sqlite3

# Install Node.js (Version 20+)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"
# Download and install Node.js:
nvm install 22
# Verify the Node.js version:
node -v # Should print "v22.22.3".
# Verify npm version:
npm -v # Should print "10.9.8".
```

---

## 2. Backend Setup (Python FastAPI)
The backend manages hardware (alcohol sensor, fingerprint) and data synchronization.

### 2.1 Virtual Environment & Dependencies
```bash
cd Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.2 SecuGen Fingerprint SDK Setup
The fingerprint scanner requires library drivers to be installed.

```bash
# Install the libraries
cd FDx_SDK/lib/pi
sudo make install

# Build the fingerprint binary files
cd ../../sgfplibtest
make -f Makefile.fingerprint

# Create the bin folder and copy the compiled binaries
mkdir -p ../../bin
cp ../bin/pi/finger_scan ../../bin/
cp ../bin/pi/match_template ../../bin/

# Add your user to the SecuGen group
cd ../../
sudo groupadd SecuGen
sudo gpasswd -a $USER SecuGen

# Add USB Rules for hardware access
sudo nano /etc/udev/rules.d/99-piSecuGen.rules
```

**Paste these lines into the file:**
```text
ATTRS{idVendor}=="1162", ATTRS{idProduct}=="0320", SYMLINK+="input/fdu03-%k", MODE="0660", GROUP="SecuGen"
ATTRS{idVendor}=="1162", ATTRS{idProduct}=="0322", SYMLINK+="input/sdu03m-%k", MODE="0660", GROUP="SecuGen"
ATTRS{idVendor}=="1162", ATTRS{idProduct}=="0330", SYMLINK+="input/fdu04-%k", MODE="0660", GROUP="SecuGen"
ATTRS{idVendor}=="1162", ATTRS{idProduct}=="1000", SYMLINK+="input/sdu03p-%k", MODE="0660", GROUP="SecuGen"
ATTRS{idVendor}=="1162", ATTRS{idProduct}=="2000", SYMLINK+="input/sdu04p-%k", MODE="0660", GROUP="SecuGen"
ATTRS{idVendor}=="1162", ATTRS{idProduct}=="2200", SYMLINK+="input/sdu05-%k", MODE="0660", GROUP="SecuGen"
KERNEL=="uinput", MODE="0660", GROUP="SecuGen"
```
**Reboot the Pi** to apply hardware permissions: `sudo reboot`

### 2.3 Configuration
```bash
cd Backend
cp .env.example .env
nano .env
```

Configure the following key parameters in the `.env` file:

*   **CLOUD_API_URL**: The API URL of the cloud backend.
*   **CLOUD_API_TOKEN**: Bearer API token generated for the device to connect securely to the cloud.
*   **CLOUD_DEVICE_ID**: The unique identifier for this Kiosk device (e.g., `kiosk-001` or `ALT-001`).
*   **CONSOLE_LOG_LEVEL**: The logging level printed to the terminal console (`INFO`, `DEBUG`, or `ERROR`). Set to `INFO` for clean operation or `DEBUG` to diagnose hardware events.
*   **DB_PATH**: Local SQLite database path (defaults to `data/kiosk.db`).

---

## 3. Frontend Setup (React + Vite)
The frontend is the touch-screen user interface.

```bash
# From the project root
npm install

# Setup environment
cp .env.example .env
nano .env
```
*   **VITE_APP_MODE** = 'prod'
*   **VITE_WS_URL**: Set to `ws://localhost:8000/ws`

---

## 4. Running the Project

### Development Mode
**Terminal 1 (Backend):**
```bash
cd Backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```bash
npm run dev -- --host
```

---

## Database Management
To inspect the local data stored on the Pi:

```bash
# Open the database
sqlite3 Backend/data/kiosk.db

# Useful SQL Commands:
# .tables                                    - List all tables
# SELECT * FROM scan_logs LIMIT 10;           - View recent logs
# SELECT count(*) FROM employees;             - Check employee sync count
# .quit                                       - Exit
```

---

## Production Setup (Auto-Start)
Use **PM2** to keep the application running automatically.

```bash
sudo npm install -g pm2

# Start Backend
cd Backend
pm2 start "venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" --name alt-backend

# Start Frontend
cd ..
pm2 start "npm run dev -- --host" --name alt-frontend

# Save for reboot
pm2 save
pm2 startup
```
