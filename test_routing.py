from app.core.orchestrator import IntentRouter
router = IntentRouter()
print("PC Patterns:")
for kw in router.PATTERNS["pc"]:
    if kw in "write code to sort a list":
        print(f"Matched: '{kw}'")

print("Result:", router.route("write code to sort a list"))
