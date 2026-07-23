"""
AND9 — Centralized Command Dictionary (Phase 2).

Single source of truth for ALL command patterns.
No regex lives in multiple files. Every intent's patterns
are defined once here and imported wherever needed.

Priority order matches AND9 cognitive architecture:
    EMERGENCY → CALL → MESSAGE → OPEN_APP → CAMERA →
    FLASHLIGHT → BLUETOOTH → WIFI → VOLUME → YOUTUBE →
    MUSIC → ALARM → REMINDER → TIMER → SEARCH → CHAT
"""
import re
from typing import List, Pattern


# ── Helper ────────────────────────────────────────────────────────
def _c(pattern: str, flags: int = re.IGNORECASE) -> Pattern:
    """Compile a regex pattern with IGNORECASE by default."""
    return re.compile(pattern, flags)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 1 — EMERGENCY
# ══════════════════════════════════════════════════════════════════
EMERGENCY: List[Pattern] = [
    _c(r'\b(emergency|help|bachao|danger|accident|sos|911|112)\b'),
]


# ══════════════════════════════════════════════════════════════════
# PRIORITY 2 — CALL
# ══════════════════════════════════════════════════════════════════

# Pattern → group(1) = contact name
CALL_CONTACT: List[Pattern] = [
    # "call mummy" / "call amit kumar"
    _c(r'^call\s+(.+)$'),
    # "mummy ko call karo" / "amit ko call karo"
    _c(r'^(.+?)\s+ko\s+call\s+karo$'),
    # "phone lagao mummy" / "phone lagao papa"
    _c(r'^phone\s+lagao\s+(.+)$'),
    # "mummy ko phone lagao"
    _c(r'^(.+?)\s+ko\s+phone\s+lagao$'),
    # "dial mummy"
    _c(r'^dial\s+(?!\+?\d)(.+)$'),
    # "phone mummy" (short form)
    _c(r'^phone\s+(?!\+?\d)(.+)$'),
    # "mummy ko call kar"
    _c(r'^(.+?)\s+ko\s+call\s+kar$'),
    # "mummy se baat karo"
    _c(r'^(.+?)\s+se\s+baat\s+karo$'),
    # "mummy ko call lagao"
    _c(r'^(.+?)\s+ko\s+call\s+lagao$'),
]

# Pattern → group(1) = phone number
CALL_NUMBER: List[Pattern] = [
    _c(r'^call\s+(\+?\d[\d\s\-()\+]{6,18})$'),
    _c(r'^dial\s+(\+?\d[\d\s\-()\+]{6,18})$'),
    _c(r'^phone\s+(\+?\d[\d\s\-()\+]{6,18})$'),
]

# Direct number pattern (used to detect if target is a number)
IS_PHONE_NUMBER: Pattern = _c(r'^\+?\d[\d\s\-()\+]{6,18}$')


# ══════════════════════════════════════════════════════════════════
# PRIORITY 3 — MESSAGE / SMS
# ══════════════════════════════════════════════════════════════════

MESSAGE: List[Pattern] = [
    _c(r'\b(message|msg|sms|text)\b'),
]

# "message mummy hello"  → group(1)=contact, group(2)=text
MESSAGE_WITH_CONTACT: Pattern = _c(
    r'(?:message|msg|sms|text)\s+(.+?)(?:\s+(?:saying|that|ki|ke baare mein)\s+(.+))?$'
)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 4 — OPEN APP
# ══════════════════════════════════════════════════════════════════

