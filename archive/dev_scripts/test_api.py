#!/usr/bin/env python
"""
Test script for the Multi-Agent Advising API.

Run this after starting the API to verify everything works.

Usage:
    python test_api.py                    # Test against localhost:8000
    python test_api.py --url https://...  # Test against deployed URL
"""
import argparse
import requests
import json
from typing import Optional


class APITester:
    """Simple API tester for the advising system."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None

    def _headers(self):
        """Get headers with auth token if available."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def test_health(self) -> bool:
        """Test health endpoint."""
        print("\n1. Testing Health Endpoint...")
        try:
            resp = requests.get(f"{self.base_url}/api/v1/health")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✓ Status: {data['status']}")
                print(f"   ✓ MongoDB: {data['components'].get('mongodb', {}).get('status')}")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_register(self, email: str, password: str) -> bool:
        """Test user registration."""
        print("\n2. Testing User Registration...")
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/auth/register",
                headers=self._headers(),
                json={
                    "email": email,
                    "password": password,
                    "full_name": "Test User",
                    "student_id": "testuser"
                }
            )
            if resp.status_code == 201:
                data = resp.json()
                self.user_id = data["id"]
                print(f"   ✓ Registered user: {data['email']}")
                print(f"   ✓ User ID: {self.user_id}")
                return True
            elif resp.status_code == 400:
                print(f"   ~ User may already exist, trying login...")
                return True  # Continue to login
            else:
                print(f"   ✗ Failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_login(self, email: str, password: str) -> bool:
        """Test login and get token."""
        print("\n3. Testing Login...")
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                headers=self._headers(),
                json={
                    "email": email,
                    "password": password
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                print(f"   ✓ Login successful")
                print(f"   ✓ Token: {self.token[:20]}...")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_get_me(self) -> bool:
        """Test getting current user info."""
        print("\n4. Testing Get Current User...")
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/auth/me",
                headers=self._headers()
            )
            if resp.status_code == 200:
                data = resp.json()
                self.user_id = data["id"]
                print(f"   ✓ User: {data['email']}")
                print(f"   ✓ Role: {data['role']}")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_create_profile(self) -> bool:
        """Test creating a student profile."""
        print("\n5. Testing Create Profile...")
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/profiles",
                headers=self._headers(),
                json={
                    "user_id": self.user_id,
                    "primary_major": "Information Systems",
                    "current_gpa": 3.5,
                    "cumulative_credits": 180,
                    "career_interests": ["software engineering", "data science"]
                }
            )
            if resp.status_code == 201:
                data = resp.json()
                print(f"   ✓ Profile created for: {data['primary_major']}")
                return True
            elif resp.status_code == 400:
                print(f"   ~ Profile may already exist")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_get_profile(self) -> bool:
        """Test getting profile."""
        print("\n6. Testing Get Profile...")
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/profiles/me",
                headers=self._headers()
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✓ Major: {data['primary_major']}")
                print(f"   ✓ GPA: {data.get('current_gpa', 'N/A')}")
                return True
            elif resp.status_code == 404:
                print(f"   ~ No profile found (may need to create one)")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_chat(self, message: str) -> bool:
        """Test the chat endpoint."""
        print(f"\n7. Testing Chat: '{message}'...")
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/chat",
                headers=self._headers(),
                json={
                    "message": message,
                    "include_workflow_details": True
                },
                timeout=120  # 2 minutes for agent processing
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✓ Response received")
                print(f"   ✓ Conversation ID: {data['conversation_id']}")
                print(f"   ✓ Agents used: {data['agents_used']}")
                print(f"   ✓ Time: {data['total_time_ms']}ms")
                print(f"\n   Response preview:")
                print(f"   {data['response'][:200]}...")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code} - {resp.text}")
                return False
        except requests.exceptions.Timeout:
            print(f"   ✗ Timeout - agents took too long")
            return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_conversations(self) -> bool:
        """Test listing conversations."""
        print("\n8. Testing List Conversations...")
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/conversations",
                headers=self._headers()
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✓ Found {len(data)} conversations")
                for conv in data[:3]:
                    print(f"     - {conv.get('title', 'Untitled')}")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

    def test_quick_chat(self, message: str) -> bool:
        """Test quick chat (no auth)."""
        print(f"\n9. Testing Quick Chat (no auth): '{message}'...")
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/chat/quick",
                json={"message": message},
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✓ Response received")
                print(f"   ✓ Agents: {data.get('agents_used', [])}")
                print(f"\n   Response preview:")
                print(f"   {data['response'][:200]}...")
                return True
            else:
                print(f"   ✗ Failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Test the Multi-Agent Advising API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--email", default="test@example.com", help="Test user email")
    parser.add_argument("--password", default="testpassword123", help="Test user password")
    parser.add_argument("--skip-chat", action="store_true", help="Skip chat tests (faster)")
    args = parser.parse_args()

    print("=" * 60)
    print("Multi-Agent Advising API Test Suite")
    print("=" * 60)
    print(f"Target: {args.url}")
    print("=" * 60)

    tester = APITester(args.url)
    results = []

    # Run tests
    results.append(("Health", tester.test_health()))
    results.append(("Register", tester.test_register(args.email, args.password)))
    results.append(("Login", tester.test_login(args.email, args.password)))
    results.append(("Get Me", tester.test_get_me()))
    results.append(("Create Profile", tester.test_create_profile()))
    results.append(("Get Profile", tester.test_get_profile()))

    if not args.skip_chat:
        results.append(("Chat", tester.test_chat("Can I add a CS minor as an IS student?")))
        results.append(("Conversations", tester.test_conversations()))
        results.append(("Quick Chat", tester.test_quick_chat("What courses are offered in Spring 2026?")))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print()
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print("\n" + "=" * 60)
    if passed == total:
        print("All tests passed! API is working correctly.")
    else:
        print("Some tests failed. Check the output above for details.")
    print("=" * 60)


if __name__ == "__main__":
    main()
