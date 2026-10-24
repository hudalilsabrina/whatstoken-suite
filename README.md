# WhatsToken AI Suite ⚡

Automated account registration, token harvesting, wallet tracking, and **9router** integration suite for **WhatsToken AI** ([whatstoken.ai](https://www.whatstoken.ai)).

Built specifically with **zero-referral enforcement**: explicitly strips and prevents all referral (`aff`) and team invite parameters during registration.

---

## Features

- **Strict Zero-Referral Enforcement**: Automatically strips any affiliate code (`aff`) and team invite parameters, ensuring direct, clean account registration.
- **Email Whitelist Handling**: Built-in validation adhering strictly to WhatsToken's backend rules:
  - Supported domains: `gmail.com`, `outlook.com`, `hotmail.com`, `163.com`, `126.com`, `qq.com`, `foxmail.com`, `aliyun.com`, `proton.me`, `icloud.com`, `yahoo.com`.
  - Enforces alphanumeric/underscore usernames (rejecting invalid dots `.` or pluses `+` in the local part before submission).
- **Automated Token Management**: Automatically creates and reveals the full `sk-...` API key via `/api/v1/tokens/{id}/reveal`.
- **Wallet & Gift Balance Inspection**: Fetches and logs promotional registration gifts and system balances.
- **Seamless 9router Integration**: Automatically inserts the provider node `WhatsToken` and harvested keys into 9router (`/var/lib/9router/db/data.sqlite`) under the prefix `wt`.

---

## Installation

```bash
git clone https://github.com/hudalilsabrina/whatstoken-suite.git
cd whatstoken-suite
chmod +x install.sh
./install.sh
```

---

## Usage Guide

### 1. Register a New Account (Zero-Referral)

```bash
./main.py register
```
Interactive steps:
1. Prompts for your email (e.g. `yourname@outlook.com` or `yourname@gmail.com`).
2. Requests the 6-digit OTP code from WhatsToken.
3. Prompts for the code received in your inbox.
4. Registers the account, generates an API key, checks wallet balance, saves to `accounts.txt`, and automatically injects it into 9router!

### 2. Login & Harvest Key from Existing Account

```bash
./main.py login -e user@outlook.com -p "YourPassword123"
```

### 3. Check Account Balances

```bash
./main.py balance
```

### 4. Sync Keys to 9router

```bash
./main.py sync
```

---

## Using with OpenAI SDK

Direct API access:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://www.whatstoken.ai/v1",
    api_key="sk-...",
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Halo!"}],
)
print(response.choices[0].message.content)
```

---

## Using via 9router

Once injected by the suite:

```bash
curl http://127.0.0.1:20127/v1/chat/completions \
  -H "Authorization: Bearer <9ROUTER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "wt/gpt-4o-mini",
    "messages": [{"role": "user", "content": "Halo!"}]
  }'
```
