"""
AND9 — Assistant-Level Action Handlers.

Pure-Python reflex handlers for assistant info, help, system status,
screenshot, lock screen, calculator, jokes, and quotes.
These are fast, deterministic, no-LLM-required actions.
"""
import logging
import random
import re
import math

logger = logging.getLogger(__name__)

# ── Assistant Identity ─────────────────────────────────────────────

_ASSISTANT_IDENTITY = (
    "Main **JARVIS** hoon — aapka personal AI assistant! 🤖\n\n"
    "Mujhe **AND9** ne banaya hai — ek advanced cognitive AI system "
    "jo aapki roj ki tasks mein help karta hai.\n\n"
    "Main Hinglish aur dono languages samajhta hoon, "
    "calls kar sakta hoon, apps khol sakta hoon, "
    "reminders set kar sakta hoon, aur bhi bahut kuch! 🚀\n\n"
    "Kya kar sakte ho? Boliye 'help' ya 'kya kar sakte ho'!"
)

# ── Jokes ──────────────────────────────────────────────────────────

_JOKES = [
    "Teacher: \"Tumne exam mein copy kyun ki?\"\nStudent: \"Sir, aapne kaha tha — "
    "life mein kabhi haar nahi maanani!\" 😂",
    "Doctor: \"Aapko roz 15 minute walk karna chahiye.\"\nPatient: \"But doctor sahab, "
    "main toh bus driver hoon!\" 🚌😂",
    "Santa: \"Maine apne dog ka naam 'Google' rakha hai.\"\nBanta: \"Kyun?\"\n"
    "Santa: \"Kyuki jo bhi pucho, woh *bhonkta* hai!\" 🐶😂",
    "Ek aadmi restaurant mein gaya aur bola: \"Waiter! Khaane mein chhota mota kyun hai?\"\n"
    "Waiter: \"Sir, yeh 'chhota mota' nahi, 'fried rice' hai!\" 🍚😄",
    "Banta: \"Yaar, main bahut pareshan hoon.\"\nSanta: \"Kyun?\"\n"
    "Banta: \"Meri biwi ko har cheez yaad rehti hai!\"\n"
    "Santa: \"Itni badi problem kya hai?\"\n"
    "Banta: \"Problem yeh hai ki woh bhoolti nahi, lekin main yaad nahi rakh paata!\" 😅",
    "Santa ne train mein ticket liya. T.C. aaya aur bola \"Ticket dikhao\".\n"
    "Santa: \"Ticket nahi hai.\"\nT.C.: \"Toh kyun aaye train mein?\"\n"
    "Santa: \"Kyunki gaadi nahi aayi thi!\" 🚂😁",
    "Programming joke:\nThere are 10 types of people in the world — "
    "those who understand binary, and those who don't. 😄💻",
    "Q: What did the AI say to the human?\nA: \"You had me at 'Hello World'!\" 🤖💬",
    "Q: Why did the developer go broke?\nA: Because he used up all his cache! 💳😂",
    "Banta: \"Santa, tumhara phone toh bahut smart hai! Kya karta hai?\"\n"
    "Santa: \"Mera phone mujhe batata hai ki main kahan hoon.\"\n"
    "Banta: \"Achha? Kaise?\"\n"
    "Santa: \"Jab main ghar se nikalta hoon toh phone bolta hai — "
    "'Aap apni chabhi bhool gaye!'\" 🔑😄",
]

# ── Motivational Quotes ───────────────────────────────────────────

