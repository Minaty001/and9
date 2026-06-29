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
    _c(r'\b(emergency|bachao|danger|accident|sos|911|112)\b'),
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
    # "phone mummy" (short form) — but NOT "phone lock karo" / "phone screen" / "phone band"
    _c(r'^phone\s+(?!(?:lock|screen|band)\b)(?!\+?\d)(.+)$'),
    # "mummy ko call kar"
    _c(r'^(.+?)\s+ko\s+call\s+kar$'),
    # "mummy se baat karo"
    _c(r'^(.+?)\s+se\s+baat\s+karo$'),
    # "mummy ko call lagao"
    _c(r'^(.+?)\s+ko\s+call\s+lagao$'),
    # "mummy ko dial karo"
    _c(r'^(.+?)\s+ko\s+dial\s+karo$'),
    # "call karo mummy"
    _c(r'^call\s+karo\s+(.+)$'),
    # "mummy call" / "papa call"
    _c(r'^(.+?)\s+call$'),
    # "make a call to mummy"
    _c(r'^make\s+a\s+call\s+to\s+(.+)$'),
    # "give a call to mummy"
    _c(r'^give\s+a\s+call\s+to\s+(.+)$'),
    # "call to mummy"
    _c(r'^call\s+to\s+(.+)$'),
    # "mummy se baat karani hai"
    _c(r'^(.+?)\s+se\s+baat\s+karani\s+hai$'),
    # "mummy se baat karna hai"
    _c(r'^(.+?)\s+se\s+baat\s+karna\s+hai$'),
    # "mummy ko phone karo"
    _c(r'^(.+?)\s+ko\s+phone\s+karo$'),
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

# ── Reminder Management Triggers (Phase G) ─────────────────────────

# List reminders
LIST_REMINDERS_TRIGGER: Pattern = _c(
    r'\b(?:reminder\s+dikha|reminder\s+list|reminder\s+show|show\s+reminders?'
    r'|reminder\s+dikhau|reminder\s+bata|kaunse\s+reminders?\s+hain'
    r'|list\s+reminders?|active\s+reminders?|saare\s+reminders?)\b'
)

# Delete reminder
DELETE_REMINDER_TRIGGER: Pattern = _c(
    r'\b(?:cancel\s+reminder|delete\s+reminder|remove\s+reminder|hatana?|hata\s+do|delete\s+kar|cancel\s+kar)'
    r'(?:\s+.*?)?\b(?:reminder\s+)?#?(\d+)\b'
)

# Pause reminder
PAUSE_REMINDER_TRIGGER: Pattern = _c(
    r'\b(?:pause\s+reminder|reminder\s+pause|rok\s+do|thoda\s+rok|pause\s+kar)'
    r'(?:\s+.*?)?\b#?(\d+)\b'
)

# Resume reminder
RESUME_REMINDER_TRIGGER: Pattern = _c(
    r'\b(?:resume\s+reminder|reminder\s+resume|phir\s+se\s+shuru|jari\s+rakh|resume\s+kar)'
    r'(?:\s+.*?)?\b#?(\d+)\b'
)

# Snooze reminder
SNOOZE_REMINDER_TRIGGER: Pattern = _c(
    r'\b(?:snooze|thodi\s+der\s+baad|baad\s+me|thoda\s+baad)'
    r'(?:\s+.*?)?\b(?:reminder\s+)?#?(\d+)?\b'
    r'.*?(\d+)\s*(?:minute|min|m|minute\s+ke\s+liye)?'
)

# Clear all reminders
CLEAR_ALL_REMINDERS_TRIGGER: Pattern = _c(
    r'\b(?:clear\s+all\s+reminders?|saare\s+reminders?\s+hata|sab\s+reminders?\s+delete'
    r'|sab\s+hata\s+do|clear\s+kar\s+do|remove\s+all|delete\s+all\s+reminders?)\b'
)

# Show completed reminders
SHOW_COMPLETED_REMINDERS_TRIGGER: Pattern = _c(
    r'\b(?:completed\s+reminders?|fired\s+reminders?|purane\s+reminders?'
    r'|completed\s+dikha|kya\s+yaad\s+dilaya|reminders?\s+jo\s+baj\s+chuke)\b'
)


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
# PRIORITY 15 — TIME (generic, after city_time check)
# ══════════════════════════════════════════════════════════════════

TIME_TRIGGER: Pattern = _c(
    r'\b(time|samay|baje|kitne\s+baje|kya\s+time|'
    r'ka\s+samay|ghanti|time\s+batao|time\s+kiya)\b'
)


