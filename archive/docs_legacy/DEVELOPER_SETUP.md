# Developer Setup Guide
## Multi-Agent Academic Advising System

Complete guide to set up this project on a new PC from scratch.

---

## Prerequisites

### 1. Install Python 3.10+

**Windows:**
1. Download from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Verify: `python --version`

**Mac:**
```bash
brew install python@3.11
```

### 2. Install Node.js 18+

1. Download LTS from https://nodejs.org/
2. Run installer
3. Verify: `node --version` and `npm --version`

### 3. Install Git

**Windows:**
1. Download from https://git-scm.com/download/win
2. Use default settings

**Mac:**
```bash
xcode-select --install
```

---

## Step 1: Get the Project

### Option A: Clone from GitHub
```bash
git clone https://github.com/YOUR_USERNAME/AdvisingBot.git
cd AdvisingBot/Product\ 0110
```

### Option B: Copy from USB/Cloud
Copy the entire `Product 0110` folder to your new PC.

---

## Step 2: Install Python Dependencies

Open terminal in the project root folder:

```bash
cd "path/to/Product 0110"
pip install -r requirements.txt
```

If you encounter errors:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Step 4: Configure Environment Variables

### Backend Environment

Create or edit `backend/.env`:

```env
# Backend Environment Variables

# MongoDB Atlas Connection
# Replace with your MongoDB Atlas connection string
# Note: Special characters in password must be URL-encoded (! = %21)
MONGODB_URI=mongodb+srv://advisingbot:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tls=true&tlsAllowInvalidCertificates=true
MONGODB_DATABASE=advising_bot

# OpenAI API Key
# Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# JWT Secret for authentication (generate a random string for production)
JWT_SECRET_KEY=your-secret-key-change-in-production

# CORS - Frontend URLs allowed
ALLOWED_ORIGINS=http://localhost:3000

# Server port
PORT=8000

# Optional: OpenAI API Proxy (for users in China)
# OPENAI_API_BASE=https://your-proxy-url.com/v1
```

### Frontend Environment (Optional)

Create `frontend/.env.local` for production deployment:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 5: Network Configuration (China Users Only)

If you're in China, OpenAI API is blocked. You need either:

### Option A: VPN
Use a VPN that can access OpenAI before running the backend.

### Option B: Change DNS
1. Press `Win + R`, type `ncpa.cpl`, press Enter
2. Right-click network adapter → Properties
3. Select "Internet Protocol Version 4 (TCP/IPv4)" → Properties
4. Use these DNS servers:
   - Preferred: `8.8.8.8`
   - Alternate: `8.8.4.4`
5. Flush DNS: `ipconfig /flushdns`

### Option C: Use OpenAI Proxy
Add to `backend/.env`:
```env
OPENAI_API_BASE=https://your-working-proxy.com/v1
```

---

## Step 6: MongoDB Atlas Setup

If you need to create a new MongoDB cluster:

1. Go to https://cloud.mongodb.com
2. Sign up / Log in
3. Create a free cluster (M0)
4. Create database user:
   - Database Access → Add New User
   - Username: `advisingbot`
   - Password: (choose one, avoid special chars or URL-encode them)
5. Whitelist IP:
   - Network Access → Add IP Address
   - Click "Allow Access from Anywhere" (for development)
6. Get connection string:
   - Database → Connect → Drivers
   - Copy the connection string
   - Replace `<password>` with your actual password

---

## Step 7: Run the Project

### Terminal 1: Backend

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:database:Connected to MongoDB: advising_bot
INFO:     Application startup complete.
```

### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

Expected output:
```
▲ Next.js 14.1.0
- Local: http://localhost:3000
✓ Ready
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Step 8: Verify Everything Works

1. Open http://localhost:3000
2. Click "Sign Up" → Create an account
3. Send a test message: "What CS courses are available?"
4. You should get a response from the multi-agent system

---

## Project Structure

```
Product 0110/
├── backend/                 # FastAPI backend
│   ├── server.py           # Main server
│   ├── database.py         # MongoDB connection
│   └── .env                # Environment variables
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Pages
│   │   ├── components/    # React components
│   │   └── lib/           # API client
│   └── package.json
├── agents/                 # Multi-agent system
│   ├── base_agent.py
│   ├── programs_agent.py
│   ├── courses_agent.py
│   ├── policy_agent.py
│   └── planning_agent.py
├── coordinator/            # Agent coordinator
│   └── coordinator.py
├── blackboard/             # Shared state
│   └── schema.py
├── data/                   # RAG knowledge base
│   ├── programs/
│   ├── courses/
│   └── policies/
├── config.py               # Model configuration
├── multi_agent.py          # Workflow definition
└── rag_engine_improved.py  # RAG engine
```

---

## Common Issues

### "Failed to fetch" in frontend
- Backend not running or crashed
- Check backend terminal for errors

### "Database not connected"
- MongoDB URI incorrect
- Password special characters not URL-encoded
- IP not whitelisted in MongoDB Atlas

### "Request timed out" (OpenAI)
- VPN not connected (China)
- OpenAI API key invalid
- Network issues

### "No documents found for domain"
- RAG data paths incorrect
- Missing data files in `data/` folder

### npm errors
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again

---

## Development Tips

### Hot Reload
Both backend and frontend have hot reload enabled:
- Backend: `--reload` flag
- Frontend: Built into Next.js dev server

### View API Documentation
Open http://localhost:8000/docs for interactive Swagger UI

### Database Inspection
Use MongoDB Compass or Atlas web UI to view stored data:
- Users collection
- Conversations collection
- Messages collection

### Logs
- Backend logs appear in Terminal 1
- Frontend logs appear in browser console (F12)

---

## Quick Start Commands

```bash
# One-time setup
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Daily development
# Terminal 1:
cd backend && uvicorn server:app --reload --host 0.0.0.0 --port 8000

# Terminal 2:
cd frontend && npm run dev
```

---

## Contact & Resources

- Project: ACL 2026 Demo Track
- MongoDB Atlas: https://cloud.mongodb.com
- OpenAI API: https://platform.openai.com
- Railway (Deployment): https://railway.app
