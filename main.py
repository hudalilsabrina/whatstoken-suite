#!/usr/bin/env python3
"""
WhatsToken Suite CLI.
Automates account registration, wallet checking, token harvesting,
and seamless integration with 9router.
"""

import argparse
import json
import os
import random
import re
import sqlite3
import string
import sys
import time
import uuid
from typing import Optional, Dict, Any, List

from whatstoken_client import WhatsTokenClient, WhatsTokenError, ALLOWED_EMAIL_DOMAINS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
KEYS_FILE = os.path.join(BASE_DIR, "keys.txt")
ROUTER_DB_PATH = "/var/lib/9router/db/data.sqlite"
PROVIDER_NODE_ID = "openai-compatible-chat-whatstoken-001"


def print_step(msg: str):
    print(f"\n[+] {msg}", flush=True)


def print_sub(msg: str):
    print(f"    -> {msg}", flush=True)


def print_error(msg: str):
    print(f"[-] ERROR: {msg}", flush=True)


def validate_email_format(email: str) -> Optional[str]:
    email = email.strip()
    if "@" not in email:
        return "Email must contain @"
    user_part, domain_part = email.split("@", 1)
    
    # Check valid characters in username part: letters, numbers, underscores only
    if not re.match(r'^[a-zA-Z0-9_]+$', user_part):
        return "WhatsToken username prefix only allows letters, numbers, and underscores (no dots '.' or pluses '+')."
    
    # Check domain
    if domain_part.lower() not in ALLOWED_EMAIL_DOMAINS:
        allowed_str = ", ".join(ALLOWED_EMAIL_DOMAINS)
        return f"Domain '@{domain_part}' is not supported by WhatsToken backend. Allowed: {allowed_str}"

    return None


def random_password(length: int = 14) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(chars, k=length))


def inject_into_9router(email: str, api_key: str, name: Optional[str] = None) -> bool:
    if not os.path.exists(ROUTER_DB_PATH):
        print_sub("9router database not found, skipping injection.")
        return False

    try:
        conn = sqlite3.connect(ROUTER_DB_PATH)
        cur = conn.cursor()
        now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

        # 1. Ensure providerNode exists
        cur.execute("SELECT id FROM providerNodes WHERE id = ?;", (PROVIDER_NODE_ID,))
        if not cur.fetchone():
            node_data = {
                "prefix": "wt",
                "apiType": "chat",
                "baseUrl": "https://www.whatstoken.ai/v1",
                "nodeName": "WhatsToken",
                "logo": "",
                "createdAt": now,
                "updatedAt": now
            }
            cur.execute(
                "INSERT INTO providerNodes (id, type, name, data, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?);",
                (PROVIDER_NODE_ID, "openai-compatible", "WhatsToken", json.dumps(node_data), now, now)
            )
            print_sub("Created provider node 'WhatsToken' in 9router (prefix: 'wt')")

        # 2. Add connection
        conn_id = str(uuid.uuid4())
        account_name = name or email.split("@")[0]
        conn_data = {
            "apiKey": api_key,
            "defaultModel": "wt/gpt-4o-mini",
            "testStatus": "active",
            "errorCode": None,
            "backoffLevel": 0,
            "providerSpecificData": {
                "prefix": "wt",
                "apiType": "chat",
                "baseUrl": "https://www.whatstoken.ai/v1",
                "nodeName": "WhatsToken",
                "connectionProxyEnabled": False,
                "connectionProxyUrl": "",
                "connectionNoProxy": ""
            }
        }
        cur.execute(
            "INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (conn_id, PROVIDER_NODE_ID, "apikey", account_name, email, 1, 1, json.dumps(conn_data), now, now)
        )
        conn.commit()
        conn.close()
        print_sub(f"Added connection to 9router pool under prefix 'wt'!")
        return True
    except Exception as e:
        print_sub(f"Failed to inject to 9router: {e}")
        return False


