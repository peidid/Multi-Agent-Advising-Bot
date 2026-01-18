# Deployment Guide - Share Your Advising Bot via Link

**Share your multi-agent advising system with anyone in the world!**

---

## 🌐 Deployment Options

### Option 1: Streamlit Community Cloud (FREE & EASIEST) ⭐

**Perfect for demos, sharing with advisors, ACL 2026 reviewers**

✅ **100% Free**
✅ **Share via link** (e.g., `https://your-app.streamlit.app`)
✅ **Auto-updates** from GitHub
✅ **No server management**

---

## 🚀 Deploy to Streamlit Cloud (Step-by-Step)

### Prerequisites

- GitHub account (free)
- Your code pushed to GitHub repository
- OpenAI API key

### Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
cd "e:\CMU\Research\AdvisingBot\Product 0110"
git init

# Add all files
git add .

# Commit
git commit -m "Add Streamlit advising bot"

# Create repository on GitHub (via website)
# Then connect and push:
git remote add origin https://github.com/YOUR_USERNAME/cmu-advising-bot.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. **Go to**: https://share.streamlit.io/

2. **Sign in** with GitHub

3. **Click "New app"**

4. **Fill in details**:
   - Repository: `YOUR_USERNAME/cmu-advising-bot`
   - Branch: `main`
   - Main file path: `streamlit_app_enhanced.py`

5. **Advanced settings** → Click "Secrets"

6. **Add your secrets**:
   ```toml
   OPENAI_API_KEY = "sk-your-actual-openai-api-key"
   ```

7. **Click "Deploy"**

8. **Wait 2-5 minutes** for deployment

9. **Get your link!** (e.g., `https://cmu-advising-bot.streamlit.app`)

### Step 3: Share Your Link

✅ Your app is now **public** and accessible to anyone!

Share the link with:
- Academic advisors
- Students
- Research collaborators
- ACL 2026 reviewers

---

## 🔒 Making It Private (Optional)

By default, Streamlit Cloud apps are **public**. To restrict access:

### Option A: Password Protection (Simple)

Add to `streamlit_app_enhanced.py`:

```python
import streamlit as st
import hmac

def check_password():
    """Returns `True` if user entered correct password."""

    def password_entered():
        """Checks whether password is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    # Return True if password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

# Add at top of main()
if not check_password():
    st.stop()  # Do not continue if password incorrect
```

Add to secrets:
```toml
password = "your-demo-password"
```

### Option B: Email Whitelist

```python
def check_email():
    """Check if user email is whitelisted."""

    allowed_emails = st.secrets.get("allowed_emails", "").split(",")

    if "user_email" not in st.session_state:
        email = st.text_input("Enter your CMU email:")
        if email:
            if email in allowed_emails or email.endswith("@cmu.edu"):
                st.session_state["user_email"] = email
                st.rerun()
            else:
                st.error("Access denied. CMU email required.")
                st.stop()
        else:
            st.stop()

    return True

# Add at top of main()
check_email()
```

---

## 🔄 Auto-Updates from GitHub

**Every time you push to GitHub, the app auto-updates!**

```bash
# Make changes to your code
# Then:
git add .
git commit -m "Improved workflow visualization"
git push

# Streamlit Cloud will automatically:
# 1. Detect the push
# 2. Rebuild the app
# 3. Deploy new version
# (Takes ~2-3 minutes)
```

---

## 📊 Monitor Usage

### View App Analytics

1. Go to https://share.streamlit.io/
2. Click your app
3. See metrics:
   - Total views
   - Active users
   - Error logs
   - Resource usage

### Add Custom Analytics (Optional)

```python
# In streamlit_app_enhanced.py

import streamlit as st
from datetime import datetime

# Log query
def log_query(user_query):
    """Log queries for analytics."""

    if 'query_log' not in st.session_state:
        st.session_state.query_log = []

    st.session_state.query_log.append({
        "timestamp": datetime.now().isoformat(),
        "query": user_query,
        "user_id": st.session_state.get("user_email", "anonymous")
    })

    # Optionally: Send to external analytics
    # requests.post("your-analytics-endpoint", json=query_data)
```

---

## 🎓 Custom Domain (Optional)

Want `advising.cmu-q.edu` instead of `your-app.streamlit.app`?

**For CMU hosting:**
1. Contact CMU IT
2. Request subdomain
3. Point CNAME to Streamlit Cloud
4. Configure in Streamlit settings

**For personal domain:**
1. Buy domain (Namecheap, Google Domains)
2. Add CNAME record → `your-app.streamlit.app`
3. Update Streamlit settings

---

## ⚙️ Alternative Deployment Options

### Option 2: Heroku

**Good for**: Custom server control, larger apps

```bash
# Install Heroku CLI
# Then:
heroku create cmu-advising-bot
git push heroku main
heroku ps:scale web=1
heroku open
```

**Cost**: ~$7/month for hobby tier

### Option 3: AWS / Google Cloud

**Good for**: Enterprise, high traffic, custom infrastructure

**Cost**: Pay-as-you-go (can be $0-20/month for demos)

See detailed guides:
- AWS: https://docs.streamlit.io/deploy/tutorials/aws
- GCP: https://docs.streamlit.io/deploy/tutorials/gcp

### Option 4: CMU Servers