_QUOTES = [
    "💪 \"Safalta ka raasta asaan nahi hota, lekin har kadam aapko "
    "apne target ke kareeb le jaata hai.\" — AND9",
    "🌟 \"Jab tak aap try karte rahenge, haar nahi maan sakte. "
    "Kyunki har galati ek nayi seekh hai!\"",
    "🚀 \"Badle se mat daro. Chhoti chhoti aadatien badlo, "
    "aur dekho zindagi kaise badalti hai!\"",
    "🎯 \"Goal clear ho toh raasta khud ban jaata hai. "
    "Bas pehla kadam uthao!\"",
    "💡 \"Kal se better aaj ho, aur aaj se better kal. "
    "Yahi hai growth ka formula!\"",
    "✨ \"The only way to do great work is to love what you do. "
    "— Steve Jobs\"",
    "🔥 \"Believe you can and you're halfway there. — Theodore Roosevelt\"",
    "🌄 \"Har subah ek naya mauka hota hai. utho, muskurao, aur shuru karo!\"",
    "⚡ \"Aap usse kahin zyada capable hain jo aap sochte hain. "
    "Bas khud par bharosa rakhiye!\"",
    "🌈 \"Zindagi mein kuch bada karna hai toh risk lena seekho. "
    "Safe khelne walon ne kabhi kuch bada nahi kiya!\"",
]


# ── Handler Functions ──────────────────────────────────────────────


def execute_assistant_info() -> dict:
    """Return assistant identity information.

    Returns:
        {"response": str, "action": str, "payload": dict}
    """
    return {
        "response": _ASSISTANT_IDENTITY,
        "action": "ASSISTANT_INFO",
        "payload": {},
    }


def execute_help() -> dict:
    """Return a formatted list of all capabilities.

    Returns:
        {"response": str, "action": str, "payload": dict}
    """
    help_text = (
        "✨ **Main kya kar sakta hoon?** ✨\n\n"
        "📞 **Calls & Contacts** — Call karo, contact add/delete/search karo\n"
        "💬 **Messages & SMS** — Message bhejo\n"
        "📱 **Apps & Device** — Apps kholo, camera, flashlight, volume, WiFi\n"
        "⏰ **Time & Alarms** — Alarm, timer, reminder set karo\n"
        "▶️ **Media** — YouTube search/play, music\n"
        "📋 **Info** — Time batao, weather, news\n"
        "🧮 **Calculator** — Calculate karo (5+3, 10*20)\n"
        "😄 **Jokes & Quotes** — Joke sunao, motivation do\n"
        "📸 **Screenshot & Lock** — Screenshot lo, phone lock karo\n"
        "📊 **System Status** — Battery, network, device info check karo\n\n"
        "Bas boliye! Main ready hoon! 🚀"
    )
    return {
        "response": help_text,
        "action": "HELP",
        "payload": {},
    }


def execute_system_status() -> dict:
    """Check and return device system status (battery, uptime, network).

    Returns:
        {"response": str, "action": str, "payload": dict}
    """
    # This sends an intent to the Android client to fetch real status.
    # The response here is the trigger; the Android side fills in the data.
    return {
        "response": "System status check kar raha hoon... 📊",
        "action": "SYSTEM_STATUS",
        "payload": {
            "action": "AND9_INTERNAL",
            "command": "system_status",
        },
    }


def execute_screenshot() -> dict:
    """Trigger a screenshot via Android accessibility service.

    Returns:
        {"response": str, "action": str, "payload": dict}
    """
    return {
        "response": "Screenshot le raha hoon... 📸",
        "action": "SCREENSHOT",
        "payload": {
            "action": "AND9_INTERNAL",
            "command": "take_screenshot",
        },
    }


def execute_lock_screen() -> dict:
    """Lock the device screen via Android device admin.

    Returns:
        {"response": str, "action": str, "payload": dict}
    """
    return {
        "response": "Phone lock kar raha hoon... 🔒",
        "action": "LOCK_SCREEN",
        "payload": {
            "action": "AND9_INTERNAL",
            "command": "lock_screen",
        },
    }