# ══════════════════════════════════════════════════════════════════
# PRIORITY 16 — GOAL
# ══════════════════════════════════════════════════════════════════

GOAL_TRIGGER: Pattern = _c(r'\b(goal|target|lakshya|aim|objective)\b')


# ══════════════════════════════════════════════════════════════════
# PRIORITY 16 — AUTOMATION
# ══════════════════════════════════════════════════════════════════

AUTOMATION_TRIGGER: Pattern = _c(
    r'\b(automate|automation|routine|har\s+roz|daily|schedule\s+karo)\b'
)


# ══════════════════════════════════════════════════════════════════
# ASSISTANT INFO (between AUTOMATION and SEARCH)
# ══════════════════════════════════════════════════════════════════

ASSISTANT_INFO: List[Pattern] = [
    _c(r'\b(who are you|what is your name|your name|kaun ho tum|'
       r'tera naam kya hai|tum kaun ho|aap kaun hain)\b'),
    _c(r'\b(who made you|who created you|tumhe kisne banaya|'
       r'aapko kisne banaya|creator|banane wala)\b'),
    _c(r'\b(your version|version|tumhara version)\b'),
    _c(r'\b(about you|about jarvis|jarvis ke baare mein|'
       r'tumhare baare mein|aapke baare mein)\b'),
    _c(r'\b(introduce yourself|apna parichay do)\b'),
]


# ══════════════════════════════════════════════════════════════════
# HELP / COMMANDS
# ══════════════════════════════════════════════════════════════════

HELP: List[Pattern] = [
    _c(r'^(help|help me|guide|guide me)\s*$'),
    _c(r'\b(what can you do|what all can you do|kya kar sakte ho|'
       r'aap kya kar sakte hain|tum kya kar sakte ho)\b'),
    _c(r'\b(commands|capabilities|features|skills|tumhari khamiyat)\b'),
    _c(r'\b(show commands|list commands|help dikhao)\b'),
    _c(r'\b(kaise use karein|how to use)\b'),
]


# ══════════════════════════════════════════════════════════════════
# SYSTEM STATUS / DEVICE INFO
# ══════════════════════════════════════════════════════════════════

SYSTEM_STATUS: List[Pattern] = [
    _c(r'\b(battery status|battery batao|battery check|battery level|'
       r'battery percent|battery kitna hai|charge kitna hai)\b'),
    _c(r'\b(network status|network check|network batao|'
       r'mobile network|signal check|internet status)\b'),
    _c(r'\b(phone status|phone ki halat|device info|device status|'
       r'system info|system status|mobile info)\b'),
    _c(r'\b(uptime|phone uptime|device uptime|kitne der se on hai)\b'),
]


# ══════════════════════════════════════════════════════════════════
# SCREENSHOT
# ══════════════════════════════════════════════════════════════════

SCREENSHOT: List[Pattern] = [
    _c(r'\b(take screenshot|screenshot lo|screenshot karo|'
       r'screenshot le|screenshot le lo|screenshot lena hai)\b'),
    _c(r'\b(screen capture|capture screen|screen shot)\b'),
    _c(r'\b(screenshot banao|screenshot khicho)\b'),
]


# ══════════════════════════════════════════════════════════════════
# LOCK SCREEN
# ══════════════════════════════════════════════════════════════════

LOCK_SCREEN: List[Pattern] = [
    _c(r'\b(lock phone|lock screen|phone lock karo|'
       r'screen lock karo|lock karo|phone band karo)\b'),
    _c(r'\b(device lock|screen ko lock karo|tal laga do|taala laga do)\b'),
]


# ══════════════════════════════════════════════════════════════════
# CALCULATOR / MATH
# ══════════════════════════════════════════════════════════════════

CALCULATOR: List[Pattern] = [
    _c(r'\b(calculate|calculation|calculator|compute|evaluate)\b'),
    _c(r'\b(what is|what\'s)\s+\d+.+\d+'),  # "what is 5+3" / "what's 5*10"
    _c(r'\b(kitna hoga|kitna hota hai|kaise nikale)\s+\d+'),
    _c(r'\b(plus|minus|multiply|divide|into|subtract|add|product|sum)\b'),
    _c(r'\b(square root|sqrt|cube root|cube|power|mod|percentage)\b'),
    _c(r'^[\d\s\+\-\*\/\(\)\%\.]+$'),  # pure math expression like "5+3*2"
]


# ══════════════════════════════════════════════════════════════════
# JOKE
# ══════════════════════════════════════════════════════════════════

