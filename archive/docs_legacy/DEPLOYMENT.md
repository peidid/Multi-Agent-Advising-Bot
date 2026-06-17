# Deployment Guide: MongoDB Atlas + Railway

This guide explains how to deploy the Multi-Agent Academic Advising System with:
- **MongoDB Atlas** for user data storage
- **Railway** for hosting both backend and frontend

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Railway                                  │
│                                                                  │
│  ┌──────────────────────┐       ┌──────────────────────┐       │
│  │   Frontend Service   │──────▶│   Backend Service    │       │
│  │     (Next.js)        │       │  (FastAPI + Agents)  │       │
│  │                      │       │                      │       │
│  │  advising-frontend   │       │  advising-backend    │       │
│  └──────────────────────┘       └──────────────────────┘       │
│                                          │                       │
└──────────────────────────────────────────│───────────────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │     MongoDB Atlas       │
                              │  (Free Tier Available)  │
                              │                         │
                              │  Collections:           │
                              │  - users                │
                              │  - conversations        │
                              │  - messages             │
                              └─────────────────────────┘
```

## Step 1: Set Up MongoDB Atlas

**You've already completed this step!** Your connection string is:
```
mongodb+srv://advisingbot:<password>@cluster0.is7ns4r.mongodb.net/?appName=Cluster0
```

### 1.1 Create Account & Cluster (DONE)

1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a free account
3. Create a **Free Tier (M0)** cluster
   - Choose a cloud provider (AWS/GCP/Azure)
   - Select a region close to your users

### 1.2 Configure Database Access (DONE)

1. Go to **Database Access** → **Add New Database User**
2. Create a user with password
3. Note the username and password

### 1.3 Configure Network Access

1. Go to **Network Access** → **Add IP Address**
2. Click **"Allow Access from Anywhere"** (for Railway)
   - Or add `0.0.0.0/0`

### 1.4 Get Connection String (DONE)

1. Go to **Database** → **Connect**
2. Choose **"Drivers"** → Select **Python**
3. Copy the connection string:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?appName=Cluster0
   ```
4. Replace `<username>` and `<password>` with your credentials
5. **URL-encode special characters in password** (e.g., `!` → `%21`)

## Step 2: Test Locally First (Recommended)

Before deploying, test everything works locally.

### 2.1 Test Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Make sure .env is configured with your MongoDB URI and OpenAI key
# Run the server
uvicorn server:app --reload --port 8000
```

Open http://localhost:8000/api/health - you should see:
```json
{"status": "healthy", "database": "connected"}
```

### 2.2 Test Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:3000 - you should see the chat UI.

### 2.3 Test the Full Flow

1. Register an account
2. Send a test message like "Can I add a CS minor?"
3. Verify you get a response from the agents

## Step 3: Deploy to Railway

### 3.1 Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### 3.2 Create Railway Project

```bash
# In your project root
railway init
```

### 3.3 Deploy Backend

```bash
cd backend

# Create backend service
railway add

# Set environment variables
railway variables set MONGODB_URI="mongodb+srv://..."
railway variables set MONGODB_DATABASE="advising_bot"
railway variables set OPENAI_API_KEY="sk-..."
railway variables set JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
railway variables set ALLOWED_ORIGINS="https://your-frontend.railway.app"

# Deploy
railway up
```

Note the backend URL (e.g., `https://advising-backend-xxx.railway.app`)

### 3.4 Deploy Frontend

```bash
cd frontend

# Create frontend service
railway add

# Set environment variables
railway variables set NEXT_PUBLIC_API_URL="https://advising-backend-xxx.railway.app"

# Deploy
railway up
```

### 3.5 Alternative: Railway Dashboard (Easier)

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Create new project
3. **Add Backend Service:**
   - Click "New" → "GitHub Repo"
   - Select your repo
   - Set root directory to `/backend`
   - Add environment variables
4. **Add Frontend Service:**
   - Click "New" → "GitHub Repo"
   - Select your repo
   - Set root directory to `/frontend`
   - Add environment variables

## Step 4: Environment Variables Reference

### Backend (`/backend`)

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | Yes | MongoDB Atlas connection string |
| `MONGODB_DATABASE` | Yes | Database name (e.g., `advising_bot`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `JWT_SECRET_KEY` | Yes | Secret for JWT tokens |
| `ALLOWED_ORIGINS` | Yes | Frontend URL for CORS |
| `PORT` | No | Railway sets automatically |

### Frontend (`/frontend`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend service URL |

## Step 5: Verify Deployment

### Check Backend Health

```bash
curl https://your-backend.railway.app/api/health
```

Expected response:
```json
{"status": "healthy", "database": "connected"}
```

### Test Frontend

1. Open your frontend URL
2. Try creating an account
3. Send a test message

## Local Development

### Run Backend Locally

```bash
cd backend

# Create virtual environment (optional if using conda)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure .env
cp .env.example .env
# Edit .env with your credentials (MongoDB URI, OpenAI key, etc.)

# Run (from backend folder)
uvicorn server:app --reload --port 8000
```

**Note:** If your MongoDB password contains special characters like `!`, URL-encode them:
- `!` becomes `%21`
- `@` becomes `%40`
- `#` becomes `%23`

### Run Frontend Locally

```bash
cd frontend

# Install dependencies
npm install

# Copy and configure .env
cp .env.example .env.local

# Run
npm run dev
```

## MongoDB Collections

The system automatically creates these collections:

### `users`
```javascript
{
  _id: ObjectId,
  email: "student@cmu.edu",
  name: "Student Name",
  password_hash: "...",
  created_at: Date,
  profile: {
    major: "Information Systems",
    minors: ["Computer Science"],
    gpa: 3.5,
    completed_courses: ["15-112", "15-122"],
    interests: ["Data Science"]
  }
}
```

### `conversations`
```javascript
{
  _id: ObjectId,
  user_id: "user_id",
  title: "Can I add a CS minor?",
  created_at: Date,
  updated_at: Date,
  message_count: 4
}
```

### `messages`
```javascript
{
  _id: ObjectId,
  conversation_id: "conv_id",
  role: "user" | "assistant",
  content: "Your question here...",
  timestamp: Date,
  metadata: {
    agents_used: ["programs_requirements", "policy_compliance"]
  }
}
```

## Troubleshooting

### "MongoDB connection failed"
- Check your `MONGODB_URI` is correct
- Verify network access allows `0.0.0.0/0`
- Check database user password

### "CORS error"
- Verify `ALLOWED_ORIGINS` includes your frontend URL
- Make sure there's no trailing slash

### "Agent timeout"
- OpenAI API may be slow
- Check your API key is valid
- Consider increasing timeout in server.py

### "Frontend can't reach backend"
- Check `NEXT_PUBLIC_API_URL` is set correctly
- Make sure backend is running and healthy
- Check Railway logs for errors

## Costs

### MongoDB Atlas
- **Free Tier (M0)**: 512MB storage, perfect for demos
- Paid tiers start at ~$9/month for 2GB

### Railway
- **Hobby Plan**: $5/month includes $5 of usage
- Typical cost for this project: ~$10-20/month

### OpenAI
- Depends on usage
- GPT-4: ~$0.03-0.06 per 1K tokens
- Estimate: ~$5-20/month for moderate usage

## Next Steps

1. Set up a custom domain on Railway
2. Add rate limiting for production
3. Implement proper logging and monitoring
4. Add analytics for conversation insights
