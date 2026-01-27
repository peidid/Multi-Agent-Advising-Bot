#!/usr/bin/env python
"""
Run the Multi-Agent Advising API locally.

Usage:
    python run_api.py                    # Default: port 8000
    python run_api.py --port 3000        # Custom port
    python run_api.py --reload           # Enable hot reload
"""
import os
import sys
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Run the Multi-Agent Advising API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    args = parser.parse_args()

    # Check for .env file
    if not os.path.exists(".env"):
        print("WARNING: No .env file found. Copy .env.example to .env and configure it.")
        print("Proceeding with default/environment variables...\n")

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    # Check required variables
    required_vars = ["OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Please set these in your .env file or environment.")
        sys.exit(1)

    # Check MongoDB (optional for local dev - will use in-memory if not set)
    if not os.getenv("MONGODB_URI"):
        print("NOTE: MONGODB_URI not set. Make sure MongoDB is running locally")
        print("      or set MONGODB_URI for MongoDB Atlas.\n")

    print("=" * 60)
    print("Starting Multi-Agent Academic Advising API")
    print("=" * 60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reload: {args.reload}")
    print(f"Workers: {args.workers}")
    print("=" * 60)
    print(f"\nAPI Docs: http://localhost:{args.port}/docs")
    print(f"Health:   http://localhost:{args.port}/api/v1/health")
    print("=" * 60 + "\n")

    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="info"
    )


if __name__ == "__main__":
    main()