def save_account_record(email: str, password: str, api_key: str, wallet: Dict[str, Any]):
    balance = wallet.get("balance", 0)
    gift = wallet.get("gift_balance", 0)
    
    with open(ACCOUNTS_FILE, "a") as f:
        f.write(
            f"=== {email} ===\n"
            f"email        : {email}\n"
            f"password     : {password}\n"
            f"apikey       : {api_key}\n"
            f"balance      : ${balance}\n"
            f"gift_balance : ${gift}\n"
            f"base_url     : https://www.whatstoken.ai/v1\n"
            f"referral_aff : NONE (stripped)\n"
            f"status       : active\n"
            f"timestamp    : {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

    # Append key
    with open(KEYS_FILE, "a") as f:
        f.write(f"{api_key}\n")

    print_sub(f"Saved account record to {ACCOUNTS_FILE}")


def do_register_interactive(args):
    print("=" * 60)
    print("WhatsToken AI - Interactive Registration (Zero-Referral)")
    print("=" * 60)

    client = WhatsTokenClient()

    # Step 1: Prompt Email
    while True:
        email = input("\nEnter your registration email (Gmail/Outlook/163/QQ): ").strip()
        err = validate_email_format(email)
        if err:
            print_error(err)
            continue
        break

    # Step 2: Request Code
    print_step(f"Requesting verification code for {email}...")
    try:
        client.send_verification_code(email)
        print_sub("Verification code sent successfully! Check your inbox.")
    except Exception as e:
        print_error(f"{e}")
        return

    # Step 3: Prompt Code & Password
    code = input("\nEnter the 6-digit verification code received: ").strip()
    password = args.password or random_password()
    print_sub(f"Using password: {password}")

    # Step 4: Submit Registration (Strip referral enforced)
    print_step("Registering account (referral stripped)...")
    try:
        reg_data = client.register_email(email, code, password, strip_referral=True)
        print_sub(f"Registration successful! Token acquired.")
    except Exception as e:
        print_error(f"{e}")
        return

    # Step 5: Check Wallet / Gift Credits
    print_step("Checking wallet balances...")
    try:
        wallet = client.get_wallet()
        print_sub(f"System Balance : ${wallet.get('balance', 0)}")
        print_sub(f"Gift Balance   : ${wallet.get('gift_balance', 0)}")
    except Exception as e:
        print_sub(f"Could not read wallet: {e}")
        wallet = {}

    # Step 6: Create or Reveal API Key
    print_step("Creating and revealing API key (sk-...)...")
    try:
        _, secret_key = client.get_or_create_api_key(name="9router Key")
        print_sub(f"API Key: {secret_key}")
    except Exception as e:
        print_error(f"Failed to generate API key: {e}")
        return

    # Step 7: Save & Inject
    save_account_record(email, password, secret_key, wallet)
    if not args.no_9router:
        inject_into_9router(email, secret_key)

    print("\n" + "=" * 60)
    print("Account Setup Complete!")
    print(f"API Key : {secret_key}")
    print(f"Base URL: https://www.whatstoken.ai/v1")
    print("=" * 60)


def do_login(args):
    print_step(f"Logging in {args.email}...")
    client = WhatsTokenClient()
    try:
        data = client.login(args.email, args.password)
        print_sub(f"Login successful!")
        
        wallet = client.get_wallet()
        print_sub(f"Balance: ${wallet.get('balance', 0)} | Gift: ${wallet.get('gift_balance', 0)}")

        _, secret_key = client.get_or_create_api_key()
        print_sub(f"Active Key: {secret_key}")

        save_account_record(args.email, args.password, secret_key, wallet)
        if not args.no_9router:
            inject_into_9router(args.email, secret_key)
    except Exception as e:
        print_error(f"{e}")


def do_check_balance(args):
    if not os.path.exists(ACCOUNTS_FILE):
        print_error(f"No accounts file found at {ACCOUNTS_FILE}")
        return

    print("=" * 70)
    print(f"{'Email':35} {'Balance':12} {'Gift':12}")
    print("=" * 70)

    with open(ACCOUNTS_FILE) as f:
        content = f.read()

    blocks = content.split("=== ")
    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        d = {}
        for l in lines:
            if ":" in l:
                k, v = l.split(":", 1)
                d[k.strip()] = v.strip()
        email = d.get("email")
        if email:
            bal = d.get("balance", "-")
            gift = d.get("gift_balance", "-")
            print(f"{email:35} {bal:12} {gift:12}")
    print("=" * 70)


def do_sync_9router(args):
    print_step("Syncing all keys from accounts.txt to 9router...")
    if not os.path.exists(ACCOUNTS_FILE):
        print_error(f"{ACCOUNTS_FILE} not found.")
        return

    count = 0
    with open(ACCOUNTS_FILE) as f:
        blocks = f.read().split("=== ")

    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        d = {}
        for l in lines:
            if ":" in l:
                k, v = l.split(":", 1)
                d[k.strip()] = v.strip()
        email = d.get("email")
        key = d.get("apikey")
        if email and key:
            if inject_into_9router(email, key):
                count += 1

    print_sub(f"Synchronized {count} keys into 9router pool!")


def main():
    parser = argparse.ArgumentParser(description="WhatsToken AI - Multi-Account & Key Management Suite")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # register command
    reg_parser = subparsers.add_parser("register", help="Register a new account interactively")
    reg_parser.add_argument("-p", "--password", help="Account password (optional, auto-generated if omitted)")
    reg_parser.add_argument("--no-9router", action="store_true", help="Do not inject into 9router")

    # login command
    login_parser = subparsers.add_parser("login", help="Login to an existing account and retrieve API key")
    login_parser.add_argument("-e", "--email", required=True, help="Email or username")
    login_parser.add_argument("-p", "--password", required=True, help="Password")
    login_parser.add_argument("--no-9router", action="store_true", help="Do not inject into 9router")

    # balance command
    subparsers.add_parser("balance", help="Display saved accounts and balances")

    # sync command
    subparsers.add_parser("sync", help="Sync all keys from accounts.txt to 9router")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "register":
        do_register_interactive(args)
    elif args.command == "login":
        do_login(args)
    elif args.command == "balance":
        do_check_balance(args)
    elif args.command == "sync":
        do_sync_9router(args)


if __name__ == "__main__":
    main()