**Good for**: Internal CMU use, no external dependencies

Contact CMU IT for:
- Server allocation
- Domain setup
- SSL certificate

---

## 🐛 Troubleshooting Deployment

### Issue: App won't deploy

**Check**:
1. `requirements.txt` includes all dependencies
2. `requirements_streamlit.txt` is listed
3. No local file paths (use relative paths)
4. API keys in secrets, not code

### Issue: App crashes on startup

**Check logs**:
1. Streamlit Cloud dashboard → Your app → Logs
2. Look for import errors
3. Check missing dependencies

**Common fixes**:
```bash
# Add to requirements.txt
python-dotenv
urllib3
```

### Issue: Slow performance

**Optimize**:
```python
# Add caching
@st.cache_data
def load_program_requirements():
    # ...

@st.cache_resource
def get_llm():
    # ...
```

### Issue: API key not working

**Check**:
1. Secrets properly formatted (TOML syntax)
2. No quotes issues (`"` vs `'`)
3. Key has correct permissions
4. Billing enabled on OpenAI account

---

## 📧 Share Your Link

### For ACL 2026 Demo

**Include in submission**:
```
Demo URL: https://cmu-advising-bot.streamlit.app
Access: Public / Password: demo2026
Instructions: Click examples in sidebar or ask questions
```

### For Advisors / Students

**Email template**:
```
Subject: Try the new AI Academic Advising System

Hi [Name],

I've built an AI-powered academic advising system that can:
- Answer questions about major requirements
- Generate 4-year graduation plans
- Check policy compliance
- Integrate minors into your schedule

Try it here: https://cmu-advising-bot.streamlit.app

Example questions:
- "What are the CS major requirements?"
- "Help me plan my courses until graduation"
- "Can I add a Business minor?"

The system shows real-time multi-agent collaboration!

Questions? Let me know!
```

### For Researchers

**Include in paper**:
```
A live demo of the system is available at:
https://cmu-advising-bot.streamlit.app

The interface visualizes dynamic multi-agent collaboration,
blackboard state evolution, and negotiation protocols in
real-time. See supplementary materials for screenshots.
```

---

## 🔐 Security Best Practices

### 1. Never Commit Secrets

✅ **Good**:
```python
api_key = st.secrets["OPENAI_API_KEY"]
```

❌ **Bad**:
```python
api_key = "sk-abc123..."  # Never hardcode!
```

### 2. Add .gitignore

```bash
# .gitignore
.streamlit/secrets.toml
.env
__pycache__/
*.pyc
.DS_Store
chroma_db_*/
```

### 3. Rotate API Keys

If you accidentally commit a key:
1. Immediately revoke it on OpenAI
2. Generate new key
3. Update secrets on Streamlit Cloud
4. Remove from git history:
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

### 4. Monitor Usage

Set up OpenAI usage alerts:
1. OpenAI Dashboard → Usage
2. Set budget limits
3. Enable email notifications

---

## 📊 Cost Estimation

### Streamlit Cloud
- **Hosting**: FREE
- **Bandwidth**: FREE (up to reasonable limits)
- **Total**: $0/month

### OpenAI API
- **GPT-4o**: ~$0.005 per query (typical)
- **Estimated**: 1000 queries = ~$5
- **Set limits** in OpenAI dashboard to control costs

### Total Monthly Cost
- Demo/testing: $0-10
- Light usage (100 users): $10-50
- Heavy usage (1000+ users): $50-200

**Tip**: Use GPT-4o-mini for lower costs ($0.0015/query)

---

## ✅ Deployment Checklist

Before deploying:

- [ ] Code pushed to GitHub
- [ ] `.gitignore` configured (no secrets committed)
- [ ] `requirements.txt` complete
- [ ] `requirements_streamlit.txt` added
- [ ] API key ready
- [ ] Test locally first (`streamlit run streamlit_app_enhanced.py`)
- [ ] Create Streamlit Cloud account
- [ ] Deploy app
- [ ] Add secrets in Streamlit dashboard
- [ ] Test deployed app
- [ ] Get shareable link
- [ ] Share with intended audience

---

## 🎬 Demo-Ready Features

Your enhanced UI includes:

✅ **Live workflow visualization** - Watch agents in action
✅ **Real-time blackboard** - See state updates live
✅ **Animated agent flow** - Visual agent collaboration
✅ **Progress indicators** - Step-by-step workflow
✅ **Negotiation bubbles** - See conflicts resolve
✅ **Example queries** - One-click demos
✅ **Student profile** - Customizable for different scenarios

**Perfect for sharing with reviewers, advisors, and students!**

---

## 📖 Next Steps

1. **Deploy now**: Follow Step-by-Step guide above
2. **Get feedback**: Share with 2-3 test users
3. **Iterate**: Improve based on feedback
4. **Promote**: Share with wider audience
5. **Monitor**: Check analytics and usage
6. **Maintain**: Update as needed

---

## 🆘 Need Help?

- **Streamlit Docs**: https://docs.streamlit.io/deploy
- **Streamlit Forum**: https://discuss.streamlit.io
- **OpenAI Support**: https://help.openai.com

**Your app is ready to share with the world!** 🚀

Deploy command:
```bash
# Just push to GitHub, then deploy via Streamlit Cloud UI
git add .
git commit -m "Ready for deployment"
git push
```
