import sys
import os

# Ensure app package is importable
sys.path.insert(0, "/root/github/and9")

from app.brain.planner.and9 import AND9

def test_queries():
    # Make sure we use an in-memory DB for contacts
    os.environ["AND9_CONTACTS_DB"] = ":memory:"

    and9 = AND9(enable_patterns=False)

    queries = [
        "hello",
        "who is the prime minister of india",
        "set alarm for tomorrow 7 am",
        "kuch achhi joke sunao",
        "call mummy",
        "what is the time in delhi?"
    ]

    results = []
    for q in queries:
        print(f"Processing query: {q}")
        res = and9.process(q)
        results.append({
            "input": q,
            "response": res.get("response", ""),
            "action": res.get("action", ""),
            "intent": res.get("intent", ""),
            "success": res.get("success", False)
        })

    # Generate feedback.md
    md = "# 📝 User Feedback & Query Integration Results\n\n"
    md += "| Input Query | Response | Action | Intent | Success |\n"
    md += "| :--- | :--- | :--- | :--- | :--- |\n"
    for r in results:
        resp_escaped = r["response"].replace("\n", " ").replace("|", "\\|")
        md += f"| `{r['input']}` | {resp_escaped} | `{r['action']}` | `{r['intent']}` | {r['success']} |\n"

    with open("/root/github/and9/feedback.md", "w") as f:
        f.write(md)
    print("feedback.md generated successfully!")

if __name__ == "__main__":
    test_queries()