JOKE: List[Pattern] = [
    _c(r'\b(tell me a joke|tell a joke|joke sunao|ek joke sunao|'
       r'joke batao|kuch hasi ka kaam karo|hasao)\b'),
    _c(r'\b(funny|make me laugh|joke do|joke kaho|kuch funny batao)\b'),
    _c(r'\b(chutkula sunao|laugh|ha ha|hansao|mujhe hansao)\b'),
]


# ══════════════════════════════════════════════════════════════════
# QUOTE / MOTIVATION
# ══════════════════════════════════════════════════════════════════

QUOTE: List[Pattern] = [
    _c(r'\b(motivate me|motivation do|inspire me|inspiration do|'
       r'kuch inspirational batao|kuch motivational batao)\b'),
    _c(r'\b(quote batao|ek quote batao|quote do|quote sunao|'
       r'motivational quote|inspirational quote)\b'),
    _c(r'\b(prerit karo|protsahan do|himmat do|dil dhadakne do|'
       r'positive energy|sukoon)\b'),
]

# ══════════════════════════════════════════════════════════════════
# CALCULATOR EXPRESSION — extract math expression (catch-all for calculations)
# ══════════════════════════════════════════════════════════════════

CALC_EXPRESSION: Pattern = _c(
    r'(?:calculate|what is|what\'s|kitna hoga|kitna hota hai)\s+(.+)$|^([\d\s\+\-\*\/\(\)\%\.]+)$'
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
# CONTACTS MANAGEMENT
# ══════════════════════════════════════════════════════════════════

# List all contacts
LIST_CONTACTS: List[Pattern] = [
    _c(r'\b(list\s+contacts|show\s+contacts|show\s+all\s+contacts|'
       r'my\s+contacts|sabhi\s+contacts|contacts\s+dikhao|'
       r'contacts\s+list|phonebook|contact\s+list)\b'),
]

# Add a contact → group(1)=name, group(2)=phone
ADD_CONTACT: List[Pattern] = [
    # "add contact name 9876543210"
    _c(r'^add\s+contact\s+(.+?)\s+(\+?\d[\d\s\-()\+]{6,18})\s*$'),
    # "add contact mummy" (will prompt for number)
    _c(r'^add\s+contact\s+(.+)$'),
    # "new contact name number"
    _c(r'^new\s+contact\s+(.+?)\s+(\+?\d[\d\s\-()\+]{6,18})\s*$'),
    # "contact save name number"
    _c(r'^save\s+contact\s+(.+?)\s+(\+?\d[\d\s\-()\+]{6,18})\s*$'),
    # Hindi: "contact add karo name number"
    _c(r'^contact\s+add\s+karo\s+(.+?)\s+(\+?\d[\d\s\-()\+]{6,18})\s*$'),
    # "naya contact name number"
    _c(r'^naya\s+contact\s+(.+?)\s+(\+?\d[\d\s\-()\+]{6,18})\s*$'),
]

# Delete a contact → group(1)=name
DELETE_CONTACT: List[Pattern] = [
    # "delete contact name"
    _c(r'^delete\s+contact\s+(.+)$'),
    # "remove contact name"
    _c(r'^remove\s+contact\s+(.+)$'),
    # "contact delete karo name"
    _c(r'^contact\s+delete\s+karo\s+(.+)$'),
    # "contact hatao name"
    _c(r'^contact\s+hatao\s+(.+)$'),
    # "delete name from contacts"
    _c(r'^delete\s+(.+?)\s+(?:from\s+)?contacts?$'),
]

# Search contacts → group(1)=query
SEARCH_CONTACTS: List[Pattern] = [
    # "search contact name"
    _c(r'^search\s+contact\s+(.+)$'),
    # "find contact name"
    _c(r'^find\s+contact\s+(.+)$'),
    # "contact dhundo name"
    _c(r'^contact\s+dhundo\s+(.+)$'),
    # "search for name in contacts"
    _c(r'search\s+(?:for\s+)?(.+?)\s+(?:in\s+)?contacts', re.IGNORECASE),
    # "find name phone number"
    _c(r'^find\s+(.+?)\s+(?:phone|number|mobile)\s*$'),
]

# ══════════════════════════════════════════════════════════════════
# UTILITY — Noise Words for Entity Cleaning
# ══════════════════════════════════════════════════════════════════

# Action verbs to strip when extracting entity names
ACTION_NOISE_WORDS = [
    "open", "launch", "start", "kholo", "chalao", "open karo",
    "launch karo", "start karo", "chalu karo",
    "chalana", "kholna", "hai",
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