# Specific known apps (for fast-path matching)
OPEN_APP_SPECIFIC: List[Pattern] = [
    # youtube
    _c(r'\b(youtube|yt|ytb)\b'),
    # whatsapp
    _c(r'\b(whatsapp|wa|wp)\b'),
    # telegram
    _c(r'\b(telegram|tg|tele)\b'),
    # instagram
    _c(r'\b(instagram|insta|ig)\b'),
    # chrome
    _c(r'\bchrome\b'),
    # camera (also Priority 5, handled there)
    _c(r'\bcamera\b'),
    # gallery
    _c(r'\bgallery\b'),
    # settings
    _c(r'\b(settings|setting)\b'),
    # calculator
    _c(r'\b(calculator|calc|calci)\b'),
    # maps
    _c(r'\b(maps|google\s*maps)\b'),
    # gmail / mail
    _c(r'\b(gmail|mail)\b'),
    # contacts
    _c(r'\bcontacts\b'),
    # phone / dialer
    _c(r'\b(phone|dialer)\b'),
    # spotify
    _c(r'\bspotify\b'),
    # facebook
    _c(r'\b(facebook|fb)\b'),
    # snapchat
    _c(r'\b(snapchat|snap)\b'),
    # twitter / x
    _c(r'\b(twitter|twit)\b'),
]

# Generic open patterns → group(1) = app name
OPEN_APP_GENERIC: List[Pattern] = [
    # "open youtube" / "open whatsapp app"
    _c(r'\bopen\s+(.+?)(?:\s+app)?\s*$'),
    # "launch youtube"
    _c(r'\blaunch\s+(.+?)(?:\s+app)?\s*$'),
    # "start youtube"
    _c(r'\bstart\s+(.+?)(?:\s+app)?\s*$'),
    # "youtube kholo" / "whatsapp open karo"
    _c(r'^(.+?)\s+(?:kholo|open\s+karo|chalao|launch\s+karo|start\s+karo|chalu\s+karo)\s*$'),
    # "kholo youtube"
    _c(r'^(?:kholo|chalao)\s+(.+)$'),
]

# Trigger keywords for open intent
OPEN_APP_TRIGGERS: Pattern = _c(
    r'\b(open|launch|start|kholo|chalao|open\s+karo|launch\s+karo|chalu\s+karo)\b'
)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 5 — CAMERA
# ══════════════════════════════════════════════════════════════════

CAMERA: List[Pattern] = [
    _c(r'\b(camera|photo|selfie|picture|pic)\b'),
    _c(r'\bphoto\s+(click|lo|khicho)\b'),
]


# ══════════════════════════════════════════════════════════════════
# PRIORITY 6 — FLASHLIGHT
# ══════════════════════════════════════════════════════════════════

FLASHLIGHT: Pattern = _c(r'\b(flashlight|torch|flash)\b')
FLASHLIGHT_ON: Pattern = _c(r'\b(on|enable|chalu|켜|켜줘)\b')
FLASHLIGHT_OFF: Pattern = _c(r'\b(off|disable|band|bnd|बंद)\b')


# ══════════════════════════════════════════════════════════════════
# PRIORITY 7 — BLUETOOTH
# ══════════════════════════════════════════════════════════════════

BLUETOOTH: Pattern = _c(r'\bbluetooth\b')
BLUETOOTH_SCAN: Pattern = _c(r'\b(scan|discover|search|dhundho|find|nearby)\b')
BLUETOOTH_PAIRED: Pattern = _c(r'\b(paired|paired devices|saved|bonded|list|showing|dikhao|dikha)\b')
TOGGLE_ON: Pattern = _c(r'\b(on|enable|chalu|start|kholo)\b')
TOGGLE_OFF: Pattern = _c(r'\b(off|disable|band|bnd|stop|band\s+karo)\b')


# ══════════════════════════════════════════════════════════════════
# PRIORITY 8 — WIFI
# ══════════════════════════════════════════════════════════════════

WIFI: Pattern = _c(r'\b(wifi|wi-fi|wlan|internet)\b')


# ══════════════════════════════════════════════════════════════════
# PRIORITY 9 — VOLUME
# ══════════════════════════════════════════════════════════════════

