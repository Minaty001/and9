import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.services.reminder import storage
from backend.services.reminder.worker import start_worker, stop_worker, register_callback

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("verify_loop")

IST = ZoneInfo("Asia/Kolkata")

fired_events = []

def test_callback(reminder):
    logger.info(f"CALLBACK TRIGGERED: Fired reminder #{reminder['id']} '{reminder['title']}'")
    fired_events.append(reminder)

def main():
    logger.info("Initializing reminder verification test...")
    register_callback(test_callback)

    # 1. Clear existing database entries for a clean test
    storage.clear_all()
    with storage._conn() as con:
        con.execute("DELETE FROM reminders_v2")
        con.execute("DELETE FROM reminders")
        con.commit()

    # 2. Add a recurring daily reminder triggering immediately
    now = datetime.now(IST)
    rid = storage.add(
        title="Test Recurring Reminder",
        trigger_time=now - timedelta(seconds=1),  # slightly in the past so it triggers immediately
        repeat_rule="daily",
        user_id="default",
    )
    logger.info(f"Created recurring daily reminder #{rid}")

    # 3. Start the background worker
    start_worker()

    # 4. Wait for 12 seconds (allowing the first poll cycle to run)
    logger.info("Waiting 12 seconds for the first worker poll cycle...")
    time.sleep(12)

    # 5. Check if the reminder rescheduled a new occurrence
    with storage._conn() as con:
        all_reminders = con.execute("SELECT id, title, trigger_time, status, repeat_rule FROM reminders_v2").fetchall()
    
    logger.info("Current reminders in database:")
    for r in all_reminders:
        logger.info(f"  #{r['id']} | Title: {r['title']} | Time: {r['trigger_time']} | Status: {r['status']} | Rule: {r['repeat_rule']}")

    # 6. Stop the background worker
    stop_worker()
    logger.info("Verification test completed.")

    # Save verification logs to a markdown file
    with open("reminder_test_results.md", "w") as f:
        f.write("# Reminder Worker Rescheduling Verification Results\n\n")
        f.write(f"Test run timestamp: {datetime.now(IST).isoformat()}\n\n")
        f.write("## Database Entries after 12 seconds:\n")
        for r in all_reminders:
            f.write(f"- **#{r['id']}**: {r['title']} | Time: `{r['trigger_time']}` | Status: `{r['status']}` | Rule: `{r['repeat_rule']}`\n")
        f.write("\n## Fired Events:\n")
        for ev in fired_events:
            f.write(f"- Fired **#{ev['id']}** at trigger time `{ev['trigger_time']}`\n")
        if len(all_reminders) > 1:
            f.write("\n### Result: SUCCESS ✅ (Recurring reminder successfully rescheduled to a new future occurrence)\n")
        else:
            f.write("\n### Result: FAILED ❌ (Recurring reminder was not rescheduled)\n")

if __name__ == "__main__":
    main()
