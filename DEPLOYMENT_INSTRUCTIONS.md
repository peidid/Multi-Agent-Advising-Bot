# Deployment Instructions - Share Your Multi-Agent Advising System

## 🚀 Quick Deploy to Streamlit Cloud (FREE)

The easiest way to share with others - they just click a link!

---

## Prerequisites

- GitHub account (free)
- OpenAI API key
- This project code

---

## Step 1: Prepare Your Repository

### 1.1 Create requirements.txt

First, let's ensure all dependencies are listed:

```bash
cd "e:\CMU\Research\AdvisingBot\Product 0110"
```

Create/verify `requirements_streamlit.txt`:

```txt
streamlit>=1.28.0
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.10
chromadb>=0.4.18
pydantic>=2.0.0
python-dotenv>=1.0.0
urllib3>=2.0.0
openai>=1.0.0
langgraph>=0.0.20
```

### 1.2 Create .gitignore

Create `.gitignore` to avoid committing secrets:

```gitignore
# Secrets
.env
.streamlit/secrets.toml

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/

# ChromaDB
chroma_db_*/
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Temporary files
*.tmp
*.log
```

---

## Step 2: Push to GitHub

### 2.1 Initialize Git (if not already done)

```bash
cd "e:\CMU\Research\AdvisingBot\Product 0110"
git init
git add .
git commit -m "Initial commit: Multi-agent academic advising system"
```

### 2.2 Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `cmu-advising-bot` (or your choice)
3. Description: "Multi-Agent Academic Advising System - ACL 2026"
4. Choose: Public (for easy sharing) or Private
5. Click "Create repository"

### 2.3 Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/cmu-advising-bot.git
git branch -M main
git push -u origin main
```

**⚠️ IMPORTANT:** Make sure `.env` and `secrets.toml` are NOT committed!

---

## Step 3: Deploy on Streamlit Cloud

### 3.1 Go to Streamlit Cloud

Visit: https://share.streamlit.io/

### 3.2 Sign In

Click "Sign in" → "Continue with GitHub"

### 3.3 Deploy New App

1. Click "New app" button
2. Fill in:
   - **Repository:** `YOUR_USERNAME/cmu-advising-bot`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app_agent_view.py`
3. Click "Advanced settings"

### 3.4 Add Secrets

In the "Secrets" section, paste:

```toml
OPENAI_API_KEY = "sk-your-actual-openai-api-key-here"
```

**⚠️ Use your real OpenAI API key!**

### 3.5 Deploy!

Click "Deploy!" button

Wait 2-5 minutes for deployment...

---

## Step 4: Share Your Link

Once deployed, you'll get a URL like:

```
https://cmu-advising-bot.streamlit.app
```

**Share this link with:**
- ✅ Academic advisors
- ✅ Students
- ✅ Research collaborators
- ✅ ACL 2026 reviewers
- ✅ Anyone in the world!

---

## Managing Your Deployed App

### Update the App

When you make changes:

```bash
git add .
git commit -m "Description of changes"
git push
```

Streamlit Cloud will **automatically rebuild** (takes ~2-3 minutes)

### View Logs

1. Go to https://share.streamlit.io/
2. Click your app
3. Click "Manage app" → "Logs"

### Monitor Usage

Dashboard shows:
- Total views
- Active users
- Error logs
- Resource usage

### Pause/Delete App

In "Manage app" settings:
- Pause: Temporarily disable
- Delete: Permanently remove

---

## Alternative: Local Deployment

If you want to share locally (e.g., demo on your laptop):

### 1. Set up environment

```bash
cd "e:\CMU\Research\AdvisingBot\Product 0110"

# Create .env file
echo OPENAI_API_KEY=sk-your-key-here > .env
```

### 2. Install dependencies

```bash
pip install -r requirements_streamlit.txt
```

### 3. Run locally

```bash
streamlit run streamlit_app_agent_view.py
```

Opens at: `http://localhost:8501`

### 4. Share on local network

```bash
streamlit run streamlit_app_agent_view.py --server.address 0.0.0.0
```

Others on same WiFi can access via: `http://YOUR_IP:8501`

Find your IP:
- Windows: `ipconfig`
- Mac/Linux: `ifconfig`

---

## Security Best Practices

### 1. Never Commit API Keys

