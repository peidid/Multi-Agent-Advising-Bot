# Deployment Guide
## Multi-Agent Academic Advising System

This guide covers deploying the system to **Railway** (backend) and **Vercel** (frontend).

---

## Live URLs

| Service | URL |
|---------|-----|
| **Frontend** | https://multi-agent-advising-bot.vercel.app |
| **Backend API** | https://web-production-e056a3.up.railway.app |
| API Health | https://web-production-e056a3.up.railway.app/api/health |
| API Docs | https://web-production-e056a3.up.railway.app/docs |

---

## Part 1: Backend Deployment (Railway)

### Step 1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with **GitHub** (recommended)
3. Authorize Railway to access your repositories

### Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository (e.g., `AdvisingBot`)
4. Railway will auto-detect the Dockerfile

### Step 3: Add MongoDB Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add MongoDB"**
3. Wait for MongoDB to deploy
4. Click on MongoDB service → **"Variables"** tab
5. Copy the `MONGO_URL` value

### Step 4: Configure Backend Environment Variables

1. Click on your **backend service** (not MongoDB)
2. Go to **"Variables"** tab
3. Add these variables:

| Variable | Value |
|----------|-------|
| `MONGODB_URI` | Paste the `MONGO_URL` from Step 3 |
| `OPENAI_API_KEY` | Your OpenAI API key (sk-proj-...) |
| `JWT_SECRET_KEY` | Any random secure string (e.g., `my-jwt-secret-key-12345`) |
| `ALLOWED_ORIGINS` | `*` (update to frontend URL after deploying frontend) |

**Note:** Do NOT add `PORT` - Railway sets this automatically.

### Step 5: Clear Any Start Command Override

1. Go to backend service → **"Settings"** tab
2. Scroll to **"Deploy"** section
3. If there's a **"Start Command"** field, **leave it empty**
4. The Dockerfile handles the start command

### Step 6: Deploy

Railway will automatically build and deploy when you push to GitHub:

```bash
git add .
git commit -m "Deploy to Railway"
git push origin main
```

### Step 7: Verify Deployment

1. Go to backend service → **"Settings"** → **"Networking"**
2. Click **"Generate Domain"** if no public URL exists
3. Visit your URL:
   - `https://your-app.up.railway.app/` → Should show API info
   - `https://your-app.up.railway.app/api/health` → Should show healthy status
   - `https://your-app.up.railway.app/docs` → Interactive API documentation

---

## Part 2: Frontend Deployment (Vercel)

### Step 1: Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Sign up with **GitHub**

### Step 2: Import Project

1. Click **"Add New"** → **"Project"**
2. Select your GitHub repository
3. Configure:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Next.js (auto-detected)

### Step 3: Add Environment Variable

Click **"Environment Variables"** and add:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_API_URL` | `https://web-production-e056a3.up.railway.app` |

Replace with your actual Railway backend URL.

### Step 4: Deploy

Click **"Deploy"** and wait for the build to complete.

### Step 5: Get Your Frontend URL

After deployment, Vercel will give you a URL like:
- `https://multi-agent-advising-bot.vercel.app`

---

## Part 3: Connect Frontend to Backend

### Update CORS Settings

1. Go to Railway → your backend service → **"Variables"**
2. Update `ALLOWED_ORIGINS` to your Vercel URL:
   ```
   https://multi-agent-advising-bot.vercel.app
   ```
3. Railway will automatically redeploy

---

## Part 4: Test the Full System

1. Open https://multi-agent-advising-bot.vercel.app
2. Click **"Sign Up"** to create an account
3. Enter email, name, and password
4. Start chatting with the advising bot

### Test Queries

| Query | Expected Behavior |
|-------|-------------------|
| "What CS courses are available?" | Courses Agent responds |
| "Tell me about the CS program" | Programs Agent responds |
| "Can I take 15-213 without prerequisites?" | Policy Agent responds |
| "Create a 4-year plan for me" | Multiple agents collaborate |

---

## Troubleshooting

### Backend won't start

**Check Railway logs:**
1. Go to backend service → **"Logs"** tab
2. Look for error messages

**Common fixes:**
- Verify all environment variables are set
- Make sure `MONGODB_URI` is correct
- Check that MongoDB service is running

### "CORS Error" in browser

**Fix:** Update `ALLOWED_ORIGINS` in Railway to include your frontend URL.

### "Failed to fetch" in frontend

**Possible causes:**
1. Backend URL is wrong in `NEXT_PUBLIC_API_URL`
2. Backend is not running
3. CORS not configured

### MongoDB connection fails

**For Railway MongoDB:**
- The code auto-detects Railway internal MongoDB and disables SSL
- Make sure you're using the `MONGO_URL` from Railway's MongoDB service

**For MongoDB Atlas:**
- Atlas may have SSL compatibility issues with Railway
- Recommend using Railway's built-in MongoDB instead

### Chat returns empty response

**Check:**
1. `OPENAI_API_KEY` is valid
2. Backend logs for API errors
3. OpenAI API has sufficient credits

---

## Environment Variables Summary

### Railway Backend Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | Yes | MongoDB connection string |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `JWT_SECRET_KEY` | Yes | Secret for JWT tokens |
| `ALLOWED_ORIGINS` | Yes | Frontend URL for CORS |

### Vercel Frontend Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Railway backend URL |

---

## Architecture (Deployed)

```
┌─────────────────────────────────────────────────────────────┐
│                        VERCEL                                │
│                   (Next.js Frontend)                         │
│        https://multi-agent-advising-bot.vercel.app           │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        RAILWAY                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               FastAPI Backend                          │  │
│  │      https://web-production-e056a3.up.railway.app      │  │
│  │                                                        │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │           Multi-Agent System (LangGraph)        │  │  │
│  │  │  Programs │ Courses │ Policy │ Planning Agents  │  │  │
│  │  │              ↓ Blackboard ↓                     │  │  │
│  │  │                Coordinator                      │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              │                               │
│  ┌───────────────────────────▼───────────────────────────┐  │
│  │              MongoDB (Railway Plugin)                  │  │
│  │           mongodb.railway.internal:27017               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │     OpenAI API      │
                   │    (GPT-4 Turbo)    │
                   └─────────────────────┘
```

---

## Quick Reference

**Backend API URL:**
```
https://web-production-e056a3.up.railway.app
```

**Endpoints:**
- `GET /` - API info
- `GET /api/health` - Health check
- `GET /docs` - Swagger documentation
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `POST /api/chat` - Send message to advising bot
- `GET /api/conversations` - Get user's conversations

---

## Updating the Deployment

When you make code changes:

1. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

2. Railway and Vercel will automatically rebuild and deploy
