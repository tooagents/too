from __future__ import annotations

import json

import httpx

AGENT_URL = "http://127.0.0.1:8000"


def run_demo(message: str = "vendor: acme supplies") -> None:
    print("STEP 1: User sends message from Frontend")
    print(f"  user -> frontend: {message}")

    resp = httpx.post(f"{AGENT_URL}/chat", json={"message": message}, timeout=20.0)
    resp.raise_for_status()
    data = resp.json()

    print("\nSTEP 2+: Agent trace (matches README flow)")
    for item in data["trace"]:
        print(f"  - {item['step']}")
        if "tools" in item:
            print(f"    tools: {item['tools']}")
        if "tool" in item:
            print(f"    selected: {item['tool']} args={item['arguments']}")

    print("\nFINAL ANSWER")
    print(f"  {data['answer']}")

    print("\nRAW JSON")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    run_demo()
