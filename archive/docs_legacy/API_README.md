# Multi-Agent Academic Advising API

## ACL 2026 Demo Track Submission

A RESTful API for the dynamic multi-agent academic advising system, designed for deployment on Railway with MongoDB Atlas.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Any UI)                        │
│                   React / Vue / Mobile App                       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │    Auth     │  │   Profiles  │  │         Chat            │ │
│  │   Routes    │  │   Routes    │  │        Routes           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                              │                   │
│                                              ▼                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │               Multi-Agent Workflow (LangGraph)             │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │
│  │  │ Programs │ │ Courses  │ │  Policy  │ │   Planning   │  │ │
│  │  │  Agent   │ │  Agent   │ │  Agent   │ │    Agent     │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │ │
│  │                      ▲                                      │ │
│  │                      │                                      │ │
│  │              ┌───────┴───────┐                             │ │
│  │              │  Coordinator  │                             │ │
│  │              │  (Orchestrator)│                            │ │
│  │              └───────────────┘                             │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
          ┌─────────────────┐       ┌─────────────────┐
          │  MongoDB Atlas  │       │    ChromaDB     │
          │  (User Data,    │       │  (Vector Store) │
          │   Conversations)│       │                 │
          └─────────────────┘       └─────────────────┘
```

## Features

### API Capabilities
- **User Authentication**: JWT-based auth with role-based access control
- **Student Profiles**: Store and retrieve academic history for personalization
- **Conversation History**: Persistent chat storage with full workflow details
- **Multi-Agent Chat**: Dynamic orchestration of specialized agents
- **Streaming Responses**: Real-time updates on agent activity

### Multi-Agent System
- **Coordinator**: Intent classification, workflow planning, conflict detection
- **Programs Agent**: Degree requirements, progress validation
- **Courses Agent**: Course offerings, scheduling, prerequisites
- **Policy Agent**: University policy compliance checking
- **Planning Agent**: Multi-semester academic planning

## Quick Start

### 1. Prerequisites

- Python 3.11+
- MongoDB Atlas account (free tier works)
- OpenAI API key

### 2. Local Development

```bash
# Clone and navigate
cd "Product 0110"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements_api.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the API
uvicorn api.main:app --reload --port 8000
```

### 3. Access the API

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and get JWT |
| POST | `/api/v1/auth/token` | OAuth2 token endpoint |
| GET | `/api/v1/auth/me` | Get current user |

### Student Profiles
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/profiles/me` | Get my profile |
| POST | `/api/v1/profiles` | Create profile |
| PUT | `/api/v1/profiles/me` | Update profile |
| POST | `/api/v1/profiles/me/courses/completed` | Add completed course |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Send message, get response |
| POST | `/api/v1/chat/stream` | Streaming response (SSE) |
| POST | `/api/v1/chat/quick` | Quick chat (no auth) |

### Conversations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/conversations` | List my conversations |
| GET | `/api/v1/conversations/{id}` | Get conversation |
| GET | `/api/v1/conversations/{id}/messages` | Get messages |
| DELETE | `/api/v1/conversations/{id}` | Delete conversation |

## Deployment on Railway

### 1. Create MongoDB Atlas Cluster

1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a free cluster
3. Create a database user
4. Whitelist `0.0.0.0/0` for Railway (or use Network Access)
5. Copy the connection string

### 2. Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Add environment variables
railway variables set MONGODB_URI="mongodb+srv://..."
railway variables set OPENAI_API_KEY="sk-..."
railway variables set JWT_SECRET_KEY="your-secret"

# Deploy
railway up
```

### 3. Or use Railway Dashboard

1. Connect your GitHub repository
2. Railway auto-detects the Dockerfile
3. Add environment variables in the dashboard
4. Deploy automatically on push

### Environment Variables for Railway

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | Yes | MongoDB Atlas connection string |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `JWT_SECRET_KEY` | Yes | Secret for JWT signing |
| `PORT` | No | Railway sets this automatically |
| `ALLOWED_ORIGINS` | No | CORS origins (comma-separated) |

## Example Usage

### Register and Login

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@cmu.edu",
    "password": "password123",
    "full_name": "Test Student",
    "student_id": "tstudent"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@cmu.edu",
    "password": "password123"
  }'

# Returns: {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600}
```

### Create Profile

```bash
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID",
    "primary_major": "Information Systems",
    "current_gpa": 3.5,
    "cumulative_credits": 180
  }'
```

### Chat with the Advisor

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can I add a CS minor as an IS student?",
    "include_workflow_details": true
  }'
```

### Response Example

```json
{
  "conversation_id": "65a1b2c3d4e5f6g7h8i9j0k1",
  "message_id": "1705123456.789",
  "response": "Yes, IS students can add a CS minor! Here's what you need to know...",
  "workflow": {
    "step": "complete",
    "active_agents": ["programs_requirements", "policy_compliance"],
    "completed_agents": ["programs_requirements", "policy_compliance"],
    "agent_outputs": {
      "programs_requirements": {
        "answer": "The CS minor requires...",
        "confidence": 0.9
      }
    }
  },
  "agents_used": ["programs_requirements", "policy_compliance"],
  "conflicts_detected": 0,
  "total_time_ms": 3500
}
```

## MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `users` | User accounts and authentication |
| `student_profiles` | Academic history and preferences |
| `conversations` | Chat history with workflow details |
| `sessions` | User sessions (optional) |
| `audit_logs` | Activity logging |

## Project Structure

```
Product 0110/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # MongoDB connection
│   ├── models/              # Pydantic models
│   │   ├── user.py
│   │   ├── student_profile.py
│   │   ├── conversation.py
│   │   └── session.py
│   ├── services/            # Business logic
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── profile_service.py
│   │   └── conversation_service.py
│   └── routes/              # API endpoints
│       ├── auth.py
│       ├── chat.py
│       ├── users.py
│       ├── profiles.py
│       ├── conversations.py
│       └── health.py
├── agents/                  # Multi-agent system
├── coordinator/             # Orchestration
├── blackboard/              # Shared state
├── data/                    # Knowledge base
├── Dockerfile
├── railway.json
├── requirements_api.txt
└── .env.example
```

## Benefits of API Architecture

| Benefit | Description |
|---------|-------------|
| **Decoupled UI** | Any frontend can connect (React, mobile, etc.) |
| **Scalability** | Railway auto-scales based on load |
| **Persistence** | All conversations stored in MongoDB |
| **Multi-user** | Proper authentication and isolation |
| **Demo-ready** | Live API for ACL 2026 demo |
| **Integration** | Other systems can call your API |

## Next Steps

1. **Frontend Development**: Build a React/Vue UI that calls this API
2. **Additional Agents**: Add more specialized agents as needed
3. **Analytics**: Add dashboards for conversation metrics
4. **Fine-tuning**: Improve agent prompts based on usage data

## Support

For issues or questions, please open a GitHub issue.