VOLUME: Pattern = _c(r'\b(volume|mute|unmute|silent|awaz|awaaz)\b')
VOLUME_UP: Pattern = _c(r'\b(up|badhao|increase|louder|higher|zyada)\b')
VOLUME_DOWN: Pattern = _c(r'\b(down|kam|decrease|lower|less|ghata)\b')
VOLUME_MUTE: Pattern = _c(r'\b(mute|silent|chup)\b')
VOLUME_MAX: Pattern = _c(r'\b(max|maximum|full|poora)\b')

# "volume up" / "increase volume" / "volume badhao"
VOLUME_UP_FULL: Pattern = _c(
    r'\b(volume\s+up|increase\s+volume|volume\s+badhao|awaz\s+badhao|louder)\b'
)
VOLUME_DOWN_FULL: Pattern = _c(
    r'\b(volume\s+down|decrease\s+volume|volume\s+kam\s+karo|awaz\s+kam\s+karo|lower\s+volume)\b'
)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 10 — YOUTUBE
# ══════════════════════════════════════════════════════════════════

YOUTUBE_TRIGGER: Pattern = _c(r'\byoutube\b')

# YouTube search patterns → group(1) = search query
YOUTUBE_SEARCH_PATTERNS: List[Pattern] = [
    # "youtube search song_name"
    _c(r'\byoutube\s+search\s+(.+)$'),
    # "search song_name on youtube"
    _c(r'\bsearch\s+(.+?)\s+on\s+youtube\b'),
    # "youtube pe search karo song_name"
    _c(r'\byoutube\s+pe\s+search\s+karo\s+(.+)$'),
    # "youtube par search karo song_name"
    _c(r'\byoutube\s+par\s+search\s+karo\s+(.+)$'),
    # "youtube pe video search karo song_name"
    _c(r'\byoutube\s+pe\s+video\s+search\s+karo\s+(.+)$'),
    # "youtube pe song search karo song_name"
    _c(r'\byoutube\s+pe\s+song\s+search\s+karo\s+(.+)$'),
    # "song_name youtube pe search karo"
    _c(r'^(.+?)\s+youtube\s+pe\s+search\s+karo\b'),
    # "youtube kholo aur search karo song_name"
    _c(r'\byoutube\s+(?:kholo|open\s+karo)\s+aur\s+search\s+karo\s+(.+)$'),
]

# YouTube play (music) patterns → group(1) = song/video name
YOUTUBE_PLAY_PATTERNS: List[Pattern] = [
    # "play song_name"
    _c(r'^play\s+(.+)$'),
    # "song bajao" / "gaana chalao" / "music sunao"
    _c(r'^(.+?)\s+(?:bajao|chalao|sunao|play\s+karo)\s*$'),
    # "play youtube video/song"
    _c(r'\bplay\s+youtube\s+(?:video|song|music)\s*(.*)$'),
    # "play song_name on youtube"
    _c(r'\bplay\s+(.+?)\s+on\s+youtube\b'),
    # "song_name youtube pe bajao"
    _c(r'^(.+?)\s+youtube\s+pe\s+(?:bajao|chalao|sunao)\b'),
]

# Indicates a YouTube play (not just open) intent
YOUTUBE_PLAY_TRIGGER: Pattern = _c(
    r'\b(play|bajao|sunao|chalao|song|music|gaana|gana|geet|track)\b'
)

# "youtube kholo" / "youtube open karo" — just open, no query
YOUTUBE_OPEN_ONLY: Pattern = _c(
    r'^youtube\s+(?:kholo|open\s+karo|chalao|launch|start)\s*$'
)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 11 — MUSIC
# ══════════════════════════════════════════════════════════════════

MUSIC_TRIGGER: Pattern = _c(
    r'\b(song|music|gaana|gana|geet|playlist|track|bhajan|ghazal|album)\b'
)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 12 — ALARM
# ══════════════════════════════════════════════════════════════════

ALARM_TRIGGER: Pattern = _c(r'\balarm\b')

