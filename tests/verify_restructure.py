"""Verify the full restructure — imports and key classes work."""
import sys, os, ast
sys.path.insert(0, "/root/github/and9")

passed = 0
failed = 0

def check(label, module_path, class_name):
    global passed, failed
    try:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        print(f"  ✅ {label}")
        passed += 1
    except (ImportError, AttributeError) as e:
        print(f"  ❌ {label}: {e}")
        failed += 1

print("=== Core imports ===")
check("config",       "app.core.config", "ConfigStore")
check("personality",  "app.core.personality", "PersonalityService")
check("learning",     "app.core.learning_system", "LearningSystem")
check("orchestrator", "app.brain.planner.orchestrator", "Orchestrator")
check("events",       "app.core.events", "EventSystem")

print("\n=== Merged Phase 22-30 feature imports ===")
check("Phase 22: Real-Time Info",  "app.integrations.realtime", "RealtimeInfoService")
check("Phase 23: Voice",           "app.services.speech", "VoiceControllerService")
check("Phase 24: Conversation",    "app.core.conversation", "SessionManager")
check("Phase 25: Personality",     "app.core.personality", "PersonalityService")
check("Phase 26: Learning",        "app.core.learning_system", "LearningSystem")
check("Phase 27: Knowledge",       "app.memory.semantic.knowledge_base", "KnowledgeBase")
check("Phase 30: Notification",    "app.services.notification", "NotificationManagerService")

print("\n=== Merged Phase 31-40 feature imports ===")
check("Phase 32: Security",        "app.core.security", "InputValidator")
check("Phase 32: Security (Auth)", "app.core.security", "AuthManager")
check("Phase 33: Permissions",     "app.core.permissions", "PermissionChecker")
check("Phase 34: Error Recovery",  "app.core.errors", "CircuitBreaker")
check("Phase 34: Rollback",        "app.core.errors", "RollbackManager")
check("Phase 36: Analytics",       "app.core.analytics", "DashboardGenerator")
check("Phase 39: Plugin SDK",      "app.core.plugin_sdk", "PluginBase")
check("Phase 39: Plugin SDK (Loader)", "app.core.plugin_sdk", "PluginLoader")
check("Phase 40: Performance",     "app.core.performance", "StartupOptimizer")
check("Phase 40: Profiler",        "app.core.performance", "BottleneckProfiler")

print("\n=== No stale references ===")
stale_patterns = [
    "from backend.", "import backend.",
    "from cognition.", "import cognition.",
    "from services.base", "import services.base",
    "from services.phase", "import services.phase",
    "from ai.micro_brain", "import ai.micro_brain",
    "app.cognition",
]

app_dir = "/root/github/and9/app"
issues = []
for root, dirs, files in os.walk(app_dir):
    for fn in files:
        if not fn.endswith(".py"):
            continue
        fp = os.path.join(root, fn)
        try:
            with open(fp) as f:
                content = f.read()
                for pat in stale_patterns:
                    if pat in content:
                        rel = os.path.relpath(fp, app_dir)
                        issues.append(f"  ⚠️  {rel}: contains '{pat}'")
        except:
            pass

if issues:
    for i in issues:
        print(i)
    failed += len(issues)
else:
    print("  ✅ No stale import paths found")

print(f"\n{'='*40}")
print(f"  Passed: {passed} | Failed: {failed}")
if failed:
    print("  ❌ Some checks failed!")
    sys.exit(1)
else:
    print("  🎉 All systems verified!")
