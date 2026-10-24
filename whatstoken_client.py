#!/usr/bin/env python3
"""
WhatsToken AI (TokensByte / tkeapi) Client Library.
Handles auth, zero-affiliate registration, wallet inspection, and token management.
Target: https://www.whatstoken.ai
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import requests

logger = logging.getLogger("whatstoken")

BASE_URL = "https://www.whatstoken.ai"
API_BASE = f"{BASE_URL}/api/v1"
RELAY_BASE = f"{BASE_URL}/v1"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/register",
}

# Whitelisted email domains enforced by WhatsToken backend
ALLOWED_EMAIL_DOMAINS = [
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "163.com",
    "126.com",
    "qq.com",
    "foxmail.com",
    "aliyun.com",
    "proton.me",
    "icloud.com",
    "yahoo.com",
]


class WhatsTokenError(Exception):
    def __init__(self, message: str, code: Optional[str] = None, status: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.status = status


class WhatsTokenClient:
    def __init__(self, token: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.token = token
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def set_token(self, token: str):
        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def send_verification_code(self, email: str, purpose: str = "register") -> bool:
        """
        Request a 6-digit email verification code.
        Email domain must be in ALLOWED_EMAIL_DOMAINS and have valid alphanumeric prefix.
        """
        email = email.strip()
        url = f"{API_BASE}/auth/send-code"
        payload = {"email": email, "purpose": purpose}
        
        resp = self.session.post(url, json=payload, timeout=20)
        data = resp.json() if resp.text else {}
        
        if resp.status_code != 200 or not data.get("success"):
            err_msg = data.get("error", {}).get("message") or resp.text
            err_code = data.get("error", {}).get("code")
            raise WhatsTokenError(f"Failed to send code: {err_msg}", code=err_code, status=resp.status_code)
            
        return True

    def register_email(
        self,
        email: str,
        code: str,
        password: str,
        timezone: str = "Asia/Singapore",
        strip_referral: bool = True
    ) -> Dict[str, Any]:
        """
        Registers an account via email.
        NOTE: strip_referral=True guarantees no 'aff' or 'team' parameters are sent,
        preventing any referral/affiliate binding.
        """
        url = f"{API_BASE}/auth/register-email"
        payload = {
            "email": email.strip(),
            "code": code.strip(),
            "password": password,
            "timezone": timezone,
        }
        
        # Explicitly ensure referral/affiliate parameters are stripped
        if not strip_referral:
            pass # reserved if user ever wants aff

        resp = self.session.post(url, json=payload, timeout=25)
        data = resp.json() if resp.text else {}

        if resp.status_code not in (200, 201) or "token" not in data:
            err_msg = data.get("error", {}).get("message") or data.get("message") or resp.text
            err_code = data.get("error", {}).get("code")
            raise WhatsTokenError(f"Registration failed: {err_msg}", code=err_code, status=resp.status_code)

        token = data.get("token")
        if token:
            self.set_token(token)

        return data

    def login(self, email_or_username: str, password: str) -> Dict[str, Any]:
        """Authenticates with password and returns session JWT token and user info."""
        url = f"{API_BASE}/auth/login"
        payload = {
            "username": email_or_username.strip(),
            "password": password
        }
        resp = self.session.post(url, json=payload, timeout=20)
        data = resp.json() if resp.text else {}

        if resp.status_code != 200 or "token" not in data:
            err_msg = data.get("error", {}).get("message") or data.get("message") or resp.text
            raise WhatsTokenError(f"Login failed: {err_msg}", status=resp.status_code)

        token = data.get("token")
        if token:
            self.set_token(token)

        return data

    def get_profile(self) -> Dict[str, Any]:
        """Fetches current user profile."""
        url = f"{API_BASE}/user/profile"
        resp = self.session.get(url, timeout=15)
        if resp.status_code != 200:
            raise WhatsTokenError(f"Failed to fetch profile: {resp.text}", status=resp.status_code)
        return resp.json().get("data", resp.json())

    def get_wallet(self) -> Dict[str, Any]:
        """Fetches wallet balances (system balance, gift balance, recharge quota)."""
        url = f"{API_BASE}/user/wallet"
        resp = self.session.get(url, timeout=15)
        if resp.status_code != 200:
            raise WhatsTokenError(f"Failed to fetch wallet: {resp.text}", status=resp.status_code)
        return resp.json().get("data", resp.json())

    def list_tokens(self) -> List[Dict[str, Any]]:
        """Lists user's API tokens."""
        url = f"{API_BASE}/tokens"
        resp = self.session.get(url, params={"include_playground_2026": 1}, timeout=15)
        if resp.status_code != 200:
            raise WhatsTokenError(f"Failed to list tokens: {resp.text}", status=resp.status_code)
        return resp.json().get("data", [])

    def create_token(
        self,
        name: str = "Default Key",
        unlimited_quota: bool = True,
        remain_quota: int = -1,
        expired_time: int = -1
    ) -> Dict[str, Any]:
        """Creates a new API token."""
        url = f"{API_BASE}/tokens"
        payload = {
            "name": name,
            "unlimited_quota": unlimited_quota,
            "remain_quota": remain_quota,
            "expired_time": expired_time,
            "quota_limit": -1,
            "daily_quota_limit": -1,
            "weekly_quota_limit": -1,
            "monthly_quota_limit": -1,
            "rps_limit": 0,
            "rpm_limit": 0,
            "allowed_ips": "",
            "allowed_models": [],
            "high_availability": 0,
            "only_playground": 0,
            "only_playground_2026": 0
        }
        resp = self.session.post(url, json=payload, timeout=20)
        data = resp.json() if resp.text else {}
        if resp.status_code not in (200, 201) or "data" not in data:
            err_msg = data.get("error", {}).get("message") or resp.text
            raise WhatsTokenError(f"Failed to create token: {err_msg}", status=resp.status_code)
        return data["data"]

    def reveal_token(self, token_id: int) -> str:
        """Reveals the full sk-... API key for a given token ID."""
        url = f"{API_BASE}/tokens/{token_id}/reveal"
        resp = self.session.post(url, timeout=15)
        data = resp.json() if resp.text else {}
        if resp.status_code != 200:
            raise WhatsTokenError(f"Failed to reveal token: {resp.text}", status=resp.status_code)
        
        # Extract secret key
        key = data.get("key") or data.get("data", {}).get("key")
        if not key:
            raise WhatsTokenError(f"Secret key not returned: {data}")
        return key

    def get_or_create_api_key(self, name: str = "9router Key") -> Tuple[int, str]:
        """Helper to get existing active key or create and reveal a new one."""
        tokens = self.list_tokens()
        for t in tokens:
            if t.get("status") == 1 and t.get("id"):
                try:
                    secret = self.reveal_token(t["id"])
                    if secret:
                        return t["id"], secret
                except Exception:
                    pass

        # Create new
        new_tok = self.create_token(name=name)
        token_id = new_tok.get("id")
        secret = self.reveal_token(token_id)
        return token_id, secret

    def test_relay(self, api_key: str, model: str = "gpt-4o-mini", prompt: str = "1+1=") -> str:
        """Tests chat completions via the public OpenAI-compatible relay endpoint."""
        url = f"{RELAY_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50
        }
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise WhatsTokenError(f"Relay error ({resp.status_code}): {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
