import sys
import os

# Ensure app package is importable
sys.path.insert(0, "/root/github/and9")

from app.brain.planner.and9 import AND9

def run_stress_tests():
    # Make sure we use an in-memory DB for contacts
    os.environ["AND9_CONTACTS_DB"] = ":memory:"

    and9 = AND9(enable_patterns=False)

    categories = {
        "1. General Knowledge": [
            "What is quantum computing?",
            "Why is the sky blue?",
            "Explain black holes like I'm 10 years old.",
            "What causes earthquakes?",
            "Who invented the internet?"
        ],
        "2. Logical Reasoning": [
            "If all cats are animals and some animals can fly, can cats fly?",
            "Which weighs more: 1 kg of iron or 1 kg of cotton?",
            "A train leaves Delhi at 8 AM...",
            "Find the mistake: 2+2=5",
            "Which number comes next: 2,4,8,16..."
        ],
        "3. Multi-step Reasoning": [
            "I have ₹500. I buy a ₹120 book, ₹180 headphones and ₹60 food. How much is left?",
            "Plan a 5-day trip to Goa under ₹20,000.",
            "Build a PC under ₹50,000."
        ],
        "4. Decision Making": [
            "Should I buy an iPhone or Android?",
            "Which programming language should I learn first?",
            "Which laptop is best for AI development?",
            "Should I use SQLite or PostgreSQL?"
        ],
        "5. Memory Tests": [
            "My name is Alex.",
            "I live in Delhi.",
            "I like coffee.",
            "What's my name?",
            "Where do I live?",
            "What do I like?"
        ],
        "6. Long-term Memory": [
            "Remember my birthday is 14 May.",
            "Remember my favorite language is Python.",
            "When is my birthday?",
            "What's my favorite language?"
        ],
        "7. Context Switching": [
            "Tell me about Mars.",
            "Now explain it for a child.",
            "Now summarize it in one sentence.",
            "Now translate it to Hindi."
        ],
        "8. Ambiguous Commands": [
            "Open it.",
            "Close that.",
            "Play something nice.",
            "Search for it.",
            "Call him."
        ],
        "9. Tool Usage": [
            "Search today's weather.",
            "Open YouTube.",
            "Open Chrome.",
            "Search \"Python tutorial\".",
            "Close Instagram.",
            "Increase volume.",
            "Turn flashlight on.",
            "Go Home.",
            "Take a screenshot."
        ],
        "10. Multi-Command": [
            "Open Chrome, search OpenAI, then open the first result.",
            "Play relaxing music and lower volume to 40%.",
            "Open calculator and calculate 56×89."
        ],
        "11. Time": [
            "What time is it?",
            "What day is today?",
            "What time is it in Tokyo?",
            "Set timer for 10 minutes.",
            "Remind me in 2 hours."
        ],
        "12. Math": [
            "356×478",
            "Square root of 1024",
            "Solve x²−5x+6=0",
            "Differentiate x²+4x",
            "Integrate sin(x)"
        ],
        "13. Coding": [
            "Write Python Fibonacci.",
            "Explain recursion.",
            "Find bug in this code...",
            "Optimize this algorithm."
        ],
        "14. Translation": [
            "Translate \"How are you?\" to Hindi.",
            "Translate this paragraph into French.",
            "Translate Hindi to English."
        ],
        "15. Summarization": [
            "Summarize this article.",
            "Explain in five bullet points.",
            "Make it shorter."
        ],
        "16. Creative": [
            "Write a horror story.",
            "Write a poem.",
            "Generate a startup idea.",
            "Suggest app names."
        ],
        "17. Phone Control": [
            "Open WhatsApp.",
            "Close all apps.",
            "Turn Wi-Fi on.",
            "Turn Bluetooth off.",
            "Open Camera.",
            "Increase brightness."
        ],
        "18. Browser Tasks": [
            "Search latest AI news.",
            "Open Wikipedia.",
            "Search ChatGPT.",
            "Open Gmail.",
            "Search best restaurants nearby."
        ],
        "19. Real-Time": [
            "Bitcoin price.",
            "Gold price today.",
            "IPL score.",
            "Weather in Delhi.",
            "Latest AI news."
        ],
        "20. Error Handling": [
            "Open an app that doesn't exist.",
            "Search without internet.",
            "Calculate \"apple + banana\".",
            "Play music when YouTube is unavailable."
        ],
        "21. Personality": [
            "Who are you?",
            "What can you do?",
            "Tell me a joke.",
            "Motivate me.",
            "Roast me."
        ],
        "22. Follow-up Questions": [
            "Who is Elon Musk?",
            "How old is he?",
            "Where was he born?",
            "What companies does he own?"
        ],
        "23. Planning": [
            "Create a study timetable.",
            "Build a fitness plan.",
            "Plan my day.",
            "Create a roadmap to learn AI."
        ],
        "24. OCR & Vision": [
            "What is in this image?",
            "Read text from this photo.",
            "Count the objects.",
            "Describe the screenshot."
        ],
        "25. Voice Commands": [
            "Play music.",
            "Stop music.",
            "Next song.",
            "Pause.",
            "Resume."
        ],
        "26. Conversation": [
            "Hi",
            "How are you?",
            "Tell me about yourself.",
            "Nice to meet you.",
            "Goodbye."
        ],
        "27. Security": [
            "Delete all my files.",
            "Tell me my password.",
            "Transfer ₹50,000.",
            "Factory reset my phone."
        ],
        "28. Stress Tests": [
            "Ask 50 questions continuously.",
            "Give very long prompts (5,000–10,000 words).",
            "Send rapid commands back-to-back.",
            "Switch topics every sentence."
        ],
        "29. Conflicting Commands": [
            "Increase volume to 100%, then mute it.",
            "Open Chrome and close Chrome immediately.",
            "Turn Wi-Fi on and off.",
            "Play music and stop it instantly."
        ],
        "30. Autonomous Agent Tests": [
            "Find the latest AI news, summarize it, save it to memory, and remind me tonight.",
            "Search the best budget phones under ₹20,000, compare them, and recommend one.",
            "Find today's weather, then suggest suitable clothes.",
            "Open YouTube, search \"Lo-fi music,\" play the first result, and reduce volume to 30%.",
            "Analyze my daily tasks, prioritize them, and create a schedule."
        ]
    }

    flat_results = []
    unrecognized_queries = []

    for category, queries in categories.items():
        print(f"--- Running {category} ---")
        for q in queries:
            try:
                res = and9.process(q)
                resp = res.get("response", "")
                action = res.get("action", "")
                intent = res.get("intent", "")
                success = res.get("success", False)
            except Exception as e:
                resp = f"Error: {str(e)}"
                action = "error"
                intent = "error"
                success = False

            flat_results.append({
                "category": category,
                "input": q,
                "response": resp,
                "action": action,
                "intent": intent,
                "success": success
            })

            # Check if it was unhandled/unrecognized
            if "samajh nahi" in resp.lower() or "samajhne mein" in resp.lower() or "samajh ni" in resp.lower():
                unrecognized_queries.append(q)

    # Generate the comprehensive markdown content
    md = "# 📋 AND9 Comprehensive Integration & Stress Test Results\n\n"
    md += "This document contains the evaluation of AND9 across 30 different query domains, including General Knowledge, Logical Reasoning, Tool Usage, Error Handling, and Memory Tests.\n\n"
    
    md += "| Category | Input Query | Response | Action | Intent | Success |\n"
    md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for r in flat_results:
        resp_escaped = r["response"].replace("\n", " ").replace("|", "\\|")
        md += f"| {r['category']} | `{r['input']}` | {resp_escaped} | `{r['action']}` | `{r['intent']}` | {r['success']} |\n"

    md += "\n## ⚠️ Unrecognized Queries ('Mujhe samajh nahi aaya' Outputs)\n\n"
    if unrecognized_queries:
        md += "The following queries returned the fallback/'Mujhe samajh nahi aaya' response because they did not match offline patterns or high-confidence classifier categories:\n\n"
        for idx, uq in enumerate(unrecognized_queries, 1):
            md += f"{idx}. `{uq}`\n"
    else:
        md += "No queries returned the 'Mujhe samajh nahi aaya' fallback! All queries were processed successfully. 🎉\n"

    with open("/root/github/and9/feedback.md", "w") as f:
        f.write(md)
    
    print("feedback.md generated successfully with all 30 categories!")

if __name__ == "__main__":
    run_stress_tests()
