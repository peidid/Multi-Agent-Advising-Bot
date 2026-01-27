# Complete Implementation Guide
## Multi-Agent Academic Advising System (ACL 2026 Demo)

This guide covers everything needed to run and deploy your system locally and on Railway.

---

## Prerequisites Checklist

Before starting, ensure you have:

- [x] **Python 3.10+** installed
- [x] **Node.js 18+** installed (verify: `node --version`)
- [x] **MongoDB Atlas** account with cluster created
- [x] **OpenAI API Key** configured
- [ ] **Railway account** (for deployment)

---

## Part 1: Local Development Setup

### Step 1: Install Python Dependencies

Open a terminal in the project root (`Product 0110`) and run:

```bash
pip install -r requirements_api.txt
```

If you encounter bcrypt issues, that's okay - we've switched to SHA256 hashing.

### Step 2: Verify Backend Environment

Your `backend/.env` file should already contain:

```env
MONGODB_URI=mongodb+srv://advisingbot:Dongpeidi12%21@cluster0.is7ns4r.mongodb.net/?appName=Cluster0
MONGODB_DATABASE=advising_bot
OPENAI_API_KEY=sk-proj-...your-key...
JWT_SECRET_KEY=acl2026-advising-bot-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000
PORT=8000
```

### Step 3: Start the Backend Server

Open **Terminal 1** and run:

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Verify Backend is Working

Open a browser and go to:
- **Health Check**: http://localhost:8000/api/health
  - Should show: `{"status":"healthy","database":"connected"}`
- **API Docs**: http://localhost:8000/docs
  - Interactive Swagger documentation

### Step 5: Start the Frontend Server

Open **Terminal 2** and run:

```bash
cd frontend
npm run dev
```

Expected output:
```
▲ Next.js 14.1.0
- Local:        http://localhost:3000
✓ Ready
```

### Step 6: Test the Full System

1. Open http://localhost:3000 in your browser
2. Click **"Sign Up"** to create an account
3. Enter email, name, and password
4. After registration, you'll be logged in automatically
5. Type a message to test the chat (e.g., "What CS courses should I take?")

---

## Part 2: Testing the Multi-Agent System

### Test Queries to Try

Once logged in, try these queries to verify all agents are working:

| Query | Expected Agents Used |
|-------|---------------------|
| "What CS electives are available?" | Courses Agent |
| "Tell me about the BS in CS program" | Programs Agent |
| "Can I take 15-213 without 15-122?" | Policy Agent |
| "Create a 4-year plan for CS major" | Planning Agent + Coordinator |
| "I want to double major in CS and Business" | All agents (complex query) |

### Verify Agent Responses

When the system responds:
- You should see which agents were used
- The response should be contextual and helpful
- Check the browser console (F12) for any errors

---

## Part 3: Profile Setup (Optional)

1. Click your profile icon (top right)
2. Fill in your academic profile:
   - **Major**: e.g., "Computer Science"
   - **GPA**: e.g., 3.5
   - **Completed Courses**: e.g., "15-112", "15-122"
   - **Interests**: e.g., "AI", "Systems"
3. Save your profile

The multi-agent system will use this information to personalize advice.

---

## Part 4: Railway Deployment

### Step 1: Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub (recommended)
3. Authorize Railway to access your repositories

### Step 2: Push Code to GitHub

If not already done:

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### Step 3: Create Backend Service

1. In Railway dashboard, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository
4. Railway will detect the Python app

**Configure Backend Environment Variables:**

In Railway dashboard, go to your service → **Variables** → Add:

| Variable | Value |
|----------|-------|
| `MONGODB_URI` | `mongodb+srv://advisingbot:Dongpeidi12%21@cluster0.is7ns4r.mongodb.net/?appName=Cluster0` |
| `MONGODB_DATABASE` | `advising_bot` |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `JWT_SECRET_KEY` | Generate a new secure key for production |
| `ALLOWED_ORIGINS` | Your frontend Railway URL (add after frontend is deployed) |
| `PORT` | `8000` |

