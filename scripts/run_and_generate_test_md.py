import json
from app.main import create_app

def run_tests():
    app = create_app()
    client = app.test_client()

    scenarios = [
        {
            "name": "Health check",
            "method": "GET",
            "path": "/api/health",
            "payload": None,
            "expected_status": 200,
            "validate": lambda r: r.json.get("status") == "ok"
        },
        {
            "name": "Analyze Greeting",
            "method": "POST",
            "path": "/api/understanding/analyze",
            "payload": {"query": "hello ji"},
            "expected_status": 200,
            "validate": lambda r: r.json.get("intent") == "greeting"
        },
        {
            "name": "Analyze Memory Store request",
            "method": "POST",
            "path": "/api/understanding/analyze",
            "payload": {"query": "note down my name is Saif"},
            "expected_status": 200,
            "validate": lambda r: r.json.get("intent") == "memory_store" or r.json.get("is_memory_store") == True
        },
        {
            "name": "Reflex: Alarm Set",
            "method": "POST",
            "path": "/api/and9",
            "payload": {"query": "alarm tomorrow 7 am"},
            "expected_status": 200,
            "validate": lambda r: r.json.get("action") == "set_alarm"
        },
        {
            "name": "Reflex: Reminder Set",
            "method": "POST",
            "path": "/api/and9",
            "payload": {"query": "remind me after 5 min to drink water"},
            "expected_status": 200,
            "validate": lambda r: r.json.get("action") == "set_reminder"
        },
        {
            "name": "Reflex: Reminder Set (after 5 seconds)",
            "method": "POST",
            "path": "/api/and9",
            "payload": {"query": "set reminder for after 5 seconds"},
            "expected_status": 200,
            "validate": lambda r: r.json.get("action") == "set_reminder" and r.json.get("payload", {}).get("trigger_at", {}).get("seconds") == 5
        },
        {
            "name": "Reflex: Time query in city",
            "method": "POST",
            "path": "/api/and9",
            "payload": {"query": "what is the time in delhi?"},
            "expected_status": 200,
            "validate": lambda r: "delhi" in r.json.get("response", "").lower()
        },
        {
            "name": "Memory Cache Stats",
            "method": "GET",
            "path": "/api/memory/cache/stats",
            "payload": None,
            "expected_status": 200,
            "validate": lambda r: "hits" in r.json
        },
        {
            "name": "Sessions Summary",
            "method": "GET",
            "path": "/api/memory/sessions",
            "payload": None,
            "expected_status": 200,
            "validate": lambda r: "sessions" in r.json
        }
    ]

    rows = []
    for s in scenarios:
        method = s["method"]
        path = s["path"]
        payload = s["payload"]
        
        print(f"Running scenario: {s['name']} -> {method} {path}")
        
        try:
            if method == "GET":
                resp = client.get(path)
            elif method == "POST":
                resp = client.post(path, json=payload)
            else:
                resp = None

            status_code = resp.status_code if resp else "N/A"
            actual_json = resp.json if resp else {}
            
            passed = (status_code == s["expected_status"]) and s["validate"](resp)
            result = "Passed" if passed else "Failed"
            problem = "None"
            solution = "None"
            
            if not passed:
                problem = f"Status code {status_code} or validation failed. Response: {actual_json}"
                solution = "Investigate logic error or expected pattern mismatch"

            rows.append({
                "input": f"{method} {path} ({payload})" if payload else f"{method} {path}",
                "expected": f"Status {s['expected_status']}",
                "actual": f"Status {status_code} ({list(actual_json.keys())[:3]} keys)" if actual_json else f"Status {status_code}",
                "result": result,
                "problem": problem,
                "solution": solution
            })
        except Exception as e:
            rows.append({
                "input": f"{method} {path} ({payload})" if payload else f"{method} {path}",
                "expected": f"Status {s['expected_status']}",
                "actual": f"Exception: {str(e)}",
                "result": "Failed",
                "problem": "Runtime Exception",
                "solution": f"Fix code trace: {str(e)}"
            })

    # Generate Markdown Table
    md = "# 📋 JARVIS PCOS — Integration Test Results\n\n"
    md += "| Input | Expected Output | Actual Output | Result (Passed/Failed) | Problem Faced | Solution |\n"
    md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for r in rows:
        md += f"| `{r['input']}` | {r['expected']} | {r['actual']} | **{r['result']}** | {r['problem']} | {r['solution']} |\n"
        
    with open("test.md", "w") as f:
        f.write(md)
    print("test.md generated successfully!")

if __name__ == "__main__":
    run_tests()