# All alarm command forms
ALARM_PATTERNS: List[Pattern] = [
    # "set alarm" / "alarm lagao" / "alarm laga do"
    _c(r'\b(?:set\s+alarm|alarm\s+lagao|alarm\s+laga\s+do|alarm\s+set\s+karo)\b'),
    # "set alarm for 7 am"
    _c(r'\bset\s+alarm\s+(?:for\s+)?(.+)$'),
    # "alarm after 5 minutes"
    _c(r'\balarm\s+(?:after|baad)\s+(.+)$'),
    # "7 baje alarm lagao" / "7 am alarm lagao"
    _c(r'^(\d{1,2}(?::\d{2})?\s*(?:am|pm|baje)?)\s+alarm'),
    # "kal subah 7 baje alarm lagao"
    _c(r'\b(kal\s+subah|aaj\s+raat|tomorrow|today)\s+(.+?)\s+alarm\b'),
]


# ══════════════════════════════════════════════════════════════════
# PRIORITY 13 — REMINDER
# ══════════════════════════════════════════════════════════════════

REMINDER_TRIGGER: Pattern = _c(r'\b(remind|reminder|yaad\s+dila|yaad\s+dilana)\b')

REMINDER_PATTERNS: List[Pattern] = [
    # "remind me after 5 minutes"
    _c(r'\bremind\s+me\s+(?:after|in)\s+(.+)$'),
    # "5 minute baad yaad dilana"
    _c(r'^(.+?)\s+(?:baad|ke\s+baad)\s+yaad\s+dila(?:na)?\b'),
    # "set reminder at 7pm"
    _c(r'\bset\s+reminder\s+(?:at|for)?\s*(.+)$'),
    # "reminder lagao 5 minute ke baad"
    _c(r'\breminder\s+lagao\s+(.+)$'),
]


# ══════════════════════════════════════════════════════════════════
# PRIORITY 14 — TIMER
# ══════════════════════════════════════════════════════════════════

TIMER_TRIGGER: Pattern = _c(r'\btimer\b')

TIMER_PATTERNS: List[Pattern] = [
    # "5 second timer" / "1 minute timer" / "2 hour timer"
    _c(r'^(\d+(?:\.\d+)?)\s*(second|sec|s|minute|min|m|hour|hr|h)s?\s+timer$'),
    # "timer lagao 5 minute" / "set timer 5 minutes"
    _c(r'\b(?:set\s+)?timer\s+(?:lagao\s+)?(?:for\s+)?(.+)$'),
    # "timer for 5 minutes"
    _c(r'\btimer\s+(?:of\s+|for\s+)(.+)$'),
]


# ══════════════════════════════════════════════════════════════════
# PRIORITY 15 — GOAL
# ══════════════════════════════════════════════════════════════════

GOAL_TRIGGER: Pattern = _c(r'\b(goal|target|lakshya|aim|objective)\b')


# ══════════════════════════════════════════════════════════════════
# PRIORITY 16 — AUTOMATION
# ══════════════════════════════════════════════════════════════════

AUTOMATION_TRIGGER: Pattern = _c(
    r'\b(automate|automation|routine|har\s+roz|daily|schedule\s+karo)\b'
)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 17 — SEARCH  (always last for device actions)
# ══════════════════════════════════════════════════════════════════

SEARCH_TRIGGER: Pattern = _c(
    r'\b(search|find|google|look\s+up|weather|news|latest|kya\s+hai|'
    r'ke\s+baare\s+mein|batao|dhundo|dhundho|khojo|talaash)\b'
)

# Chrome-allowed actions — ONLY these may open Chrome
CHROME_ALLOWED_INTENTS = frozenset({
    "search",
    "news",
    "web_lookup",
})


# ══════════════════════════════════════════════════════════════════
# PRIORITY 18 — CHAT (default fallback)
# ══════════════════════════════════════════════════════════════════

CHAT_TRIGGERS: List[Pattern] = [
    _c(r'\b(hello|hi|hey|hola|namaste|namaskar)\b'),
    _c(r'\b(kaise\s+ho|kya\s+haal|kaisa\s+chal|how\s+are\s+you)\b'),
    _c(r'\b(kya\s+kar\s+rahe|what\'s\s+up|sup)\b'),
]