def execute_calculator(expression: str = "") -> dict:
    """Evaluate a mathematical expression inline.

    Args:
        expression: Math expression string (e.g., "5 + 3 * 2").

    Returns:
        {"response": str, "action": str, "payload": dict, "metadata": dict}
    """
    if not expression or not expression.strip():
        return {
            "response": "Kya calculate karna hai? Kuch expression batao, jaise '5 + 3' 🧮",
            "action": "CALCULATOR",
            "payload": {},
        }

    # Clean the expression
    expr = expression.strip()

    # Replace common words/patterns
    replacements = {
        "plus": "+", "minus": "-", "multiply by": "*", "times": "*",
        "divided by": "/", "into": "*", "x": "*", "X": "*",
        "square of": "**2", "cube of": "**3",
        "percent of": "/100*", "percentage": "/100*",
    }
    for old, new in replacements.items():
        expr = expr.replace(old, new)

    # Handle "square root of X" or "sqrt of X" → sqrt(X)
    sqrt_m = re.search(r'(?:square\s*root\s*of|sqrt\s*of)\s*(\d+(?:\.\d+)?)', expr, re.IGNORECASE)
    if sqrt_m:
        num = float(sqrt_m.group(1))
        try:
            result = math.sqrt(num)
            return {
                "response": f"√{num} = **{result:.4f}** 🧮",
                "action": "CALCULATOR",
                "payload": {},
                "metadata": {"expression": expression, "result": result},
            }
        except (ValueError, OverflowError):
            pass
        # Replace for the fallback eval
        expr = f"sqrt({num})"

    # Remove all whitespace for evaluation
    expr = re.sub(r'\s+', '', expr)

    # Security: only allow safe math characters
    allowed = set("0123456789+-*/.()%sqrt")
    if not all(c in allowed for c in expr):
        return {
            "response": f"Mujhe yeh expression samajh nahi aaya: '{expression}'. "
                        "Kripya simple digits aur operators use karein (+ - * /). 🧮",
            "action": "CALCULATOR",
            "payload": {},
        }

    # Handle sqrt
    sqrt_match = re.search(r'sqrt\((\d+(?:\.\d+)?)\)', expr)
    if sqrt_match:
        num = float(sqrt_match.group(1))
        try:
            result = math.sqrt(num)
            return {
                "response": f"√{num} = **{result:.4f}** 🧮",
                "action": "CALCULATOR",
                "payload": {},
                "metadata": {"expression": expression, "result": result},
            }
        except (ValueError, OverflowError):
            pass

    try:
        # Safe eval using restricted globals
        result = eval(expr, {"__builtins__": {}}, {"sqrt": math.sqrt})
        if isinstance(result, float) and result == int(result):
            result = int(result)
        return {
            "response": f"**{expression}** = **{result}** 🧮",
            "action": "CALCULATOR",
            "payload": {},
            "metadata": {"expression": expression, "result": result},
        }
    except ZeroDivisionError:
        return {
            "response": "Kisi number ko zero se divide nahi kar sakte! 😅",
            "action": "CALCULATOR",
            "payload": {},
        }
    except (SyntaxError, NameError, TypeError, ValueError) as e:
        logger.debug("Calculator eval failed for '%s': %s", expression, e)
        return {
            "response": f"Expression '{expression}' ko evaluate nahi kar paaya. "
                        "Kripya sahi expression likhein. 🧮",
            "action": "CALCULATOR",
            "payload": {},
        }


def execute_joke() -> dict:
    """Return a random joke from the predefined collection.

    Returns:
        {"response": str, "action": str, "payload": dict}
    """
    joke = random.choice(_JOKES)
    return {
        "response": f"😂 **Yeh lo ek joke:**\n\n{joke}",
        "action": "JOKE",
        "payload": {},
    }


def execute_quote() -> dict:
    """Return a random motivational quote.

    Returns:
        {"response": str, "action": str, "payload": dict}
    """
    quote = random.choice(_QUOTES)
    return {
        "response": f"🌟 {quote}",
        "action": "QUOTE",
        "payload": {},
    }
