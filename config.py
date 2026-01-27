"""
Model Configuration
Centralized configuration for LLM models used across the system.

Strategy:
- Coordinator: Uses more powerful model for complex routing, synthesis, and conflict resolution
- Agents: Use faster, cost-effective model for domain-specific tasks
"""
import os
from typing import Optional

# ============================================================================
# OPENAI API CONFIGURATION
# ============================================================================
# For users in China or behind firewalls, set OPENAI_API_BASE to a proxy URL
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", None)

def get_openai_base_url() -> Optional[str]:
    """Get OpenAI API base URL (for proxy support)."""
    return OPENAI_API_BASE

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Coordinator Model - Handles complex reasoning, routing, and synthesis
# TODO: Change to "gpt-5" when OpenAI releases GPT-5
COORDINATOR_MODEL = "gpt-4-turbo"  # Best available model for complex tasks
COORDINATOR_TEMPERATURE = 0.3

# Agent Models - Fast and cost-effective for domain-specific tasks
AGENT_MODEL = "gpt-4o"  # Fast, cost-effective, good quality
AGENT_TEMPERATURE = 0.3

# ============================================================================
# MODEL SELECTION LOGIC
# ============================================================================

def get_coordinator_model() -> str:
    """Get the model name for the Coordinator."""
    return COORDINATOR_MODEL

def get_agent_model() -> str:
    """Get the model name for Agents."""
    return AGENT_MODEL

def get_coordinator_temperature() -> float:
    """Get temperature for Coordinator."""
    return COORDINATOR_TEMPERATURE

def get_agent_temperature() -> float:
    """Get temperature for Agents."""
    return AGENT_TEMPERATURE

# ============================================================================
# MODEL INFORMATION
# ============================================================================

MODEL_INFO = {
    "coordinator": {
        "model": COORDINATOR_MODEL,
        "temperature": COORDINATOR_TEMPERATURE,
        "purpose": "Complex routing, intent classification, conflict resolution, answer synthesis",
        "upgrade_note": "Set to 'gpt-5' when OpenAI releases GPT-5"
    },
    "agents": {
        "model": AGENT_MODEL,
        "temperature": AGENT_TEMPERATURE,
        "purpose": "Domain-specific knowledge retrieval and processing",
        "upgrade_note": "Optimized for speed and cost-effectiveness"
    }
}

def print_model_config():
    """Print current model configuration."""
    print("=" * 70)
    print("Model Configuration")
    print("=" * 70)
    print(f"\n📊 Coordinator Model: {COORDINATOR_MODEL}")
    print(f"   Temperature: {COORDINATOR_TEMPERATURE}")
    print(f"   Purpose: {MODEL_INFO['coordinator']['purpose']}")
    print(f"   Note: {MODEL_INFO['coordinator']['upgrade_note']}")
    print(f"\n🤖 Agent Model: {AGENT_MODEL}")
    print(f"   Temperature: {AGENT_TEMPERATURE}")
    print(f"   Purpose: {MODEL_INFO['agents']['purpose']}")
    print("=" * 70)

if __name__ == "__main__":
    print_model_config()
