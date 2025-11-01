# Notes2Notion

Take your handwritten notes and push them directly to Notion — effortlessly.

This project offers **two deployment modes**:
- **PWA Mode** (Recommended): Full-stack web application with a mobile-friendly Progressive Web App interface
- **CLI Mode**: Command-line script for quick local processing

---

## 🌐 PWA Mode (Web Application)

The PWA mode provides a complete web application with:
- 📱 **Mobile-first design** - Capture notes directly from your phone camera
- 🚀 **Backend API** - Flask server exposing the Notes2Notion functionality
- ⚛️ **Next.js Frontend** - Modern React-based PWA with offline support
- 🐳 **Docker deployment** - Easy setup with Docker Compose

### Prerequisites

- **[Docker](https://www.docker.com/)** and **Docker Compose**
- **Notion Account**  
- **OpenAI Account** - With an active API key ([Get one here](https://platform.openai.com/api-keys))

### Installation


1**Configure environment variables**:

   Create a `.env` file at the root of the project with:
   ```env

   # OpenAI Configuration (required for image text extraction)
   OPENAI_API_KEY=your_openai_api_key

   # Security - Access Code (REQUIRED for self-hosting)
   # Generate a strong random code with: openssl rand -hex 32
   ACCESS_CODE=your-secret-access-code-here

   # Application Environment
   # Options: development, production
   # - development: allow to toggle test mode of backend
   # - production: Optimized for production use
   APP_ENV=development

   # API Host Configuration
   # For desktop-only: localhost
   # For mobile access: Your local IP (e.g., 192.168.1.74)
   API_HOST=localhost
   ```

3. **Generate a secure access code**:

   When self-hosting on a VPS or public server, you **must** set an `ACCESS_CODE` to protect your API from unauthorized access and prevent others from making LLM calls at your expense.

   Generate a strong random code:
   ```bash
   # On Linux/macOS
   openssl rand -hex 32

   # On Windows (PowerShell)
   [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
   ```

   Add this code to your `.env` file as `ACCESS_CODE`. Users will need to enter this code when first accessing the application.

   > **Note**: If you're only running locally for personal use, you can skip this step. However, for any public deployment, this is **strongly recommended** to prevent unauthorized usage.

### Running with Docker Compose

#### Quick Start

**For desktop-only testing:**

Simply build and start the application (uses `localhost` by default):
```bash
docker compose up --build
```

The services will be available at:
- **Frontend (PWA)**: http://localhost:3000
- **Backend API**: http://localhost:5001

---

**For mobile access** (recommended for the full PWA experience):

You need to configure your local IP address so your phone can communicate with the backend API.

##### Step 1: Find your local IP address

- **macOS**:
  ```bash
  ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}'
  ```
  Or go to: System Settings → Network → Your active connection → Details → TCP/IP

- **Linux**:
  ```bash
  hostname -I | awk '{print $1}'
  ```

- **Windows**:
  ```cmd
  ipconfig
  ```
  Look for "IPv4 Address" under your active network adapter (WiFi or Ethernet)

Your local IP typically looks like `192.168.x.x` or `10.0.x.x`

##### Step 2: Update your `.env` file

Update the `API_HOST` variable in your `.env` file with your local IP address:

```env
API_HOST=192.168.1.74
```

Replace `192.168.1.74` with your actual local IP address.

##### Step 3: Build and start the application

```bash
docker compose up --build
```

The frontend will now be accessible from your phone at: http://YOUR_IP:3000

⚠️ **Important**: Your phone must be on the same WiFi network as your computer for mobile access to work!

The services will be available at:
- **Frontend (PWA)**: http://localhost:3000
- **Backend API**: http://localhost:5001

#### All Available Docker Compose Commands

```bash
# Build the containers
docker compose build

# Start the application (foreground)
docker compose up

# Start the application (background)
docker compose up -d

# Start with rebuild
docker compose up --build

# Stop the application
docker compose down

# Stop and remove volumes
docker compose down -v

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend

# Restart services
docker compose restart

# Check running containers
docker compose ps

# Execute a command in a running container
docker compose exec backend bash
docker compose exec frontend sh
```

### Using the PWA

1. **Access the application**:
   - **On desktop**: Open http://localhost:3000 in your browser
   - **On mobile**: Open http://YOUR_LOCAL_IP:3000 in your mobile browser
     - Replace `YOUR_LOCAL_IP` with the IP address you configured in your `.env` file
     - Make sure your phone is on the same WiFi network as your computer

2. **Enter your access code** (first visit only):
   - When you first access the application, you'll see an access code prompt
   - Enter the `ACCESS_CODE` you configured in your `.env` file
   - The code will be stored in your browser and you won't need to enter it again
   - Share this code securely with anyone who should have access to your instance

3. **Capture or upload a photo** of your handwritten notes:
   - On mobile, you can directly capture a photo using your camera
   - On desktop, you can upload an existing image file

4. **Choose processing mode**:
   - **Test Mode**: Uses mock components (no LLM API calls, $0 cost)
   - **Production Mode**: Uses real AI models to extract and process your notes

5. **Upload and process**: The app will:
   - Extract text from your handwritten notes
   - Structure and enhance the content
   - Create a new page in your Notion workspace

6. **Install as PWA** (mobile only, optional):
   - On iOS Safari: Tap the Share button → "Add to Home Screen"
   - On Android Chrome: Tap the menu → "Install app" or "Add to Home Screen"
   - This gives you a native-like app experience with offline support

### 🔒 Security & Access Control

When self-hosting Notes2Notion on a VPS or public server, it's **critical** to set up access control to prevent unauthorized users from discovering your application URL and making LLM API calls at your expense.

#### Access Code Protection

Notes2Notion includes a built-in access code mechanism:

- **How it works**: Users must enter a secret code when first accessing the application
- **Storage**: The code is stored in the browser's localStorage for convenience
- **API Protection**: Every API request includes the code in an `Authorization` header
- **Backend Validation**: The Flask backend validates the code before processing requests

#### Setting up access control

1. **Generate a strong access code** (see Installation step 3 above)
2. **Add it to your `.env` file**: `ACCESS_CODE=your-generated-code`
3. **Restart your containers**: `docker compose up -d --build`
4. **Share the code securely** with authorized users via a secure channel

#### Important notes

- ⚠️ **Anyone with the access code can use your service** - treat it like a password
- ⚠️ **No user management** - this is a simple shared secret, not multi-user auth
- ✅ **Future-proof** - Compatible with NextAuth migration (planned feature)
- ✅ **Optional for local use** - Skip if only running on localhost for personal use

#### Resetting the access code

If you need to reset the code (e.g., if it's been compromised):

1. Generate a new code: `openssl rand -hex 32`
2. Update your `.env` file with the new code
3. Restart containers: `docker compose restart`
4. All users will need to clear their browser storage and enter the new code

---

## 🖥️ CLI Mode (Local Script)

For quick local processing without the web interface.

### Prerequisites

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Python package and project manager
- **[Docker](https://www.docker.com/)** - For running the MCP Notion server
- Same Notion and OpenAI accounts as PWA mode

### Installation

1. **Pull the MCP Notion Docker image**:
   ```bash
   docker pull mcp/notion
   ```

2. **Create your virtual environment with uv**:
   ```bash
   uv init
   ```

3. **Install the dependencies**:
   ```bash
   uv pip install -r pyproject.toml
   ```

4. **Configure environment variables**:

   Create a `.env` file (same as PWA mode)

### Running the CLI

#### Test Mode (No LLM Calls)

Perfect for development and testing without incurring LLM costs:

```bash
PYTHONPATH=src uv run python src/Notes2Notion/main.py --test-mode
```

**What happens in test mode:**
- ✅ Detects images in `notes_pictures/`
- ✅ Generates structured mock content (no GPT-4o-mini calls)
- ✅ Simulates the enhancement workflow (no OpenAI calls)
- ✅ **Actually uploads to Notion** (tests the real Notion integration)
- 💰 **Cost: $0** (zero LLM API calls)

#### Production Mode

1. **Add your handwritten notes images**:
   - Place your photos in the `src/Notes2Notion/notes_pictures/` directory
   - Supported formats: PNG, JPG, JPEG

2. **Run the application**:
   ```bash
   PYTHONPATH=src uv run python src/Notes2Notion/main.py
   ```

The application will:
- Extract text from all images in the `notes_pictures` folder
- Structure and enhance the content using AI
- Create a new Notion page with the formatted notes

---

## 🧪 Running Tests

Run the unit tests with (from root of project):
```bash
PYTHONPATH=src uv run pytest -v
```

## 🧰 Tech Stack

### Backend
- 🐍 **Python 3.12+**
- 🌐 **Flask** - REST API server
- 🤖 **OpenAI API** - GPT-4o-mini for vision/text extraction
- 🔗 **LangChain & LangGraph** - AI workflow orchestration
- 🧱 **Notion MCP Server** - Model Context Protocol integration
- 🐳 **Docker** - Containerization

### Frontend
- ⚛️ **Next.js 14** - React framework with SSR
- 🎨 **Tailwind CSS** - Utility-first styling
- 📱 **PWA** - Progressive Web App with offline support
- 🔷 **TypeScript** - Type-safe development

### DevOps
- 🐳 **Docker Compose** - Multi-container orchestration
- 🧪 **Pytest** - Python testing
- 🔧 **Makefile** - Task automation  