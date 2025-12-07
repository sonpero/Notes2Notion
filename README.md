# Notes2Notion

Take your handwritten notes and push them directly to Notion — effortlessly.

This project offers **two deployment modes**:
- **PWA Mode** (Recommended): Full-stack web application with **multi-user OAuth authentication**, mobile-friendly Progressive Web App interface, and BETA license key gating
- **CLI Mode**: Command-line script for quick local processing (single-user, development use)

---

## 🌐 PWA Mode (Web Application)

The PWA mode provides a complete web application with:
- 📱 **Mobile-first design** - Capture notes directly from your phone camera
- 🚀 **Backend API** - Flask server exposing the Notes2Notion functionality
- ⚛️ **Next.js Frontend** - Modern React-based PWA with offline support
- 🐳 **Docker deployment** - Easy setup with Docker Compose

### Prerequisites

- **[Docker](https://www.docker.com/)** and **Docker Compose**
- **Notion Account** - With an OAuth integration created:
  1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
  2. Click **"+ New integration"**
  3. Choose **"Public integration"** (not internal)
  4. Fill in integration details (name, logo, etc.)
  5. Under **"OAuth Domain & URIs"**, set:
     - **Redirect URIs**: `http://localhost:3000/api/auth/callback` (for local dev)
     - For production: `https://your-domain.com/api/auth/callback`
  6. Under **"Capabilities"**, select:
     - ✅ Read content
     - ✅ Insert content
     - ✅ Update content
  7. Copy the **Client ID** and **Client Secret** (you'll need these for your `.env` file)
  8. **Note**: Users will grant page access during the OAuth flow — no manual page sharing needed!
- **OpenAI Account** - With an active API key ([Get one here](https://platform.openai.com/api-keys))

### Installation

1. **Pull the MCP Notion Docker image**:
   ```bash
   docker pull mcp/notion
   ```

2. **Configure environment variables**:

   Create a `.env` file at the root of the project. You can reference [.env.example](.env.example) for a complete template.

   **Required variables**:
   ```env
   # Notion OAuth Configuration
   NOTION_CLIENT_ID=your-notion-client-id-here
   NOTION_CLIENT_SECRET=your-notion-client-secret-here
   NOTION_REDIRECT_URI=http://localhost:3000/api/auth/callback

   # Frontend URL (used for OAuth redirects)
   FRONTEND_URL=http://localhost:3000

   # JWT Secret for session tokens
   # Generate with: openssl rand -hex 32
   JWT_SECRET=your-random-jwt-secret-here

   # OpenAI Configuration (required)
   OPENAI_API_KEY=your-openai-api-key

   # Database Configuration (MySQL)
   DATABASE_URL=mysql+pymysql://notes2notion:notes2notion@mysql:3306/notes2notion?charset=utf8mb4

   # MySQL Service Configuration (for docker-compose)
   MYSQL_ROOT_PASSWORD=rootpassword
   MYSQL_DATABASE=notes2notion
   MYSQL_USER=notes2notion
   MYSQL_PASSWORD=notes2notion

   # Application Environment
   # Options: development, production
   # - development: allows test mode toggle
   # - production: optimized for production use
   APP_ENV=production

   # API Host Configuration
   # For desktop-only: localhost
   # For mobile access: Your local IP (e.g., 192.168.1.74)
   # For production: Your server IP or domain
   API_HOST=localhost
   ```

3. **Database initialization**:

   The MySQL database and schema will be automatically created when you first start the application via Docker Compose. Alembic migrations run automatically on backend startup to ensure the database schema is up to date.

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

#### First-Time Setup (3-Step Onboarding)

**Step 1: Enter Your BETA License Key** (MANDATORY)

1. **Access the application**:
   - **On desktop**: Open http://localhost:3000 in your browser
   - **On mobile**: Open http://YOUR_LOCAL_IP:3000 in your mobile browser
     - Replace `YOUR_LOCAL_IP` with the IP address you configured in your `.env` file
     - Make sure your phone is on the same WiFi network as your computer

2. **Enter your license key**:
   - You'll see a prompt asking for your BETA license key
   - Enter the key provided by your administrator (format: `BETA-XXXX-XXXX-XXXX`)
   - The key will be validated and stored in your browser
   - **Note**: This license key is required for all users during the beta testing phase

**Step 2: Authenticate with Notion**

3. **Click "Sign in with Notion"**:
   - You'll be redirected to Notion's OAuth authorization page
   - Log in to your Notion account if prompted

4. **Grant access**:
   - Select your Notion workspace
   - Choose at least one page to share with the integration
   - Click "Select pages" to authorize the app
   - You'll be redirected back to Notes2Notion

**Step 3: Select Your Default Page**

5. **Choose where to create notes**:
   - You'll see a hierarchical list of all pages you've shared with the integration
   - Use the search bar to filter pages if needed
   - Select the page where you want your notes to be created by default
   - Click "Confirm" to save your selection

6. **You're all set!** Your authentication and preferences are now saved.

#### Using the App

7. **Capture or upload a photo** of your handwritten notes:
   - On mobile, you can directly capture a photo using your camera
   - On desktop, you can upload an existing image file

8. **Choose processing mode** (development environment only):
   - **Test Mode**: Uses mock components (no LLM API calls, $0 cost)
   - **Production Mode**: Uses real AI models to extract and process your notes

9. **Upload and process**: The app will:
   - Extract text from your handwritten notes using OpenAI GPT-4o-mini
   - Structure and enhance the content
   - Create a new page in your selected Notion workspace

#### Returning Users

- **Automatic login**: If your session is still valid (7 days), you'll be logged in automatically
- **Re-authentication**: If your session expires, you'll need to sign in with Notion again (your license key is already saved)

#### Install as PWA (Optional)

- **On iOS Safari**: Tap the Share button → "Add to Home Screen"
- **On Android Chrome**: Tap the menu → "Install app" or "Add to Home Screen"
- This gives you a native-like app experience with offline support

### 🗄️ Database Management

Notes2Notion uses **MySQL** to persist user data, OAuth credentials, and license keys.

#### MySQL Configuration

- **Docker Compose** includes a MySQL service that's automatically configured
- **Database creation**: Happens automatically on first startup
- **Character set**: UTF8MB4 for full Unicode and emoji support
- **Connection string format**: `mysql+pymysql://user:password@host:port/database?charset=utf8mb4`

#### Alembic Migrations

Database schema management is handled by [Alembic](https://alembic.sqlalchemy.org/):

- **Automatic migrations**: Run on backend startup
- **Migration files**: Located in `backend/alembic/versions/`
- **Configuration**: See `backend/alembic.ini` for advanced settings

**Current schema**:
- `users` table: Stores Notion OAuth tokens, workspace info, and default page IDs
- `license_keys` table: Manages BETA license keys and their activation status

#### Database Schema

**User**:
- `bot_id` - Unique Notion bot identifier (primary identifier)
- `workspace_id`, `workspace_name` - Notion workspace details
- `access_token`, `refresh_token` - OAuth credentials
- `notion_page_id` - User's selected default page for notes
- `created_at`, `updated_at` - Timestamps

**LicenseKey**:
- `key` - License key in format BETA-XXXX-XXXX-XXXX
- `is_active` - Whether the license is currently valid
- `used_by_user_id` - Which user activated this license
- `created_at`, `activated_at`, `revoked_at` - Lifecycle timestamps

---

### 👨‍💼 Administrator Guide

As an administrator deploying Notes2Notion for beta users, you'll need to manage license keys.

#### Creating License Keys

Use the **`admin_tools/license_manager.py`** CLI tool:

```bash
cd admin_tools

# Install dependencies
pip install -r requirements.txt

# Generate a single license key
python license_manager.py generate

# Generate multiple keys
python license_manager.py generate --count 10 --notes "Batch #1 for beta testers"

# Save keys to a file
python license_manager.py generate --count 50 --output keys.txt
```

#### Managing Licenses

```bash
# List all licenses
python license_manager.py list

# List only active licenses
python license_manager.py list --active-only

# Check a specific license
python license_manager.py check BETA-ABCD-1234-EFGH

# Revoke a license
python license_manager.py revoke BETA-ABCD-1234-EFGH

# View statistics
python license_manager.py stats
```

#### License Key Format

- Format: `BETA-XXXX-XXXX-XXXX`
- Cryptographically secure random generation
- Case-insensitive (auto-converted to uppercase)
- Excludes confusing characters (0, O, I, 1)

#### Distribution

- Share keys securely with beta users via encrypted channels
- Each key can only be activated by one user
- Users must enter the key before authenticating with Notion

For detailed information, see [admin_tools/README.md](admin_tools/README.md).

---

### 🔒 Security: OAuth + License Key System

Notes2Notion implements a multi-layered security approach for production deployments.

#### BETA License Key System (MANDATORY)

**Access Control**:
- ✅ **Required for all users** during beta testing phase
- ✅ One license per user (cannot be shared across workspaces)
- ✅ Can be revoked by administrators if needed
- ✅ Validates before OAuth flow begins

**How it works**:
1. User enters license key on first visit
2. Backend validates key is active and unused (or used by same user)
3. Key stored in browser localStorage
4. All API requests include key for validation

#### OAuth 2.0 Authentication

**Multi-User Isolation**:
- ✅ Each user has separate Notion workspace credentials
- ✅ OAuth tokens stored securely in MySQL database
- ✅ Per-user default page selection
- ✅ No credential sharing between users

**OAuth Flow**:
1. User clicks "Sign in with Notion"
2. Redirected to Notion's authorization page
3. User grants access to specific pages
4. Backend exchanges authorization code for access + refresh tokens
5. Tokens stored in database, linked to user's bot_id

**Token Management**:
- **Access tokens**: Short-lived, used for Notion API calls
- **Refresh tokens**: Long-lived, used to obtain new access tokens
- **Automatic refresh**: Backend refreshes expired tokens transparently

#### JWT Session Management

**Session Tokens**:
- ✅ **7-day expiration** for user convenience
- ✅ **HMAC-SHA256 signatures** for integrity
- ✅ Stored in browser localStorage
- ✅ Validated on every API request

**How it works**:
- Backend creates JWT after successful OAuth
- Token contains only bot_id (minimal sensitive data)
- Frontend includes token in `Authorization: Bearer <token>` header
- Backend verifies signature and expiration before processing requests

#### Security Benefits

| Feature | Old System (ACCESS_CODE) | New System (OAuth + License) |
|---------|-------------------------|------------------------------|
| Authentication | Shared secret | OAuth 2.0 standard |
| User isolation | None | Per-user credentials |
| Token expiration | Never | 7 days (JWT) |
| Token refresh | Manual | Automatic |
| Credential storage | Environment variables | Encrypted database |
| Revocation | Reset code for all | Per-user license revocation |
| Multi-user | Not supported | Full support |

#### Production Deployment Best Practices

1. **Generate a strong JWT secret**:
   ```bash
   openssl rand -hex 32
   ```

2. **Use HTTPS** for production deployments to protect tokens in transit

3. **Secure your database**: Use strong MySQL passwords and restrict network access

4. **Monitor license usage**: Regularly check which keys are activated

5. **Revoke compromised keys**: Use `license_manager.py revoke` if a key is leaked

---

### 🧪 End-to-End Testing

Notes2Notion has been validated with comprehensive end-to-end tests covering all critical user workflows.

#### Validated Test Scenarios

1. **✅ Complete Onboarding**
   - Valid license key entry
   - Full OAuth flow with Notion
   - Page selection from shared pages

2. **✅ User Logout & Reconnection**
   - User logs out and logs back in
   - Same license key and workspace
   - No duplicate user records created

3. **✅ Expired Token Handling**
   - Notion access token expires
   - Automatic token refresh using refresh_token
   - Seamless continuation of service

4. **✅ Revoked Integration**
   - User revokes Notion integration access
   - App detects revocation and prompts re-authentication
   - Database updated with new tokens after re-auth

5. **✅ Deleted Default Page**
   - User deletes their default Notion page
   - App detects deletion and redirects to page selection
   - User selects new default page

6. **✅ Invalid License Key**
   - User enters invalid/non-existent license
   - Clear error message displayed
   - Access denied until valid key provided

7. **✅ Duplicate License Usage**
   - Second user attempts to use already-activated license
   - Authentication fails with appropriate error
   - License remains tied to original user  
   

---

## 🖥️ CLI Mode (Local Script)

> **Note**: CLI mode is available for single-user/development scenarios using internal Notion integrations. For production multi-user deployments, use the **PWA mode with OAuth** (documented above). CLI mode does not support the OAuth authentication system or license keys.

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
- 🤖 **OpenAI API** - GPT-4o-mini for vision/text extraction AND text enhancement
- 🔗 **LangChain & LangGraph** - AI workflow orchestration
- 🧱 **Notion MCP Server** - Model Context Protocol integration
- 🗄️ **SQLAlchemy** - ORM for database models
- 🔄 **Alembic** - Database migration management
- 🔐 **PyJWT** - JWT session token generation and validation
- 🐬 **PyMySQL** - MySQL database driver
- 🐳 **Docker** - Containerization

### Database
- 🗄️ **MySQL** - User data and license key persistence
- 🔤 **UTF8MB4** - Full Unicode and emoji support
- 🔐 **Encrypted storage** - Secure OAuth token storage

### Frontend
- ⚛️ **Next.js 14** - React framework with SSR
- 🎨 **Tailwind CSS** - Utility-first styling
- 📱 **PWA** - Progressive Web App with offline support
- 🔷 **TypeScript** - Type-safe development
- 🔐 **OAuth 2.0** - Notion authentication flow

### DevOps
- 🐳 **Docker Compose** - Multi-container orchestration (backend + frontend + MySQL)
- 🧪 **Pytest** - Python testing
- 🔧 **Makefile** - Task automation

### Architecture
- 🌐 **Multi-user architecture** - Per-user Notion credentials and workspace isolation
- 🔐 **OAuth 2.0 authentication** - Industry-standard authorization flow
- 🎫 **JWT session management** - Secure, stateless session tokens (7-day expiration)
- 🔑 **License key gating** - BETA access control system  