# ══════════════════════════════════════════════════════════════════
# HOME SCREEN
# ══════════════════════════════════════════════════════════════════

GO_HOME: Pattern = _c(
    r'\b(go\s+home|home\s+jao|home\s+screen|sab\s+apps\s+band\s+karo)\b'
)


# ══════════════════════════════════════════════════════════════════
# AIRPLANE MODE
# ══════════════════════════════════════════════════════════════════

AIRPLANE_MODE: Pattern = _c(r'\b(airplane\s*mode|flight\s*mode|aeroplane\s*mode)\b')


# ══════════════════════════════════════════════════════════════════
# ACCESSIBILITY INTENTS (between Automation and Search)
# ══════════════════════════════════════════════════════════════════

# "screen pe kya hai" / "describe the screen" / "what is on screen"
ACCESSIBILITY_SCREEN_DESCRIBE: Pattern = _c(
    r'\b(describe\s+\w*\s*screen|screen\s+describe|screen\s+pe\s+kya\s+hai|'
    r'what.*on\s+(the\s+)?screen|screen\s+dikhao|kya\s+dikh\s+raha|'
    r'current\s+screen|batao\s+screen|screen\s+batao)\b'
)

# "click X" / "tap X" / "press X" / "X dabao"
ACCESSIBILITY_CLICK_ELEMENT: Pattern = _c(
    r'\b(click|tap|press|dabao|click\s+karo|tap\s+karo|'
    r'press\s+karo|daba\s+do|click\s+kar)\b'
)

# "type X" / "write X" / "enter X" / "X likho"
ACCESSIBILITY_TYPE_TEXT: Pattern = _c(
    r'\b(type|write|enter|likho|type\s+karo|daalo|'
    r'input|text\s+daalo|type\s+kar)\b'
)

# "scroll up/down" / "swipe" / "upar jao" / "neeche jao"
ACCESSIBILITY_SCROLL: Pattern = _c(
    r'\b(scroll|swipe|upar|neeche|niche|scroll\s+karo|'
    r'swipe\s+karo|page\s+up|page\s+down)\b'
)

ACCESSIBILITY_LIST_ELEMENTS: Pattern = _c(
    r'\b(list|buttons|options|menu|kya\s+kuch\s+hai|'
    r'saare\s+options|dikhao\s+buttons|show.*buttons|'
    r'list.*elements|list.*options)\b'
)

ACCESSIBILITY_CURRENT_APP: Pattern = _c(
    r'\b(current\s+app|kaunsi\s+app|kon\s+sa\s+app|'
    r'foreground\s+app|kya\s+app\s+khula|kaun\s+si\s+app)\b'
)


# ══════════════════════════════════════════════════════════════════
# UTILITY — Noise Words for Entity Cleaning
# ══════════════════════════════════════════════════════════════════

# Action verbs to strip when extracting entity names
ACTION_NOISE_WORDS = [
    "open", "launch", "start", "kholo", "chalao", "open karo",
    "launch karo", "start karo", "chalu karo",
    "call", "dial", "phone", "phone lagao", "call karo", "call lagao",
    "search", "find", "google", "search karo", "dhundo",
    "play", "bajao", "sunao", "play karo", "laga do",
    "set alarm", "alarm lagao", "alarm laga do",
    "set reminder", "reminder lagao", "yaad dilana",
    "set timer", "timer lagao",
    "remind me to", "remind me about", "remind me for", "remind me",
]

# Time noise words to strip when extracting labels/entities
TIME_NOISE_WORDS = [
    "minute", "minutes", "second", "seconds", "hour", "hours",
    "sec", "min", "hr", "hrs", "ghanta", "ghante",
    "baad", "ke baad", "me", "ke", "ka", "ki", "ko", "se",
    "par", "pe", "after", "in", "for", "at",
    "baje", "bajkar", "am", "pm",
]