**Configure Build Settings:**

- **Root Directory**: `backend`
- **Build Command**: `pip install -r ../requirements_api.txt`
- **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

### Step 4: Create Frontend Service

1. In Railway, click **"+ New"** → **"Service"**
2. Select same GitHub repo
3. Configure:

**Environment Variables:**

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your backend Railway URL (e.g., `https://backend-xxx.up.railway.app`) |

**Build Settings:**

- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`

### Step 5: Update CORS for Production

After both services are deployed:

1. Go to Backend service → Variables
2. Update `ALLOWED_ORIGINS` to include your frontend URL:
   ```
   http://localhost:3000,https://your-frontend-xxx.up.railway.app
   ```
3. Redeploy backend

### Step 6: Generate Public URLs

For each service in Railway:
1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Note down the URLs

---

## Part 5: Troubleshooting

### Common Issues and Solutions

#### "Failed to fetch" Error
- **Cause**: Backend is not running or crashed
- **Fix**: Check backend terminal for errors, restart with `uvicorn server:app --reload`

#### "Database not connected"
- **Cause**: MongoDB URI issue
- **Fix**: Verify the `!` is encoded as `%21` in your MongoDB URI

#### "CORS Error"
- **Cause**: Frontend URL not in ALLOWED_ORIGINS
- **Fix**: Add frontend URL to `ALLOWED_ORIGINS` in backend `.env`

#### "ModuleNotFoundError"
- **Cause**: Missing Python packages
- **Fix**: Run `pip install -r requirements_api.txt`

#### "npm not found"
- **Cause**: Node.js not installed
- **Fix**: Install from https://nodejs.org (LTS version)

#### Chat returns empty response
- **Cause**: OpenAI API key invalid or expired
- **Fix**: Verify your `OPENAI_API_KEY` in `backend/.env`

---

## Part 6: Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                              │
│                    http://localhost:3000                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │  AuthModal  │  │   Sidebar   │  │    ChatMessage/Input    │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                               │
│                    http://localhost:8000                          │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    API Endpoints                          │    │
│  │  /api/auth/*  │  /api/chat  │  /api/conversations/*      │    │
│  └──────────────────────────────────────────────────────────┘    │
│                             │                                     │
│  ┌──────────────────────────▼──────────────────────────────┐     │
│  │              MULTI-AGENT SYSTEM (LangGraph)              │     │
│  │  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐  │     │
│  │  │ Programs  │ │  Courses  │ │  Policy  │ │ Planning │  │     │
│  │  │   Agent   │ │   Agent   │ │  Agent   │ │  Agent   │  │     │
│  │  └─────┬─────┘ └─────┬─────┘ └────┬─────┘ └────┬─────┘  │     │
│  │        └─────────────┴────────────┴────────────┘        │     │
│  │                      │ Blackboard                       │     │
│  │                      ▼                                  │     │
│  │              ┌──────────────┐                           │     │
│  │              │  Coordinator │                           │     │
│  │              │     Agent    │                           │     │
│  │              └──────────────┘                           │     │
│  └─────────────────────────────────────────────────────────┘     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
┌─────────────────────────┐    ┌─────────────────────────────┐
│      MONGODB ATLAS      │    │         OPENAI API          │
│   (User Data, Chats)    │    │    (GPT-4 for Agents)       │
└─────────────────────────┘    └─────────────────────────────┘
```

---

## Quick Start Commands

```bash
# Terminal 1: Backend
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Then open http://localhost:3000

---

## Next Steps After Local Testing

1. ✅ Verify registration/login works
2. ✅ Verify chat responses use correct agents
3. ✅ Test with various academic queries
4. ⬜ Deploy to Railway (Part 4)
5. ⬜ Demo preparation for ACL 2026