✅ Good:
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
```

❌ Bad:
```python
api_key = "sk-abc123..."  # NEVER DO THIS
```

### 2. Set Usage Limits

In OpenAI dashboard:
1. Go to "Settings" → "Limits"
2. Set monthly budget (e.g., $10)
3. Enable email alerts

### 3. Monitor Usage

Check regularly:
- Streamlit Cloud: App dashboard
- OpenAI: Usage page

### 4. Use Read-Only Keys (if available)

For demos, create restricted API keys with minimal permissions

---

## Cost Estimation

### Streamlit Cloud Hosting

**FREE** tier includes:
- 1 app
- Unlimited viewers
- Reasonable bandwidth

**Paid** ($20/month) if you need:
- Multiple apps
- Private apps
- Custom domains

### OpenAI API Costs

**GPT-4o** (current model):
- ~$0.005 per query (typical)
- 100 queries = ~$0.50
- 1000 queries = ~$5

**Tips to reduce costs:**
- Use GPT-4o-mini (~60% cheaper)
- Set usage limits
- Cache frequent queries

**Expected costs:**
- Demo/testing: $0-5/month
- Light usage (100 users): $10-30/month
- Heavy usage (1000+ users): $50-150/month

---

## Troubleshooting

### App Won't Start

**Check:**
1. `requirements_streamlit.txt` is complete
2. No syntax errors in code
3. Secrets are properly formatted
4. API key is valid

**View logs:**
Streamlit Cloud → Your app → "Logs"

### App is Slow

**Optimize:**
```python
# Add caching
@st.cache_data
def load_knowledge_base():
    # ...

@st.cache_resource
def get_llm():
    # ...
```

### API Errors

**Check:**
1. API key is correct in secrets
2. OpenAI account has billing enabled
3. API rate limits not exceeded

---

## Sharing with ACL 2026 Reviewers

### In Your Paper

```markdown
A live demonstration is available at:
https://cmu-advising-bot.streamlit.app

The interface visualizes real-time multi-agent collaboration,
showing dynamic coordination, negotiation, and emergent behavior.
```

### Access Instructions

```
Demo URL: https://cmu-advising-bot.streamlit.app

Instructions:
1. Set student profile (optional) in left sidebar
2. Enter academic advising question
3. Click "🚀 Process"
4. Watch all 5 agents collaborate in real-time
5. See final answer and workflow timeline

Example queries:
- "What are the CS major requirements?"
- "Can I add a Business minor?"
- "Plan my courses until graduation"
```

### Demo Video (Optional)

Consider recording a 2-3 minute screencast showing:
1. Setting student profile
2. Submitting query
3. Watching agents activate
4. Final answer appearing

Upload to: YouTube, Google Drive, or Vimeo

---

## Updating After Deployment

### Change API Key

Streamlit Cloud → Your app → "Settings" → "Secrets" → Update

### Change Code

```bash
# Make changes locally
# Test locally first:
streamlit run streamlit_app_agent_view.py

# If working, push:
git add .
git commit -m "Update: ..."
git push
```

Auto-deploys in 2-3 minutes!

---

## Support

### Streamlit Issues

- Docs: https://docs.streamlit.io/
- Forum: https://discuss.streamlit.io/
- GitHub: https://github.com/streamlit/streamlit/issues

### OpenAI Issues

- Docs: https://platform.openai.com/docs
- Support: https://help.openai.com/

---

## Quick Reference

| Task | Command |
|------|---------|
| Run locally | `streamlit run streamlit_app_agent_view.py` |
| Push updates | `git add . && git commit -m "msg" && git push` |
| View logs | Streamlit Cloud → App → Logs |
| Update secrets | Streamlit Cloud → App → Settings → Secrets |
| Pause app | Streamlit Cloud → App → Settings → Pause |

---

## Final Checklist

Before sharing:

- [ ] Code pushed to GitHub
- [ ] `.gitignore` configured (no secrets)
- [ ] `requirements_streamlit.txt` complete
- [ ] Deployed to Streamlit Cloud
- [ ] Secrets configured
- [ ] Tested the deployed app
- [ ] Set OpenAI usage limits
- [ ] Prepared demo instructions
- [ ] Link ready to share

---

## Your Deployed App

**URL:** `https://[YOUR_APP_NAME].streamlit.app`

**Share with:** Anyone!

**Features:**
✅ All 5 agents always visible
✅ Real-time collaboration visualization
✅ Student profile support
✅ Conversation history
✅ Timeline and blackboard monitoring
✅ Perfect for ACL 2026 demo

**Ready to share with the world!** 🚀🎓
