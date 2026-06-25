"""
╔══════════════════════════════════════════════════╗
║     MICRO NEURAL BRAIN - DATASET GENERATOR       ║
║   Generates 5000+ training examples across       ║
║   all 20 intents with Hindi/English/Hinglish     ║
╚══════════════════════════════════════════════════╝
"""

import os
import json
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import INTENTS, DATASETS_DIR


class IntentDatasetGenerator:
    """
    Generates large intent training datasets with multilingual support.
    English + Hindi + Hinglish (mixed) examples.
    """

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.examples = []  # (text, intent_label)

        # ── Action verb mappings (English → Hindi/Hinglish) ─────
        self.verb_map = {
            "open": ["kholo", "khol", "khol do", "kholo", "open karo", "khol de", "kholna"],
            "close": ["band kar", "band karo", "band kardo", "band kar do", "close karo"],
            "play": ["chalao", "bajao", "play karo", "chala do", "start karo"],
            "pause": ["rok do", "rok", "rok de", "pause karo", "band kar"],
            "stop": ["band kar", "rok do", "rok", "stop karo", "band karo"],
            "search": ["search karo", "dhoondho", "dhundho", "search kar", "khojo", "search karo"],
            "set": ["set karo", "lagao", "set kar do", "set kardo", "ra karo"],
            "increase": ["badhao", "badha do", "increase karo", "zyada karo"],
            "decrease": ["kam karo", "kam kardo", "ghatao", "decrease karo"],
            "tell": ["batao", "bata", "bata do", "batao na"],
            "make": ["karo", "kar do", "kardo", "karna hai"],
            "send": ["bhejo", "bhej do", "send karo", "bhejna"],
            "turn on": ["chalu karo", "on karo", "jalao", "chalu kar", "on kar do"],
            "turn off": ["band karo", "off karo", "bujhao", "band kar do", "off kar do"],
        }

        self.app_names = [
            ("whatsapp", "whatsapp", "com.whatsapp"),
            ("youtube", "youtube", "com.google.android.youtube"),
            ("chrome", "chrome", "com.android.chrome"),
            ("telegram", "telegram", "org.telegram.messenger"),
            ("instagram", "instagram", "com.instagram.android"),
            ("gmail", "gmail", "com.google.android.gm"),
            ("maps", "maps", "com.google.android.apps.maps"),
            ("camera", "camera", "com.android.camera2"),
            ("phone", "phone", "com.android.dialer"),
            ("contacts", "contacts", "com.android.contacts"),
            ("gallery", "gallery", "com.android.gallery3d"),
            ("settings", "settings", "com.android.settings"),
            ("calculator", "calculator", "com.android.calculator2"),
            ("calendar", "calendar", "com.android.calendar"),
            ("clock", "clock", "com.android.deskclock"),
            ("spotify", "spotify", "com.spotify.music"),
            ("messages", "messages", "com.android.messaging"),
            ("play store", "play store", "com.android.vending"),
            ("music", "music", ""),
            ("video", "video", ""),
            ("file manager", "files", "com.android.documentsui"),
        ]

        self.contact_names = [
            "mummy", "papa", "bhai", "didi", "friend",
            "ammu", "abu", "mama", "mausi",
        ]

    def generate(self, target: int = 5000) -> list:
        """
        Generate the full dataset with at least `target` examples.
        Returns list of (text, intent_label_index) tuples.
        """
        # Generate examples for each intent
        generators = [
            (self._gen_open_app, "OPEN_APP", 500),
            (self._gen_close_app, "CLOSE_APP", 150),
            (self._gen_play_music, "PLAY_MUSIC", 300),
            (self._gen_pause_music, "PAUSE_MUSIC", 200),
            (self._gen_search_web, "SEARCH_WEB", 350),
            (self._gen_weather, "WEATHER", 250),
            (self._gen_time, "TIME", 250),
            (self._gen_date, "DATE", 200),
            (self._gen_reminder, "REMINDER", 300),
            (self._gen_call, "CALL", 350),
            (self._gen_message, "MESSAGE", 250),
            (self._gen_camera, "CAMERA", 200),
            (self._gen_flashlight_on, "FLASHLIGHT_ON", 200),
            (self._gen_flashlight_off, "FLASHLIGHT_OFF", 200),
            (self._gen_volume_up, "VOLUME_UP", 200),
            (self._gen_volume_down, "VOLUME_DOWN", 200),
            (self._gen_home, "HOME", 150),
            (self._gen_back, "BACK", 150),
            (self._gen_setting, "SETTING", 200),
            (self._gen_unknown, "UNKNOWN", 300),
        ]

        intent_map = {name: idx for idx, name in enumerate(INTENTS)}

        examples = []
        for gen_func, intent_name, count in generators:
            intent_idx = intent_map[intent_name]
            texts = gen_func(count)
            for text in texts:
                examples.append({"text": text, "intent": intent_name, "label": intent_idx})

        # Shuffle
        random.shuffle(examples)

        # Ensure we have enough
        while len(examples) < target:
            more = self._gen_random_examples(target - len(examples))
            examples.extend(more)

        self.examples = examples
        print(f"Generated {len(examples)} intent examples across {len(INTENTS)} classes")

        # Show class distribution
        from collections import Counter
        dist = Counter(e["intent"] for e in examples)
        for intent, count in sorted(dist.items()):
            print(f"  {intent:20s}: {count:4d}")

        return examples

    def save(self, filename: str = "intents.json"):
        """Save dataset to JSON file."""
        filepath = DATASETS_DIR / filename
        data = {
            "version": "1.0",
            "description": "Micro Neural Brain Intent Dataset (5000+ examples)",
            "intents": INTENTS,
            "examples": self.examples,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"Dataset saved to {filepath}")
        return filepath

    def load(self, filename: str = "intents.json") -> list:
        """Load dataset from JSON file."""
        filepath = DATASETS_DIR / filename
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.examples = data["examples"]
        print(f"Loaded {len(self.examples)} examples from {filepath}")
        return self.examples

    def get_split(self, val_split: float = 0.2, test_split: float = 0.1):
        """Split dataset into train/val/test."""
        examples = self.examples[:]
        random.shuffle(examples)

        n = len(examples)
        n_test = int(n * test_split)
        n_val = int(n * val_split)
        n_train = n - n_test - n_val

        train = examples[:n_train]
        val = examples[n_train:n_train + n_val]
        test = examples[n_train + n_val:]

        print(f"Split: train={len(train)}, val={len(val)}, test={len(test)}")
        return train, val, test

    # ═══════════════════════════════════════════════════════════
    # GENERATOR METHODS
    # ═══════════════════════════════════════════════════════════

    def _variations(self, base: str) -> list:
        """Generate variations of a base phrase."""
        texts = [base]
        texts.append(base + ".")
        texts.append(base + " please")
        texts.append(base + " karo")
        texts.append(base + " kar do")
        texts.append(base + " dijiye")
        texts.append("please " + base)
        texts.append("mujhe " + base)
        texts.append("aap " + base)
        # Case variations
        texts.append(base.capitalize())
        texts.append(base.upper())
        return texts

    def _gen_open_app(self, count: int) -> list:
        texts = []
        for app_name, hindu_name, _ in self.app_names:
            variants = [
                f"open {app_name}",
                f"open {hindu_name}",
                f"{app_name} kholo",
                f"{app_name} open karo",
                f"{app_name} khol do",
                f"{hindu_name} kholo",
                f"kholo {app_name}",
                f"{hindu_name} open kar",
                f"khole {hindu_name}",
                f"{app_name} chalao",
                f"start {app_name}",
                f"launch {app_name}",
                f"{app_name} start karo",
                f"jao {app_name}",
                f"{hindu_name} open karna",
                f"{app_name} open karde",
                f"{hindu_name} pe jao",
                f"{app_name} dikhao",
                f"open karo {app_name}",
                f"chalao {hindu_name}",
                f"{app_name} kholna",
            ]
            texts.extend(variants)
            if len(texts) >= count * 1.5:
                break

        # Augment
        return (texts * 3)[:count]

    def _gen_close_app(self, count: int) -> list:
        texts = []
        base = [
            "close app", "close application", "exit app",
            "band karo", "band kar", "close karo",
            "app band karo", "app ko band karo",
            "app close karo", "close this app",
            "app ko band kar do", "exit this app",
            "app exit karo", "current app band karo",
            "app hatao", "hatao is app ko",
            "app ko hatao", "close kar do",
            "band kar do app", "app close kar do",
        ]
        texts = [self._add_noise(t) for t in base] * (count // len(base) + 1)
        return texts[:count]

    def _gen_play_music(self, count: int) -> list:
        base = [
            "play music", "play song", "play some music",
            "play gaana", "song play karo", "music play karo",
            "gaana chalao", "gaana bajao", "kuch gaana chalao",
            "song chalao", "music chalao", "music on karo",
            "music start karo", "bajao kuch", "play karo music",
            "kuch gaana bajao", "music start kar",
            "chalao gaana", "bajao gaana", "song laga do",
            "kuch song chalao", "kuch bajao",
            "music on kar do", "music play kardo",
            "play some songs", "music chala do",
            "gaana chala do", "kuch music bajao",
            "song on karo", "gaana on karo",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return (texts * 2)[:count]

    def _gen_pause_music(self, count: int) -> list:
        base = [
            "pause music", "pause song", "stop music", "stop song",
            "music rok do", "song rok do", "gaana band kar",
            "pause karo", "stop karo", "music off karo",
            "music band kar", "song pause karo", "gaana rok do",
            "music stop karo", "song off karo",
            "pause the music", "stop the music", "music stop",
            "gaana band kardo", "song stop karo",
            "abhi ke liye stop", "pause kar do music",
            "music ruko", "gaana ruko", "song band karo",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return (texts * 2)[:count]

    def _gen_search_web(self, count: int) -> list:
        topics = ["weather", "news", "recipes", "games", "weather today",
                  "movies", "songs", "places", "restaurants", "hospitals"]
        base = [
            "search internet", "search web", "search google",
            "google search karo", "search karo", "dhoondho",
            "internet pe search karo", "google pe search karo",
            "search kar", "dhundh", "khojo",
            "find online", "look up", "search online",
            "google karo", "web search", "search",
            "online search karo", "internet search",
            "google pe dhundho", "information do",
            "search kar do", "kuch dhundho",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        # Add topic-specific searches
        for topic in topics:
            texts.extend([
                f"search {topic}",
                f"search {topic} karo",
                f"{topic} search karo",
                f"{topic} dhoondho",
            ])
        return (texts * 2)[:count]

    def _gen_weather(self, count: int) -> list:
        base = [
            "weather", "weather kaisa hai", "mausam",
            "mausam kaisa hai", "weather report",
            "weather today", "weather update",
            "aaj kya mausam hai", "aaj ka mausam",
            "aaj kaisa mausam hai", "aaj weather kaisa hai",
            "outside temperature", "weather kya hai",
            "kya mausam hai", "aaj ka mausam kaisa hai",
            "temperature kya hai", "weather batao",
            "mausam batao", "aaj kaisi weather hai",
            "weather status", "check weather",
            "weather check karo", "mausam ka haal",
            "aaj mausam kaisa rahega", "weather forecast",
            "mausam ki jaankari", "mausam ki khabar",
            "tell weather", "what is the weather",
            "how is the weather today", "weather outside",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return (texts * 2)[:count]

    def _gen_time(self, count: int) -> list:
        base = [
            "time", "what time is it", "current time",
            "time batao", "samay batao", "kitna bajaa",
            "kitne baje", "time kya hai", "current time batao",
            "what's the time", "samay kya hai",
            "ghanti batao", "time do", "tell me time",
            "time please", "time bata do",
            "kitna baj gaya", "kya time hai",
            "aapke paas time kya hai", "time batao na",
            "give me time", "samay batao",
            "batao time", "current time do",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return (texts * 3)[:count]

    def _gen_date(self, count: int) -> list:
        base = [
            "date", "what is today's date", "today's date",
            "date batao", "tareekh batao", "aaj ki tareekh",
            "aaj kya date hai", "current date", "what day is it",
            "aaj konsa din hai", "tareekh kya hai",
            "date do", "din batao", "aaj ka din",
            "whats the date", "kya tareekh hai",
            "aaj ki date batao", "date of today",
            "mujhe batao tareekh", "aaj kya din hai",
            "todays date", "tareekh bata do",
            "date kya hai", "tareekh kya hai aaj",
            "aaj konsi tareekh hai", "kya din hai aaj",
            "aaj date kya hai", "today date",
            "what date is today", "tell me the date",
            "aaj kya tareekh hai", "batao aaj kya tareekh hai",
            "date kya hai aaj", "konsi date hai",
            "kya din hai", "batao tareekh",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return (texts * 3)[:count]

    def _gen_reminder(self, count: int) -> list:
        times = ["5 min", "10 min", "30 min", "1 hour", "2 hours", "tomorrow",
                 "5 minute", "10 minute", "ek ghanta", "aaj raat", "kal",
                 "1 minute", "15 minute", "30 second", "after 5 min"]
        tasks = ["call", "meeting", "pills", "water", "medicine", "lunch",
                 "dinner", "breakfast", "workout", "yoga", "homework"]
        base = [
            "remind me", "set reminder", "reminder",
            "reminder set karo", "reminder lagao",
            "mujhe yaad dilao", "yaad dila do",
            "yaad dila", "reminder do",
            "alarm laga do", "alarm set kar do",
            "set an alarm", "reminder ra karo",
            "mujhe yaad dila dena", "reminder set",
        ]
        texts = []
        for b in base:
            for t in times:
                texts.append(f"{b} {t}")
            for task in tasks[:3]:
                for t in times[:3]:
                    texts.append(f"{b} to {task} in {t}")
        return texts[:count]

    def _gen_call(self, count: int) -> list:
        texts = []
        for contact in self.contact_names:
            variants = [
                f"call {contact}",
                f"{contact} ko call karo",
                f"{contact} ko phone karo",
                f"{contact} ko call kar",
                f"phone karo {contact} ko",
                f"{contact} phone karo",
                f"{contact} ko dial karo",
                f"call karo {contact} ko",
                f"{contact} se baat karni hai",
                f"{contact} ka number milao",
                f"{contact} lagao",
            ]
            texts.extend(variants)

        # General call phrases
        call_vars = [
            "make a call", "phone call karo",
            "phone lagao", "call kar do",
            "phone karo", "dial karo",
            "call please", "mujhe call karna hai",
            "phone call kar do",
        ]
        texts.extend(call_vars)
        return (texts * 2)[:count]

    def _gen_message(self, count: int) -> list:
        texts = []
        for contact in self.contact_names[:5]:
            variants = [
                f"message {contact}",
                f"{contact} ko message karo",
                f"{contact} ko text karo",
                f"text {contact}",
                f"send message to {contact}",
                f"{contact} ko msg bhejo",
                f"sms {contact}",
                f"message bhejo {contact} ko",
                f"{contact} ko sms karo",
            ]
            texts.extend(variants)

        msg_vars = [
            "send message", "text", "send text",
            "message bhejo", "sms bhejo", "msg bhejo",
            "text bhejo", "send a message",
            "message karo", "text karo",
        ]
        texts.extend(msg_vars)
        return (texts * 2)[:count]

    def _gen_camera(self, count: int) -> list:
        base = [
            "camera", "open camera", "camera kholo",
            "photo lena hai", "picture lena hai",
            "selfie lena hai", "photo khinch",
            "camera open karo", "camera chalao",
            "picture khinch", "camera start karo",
            "camera on karo", "kholo camera",
            "selfie khinch", "photo click karo",
            "camera chal jao", "photo lena hai",
            "picture click karo", "mujhe picture leni hai",
            "camera khole", "camera dikhao",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return texts[:count]

    def _gen_flashlight_on(self, count: int) -> list:
        base = [
            "flashlight on", "torch on", "flash on",
            "flashlight chalu kar", "torch chalu kar",
            "light on karo", "flashlight on karo",
            "torch on karo", "flash on karo",
            "light chalu karo", "flashlight jalao",
            "torch jalao", "flash on kar do",
            "flashlight on kar do", "torch jala do",
            "light on", "torch on kardo",
            "flash on kardo", "flash chalu kar",
            "light jalao", "torch chalu kardo",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return texts[:count]

    def _gen_flashlight_off(self, count: int) -> list:
        base = [
            "flashlight off", "torch off", "flash off",
            "flashlight band kar", "torch band kar",
            "light off karo", "flashlight off karo",
            "torch off karo", "flash off karo",
            "light band karo", "flashlight bujhao",
            "torch bujhao", "flash bujha do",
            "flashlight off kardo", "torch off kardo",
            "light off kardo", "flash band kar",
            "torch bujha do", "light band karo",
            "flashlight band kardo", "torch band kardo",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return texts[:count]

    def _gen_volume_up(self, count: int) -> list:
        base = [
            "volume up", "increase volume", "volume badhao",
            "aawaz badhao", "sound badhao", "volume up karo",
            "louder", "tez karo", "volume plus",
            "aawaz tez karo", "sound up karo",
            "volume increase karo", "sound increase karo",
            "zordar", "volume badha do", "volume tez karo",
            "volume up kar do", "aawaz tez kardo",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        # Add intensity variants
        texts.extend([f"{t} {n}" for t in ["volume up", "volume badhao", "aawaz badhao"]
                      for n in ["thoda", "zyada", "a little", "more", "thor sa"]])
        return texts[:count]

    def _gen_volume_down(self, count: int) -> list:
        base = [
            "volume down", "decrease volume", "volume kam karo",
            "aawaz kam karo", "sound kam karo", "volume low karo",
            "quieter", "halka karo", "volume minus",
            "aawaz halki karo", "dheere karo", "sound down karo",
            "volume decrease karo", "sound decrease karo",
            "volume kam kardo", "aawaz kam kardo",
            "volume low kardo", "dheere bolo",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        texts.extend([f"{t} {n}" for t in ["volume down", "volume kam", "aawaz kam"]
                      for n in ["thoda", "zyada", "a little", "more", "aur"]])

        return texts[:count]

    def _gen_home(self, count: int) -> list:
        base = [
            "go home", "home screen", "home",
            "home par jao", "home pe jao", "home screen dikhao",
            "main screen", "desktop dikhao", "home page",
            "home jao", "home kholo", "home screen chalao",
            "gher jao", "home dikhao", "pehle page",
            "main page dikhao", "home screen pe jao",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return texts[:count]

    def _gen_back(self, count: int) -> list:
        base = [
            "go back", "back", "back karo", "peeche jao",
            "wapis jao", "pichhle page", "pichhe jao",
            "wapis", "back button", "pichle page pe jao",
            "ek step pichhe jao", "go back one page",
            "back arrow", "wapis chalo", "pichhe",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        return texts[:count]

    def _gen_setting(self, count: int) -> list:
        setting_types = ["wifi", "bluetooth", "display", "sound", "network",
                         "mobile data", "hotspot", "storage", "battery", "security"]
        base = [
            "open settings", "settings", "setting",
            "settings kholo", "setting kholo",
            "settings open karo", "setting open kar",
            "settings dikhao", "settings par jao",
            "setting khol do", "setting menu",
            "system settings", "phone settings",
            "settings mein jao",
        ]
        texts = []
        for b in base:
            texts.extend(self._variations(b))
        for s in setting_types:
            texts.extend([
                f"{s} settings",
                f"{s} settings kholo",
                f"{s} settings open karo",
                f"{s} ki settings",
            ])
        return texts[:count]

    def _gen_unknown(self, count: int) -> list:
        """Generate out-of-scope / unknown examples."""
        unknown_phrases = [
            "hello", "hi", "hey", "how are you", "kaise ho",
            "good morning", "good night", "thank you",
            "shukriya", "dhanyavaad", "bye",
            "tum kaun ho", "who are you", "what can you do",
            "tum kya kar sakte ho", "tell me a joke",
            "chutkula sunao", "sing a song", "gaana gaao",
            "dance", "naach", "kya ho tum",
            "will you be my friend", "i love you",
            "main tumse pyaar karta hoon", "what is love",
            "meaning of life", "life kya hai",
            "who created you", "tumhe kisne banaya",
            "what's your name", "tumhara naam kya hai",
            "how old are you", "tere kitne saal hai",
            "you are great", "you are smart",
            "tum bahut achhe ho", "good morning sir",
            "hello ji", "namaste", "pranam",
            "let's chat", "baat karein", "kya kar rahe ho",
        ]
        return (unknown_phrases * 5)[:count]

    def _gen_random_examples(self, count: int) -> list:
        """Generate random mix of examples."""
        all_generators = [
            self._gen_open_app, self._gen_close_app,
            self._gen_play_music, self._gen_pause_music,
            self._gen_search_web, self._gen_weather,
            self._gen_time, self._gen_date,
            self._gen_reminder, self._gen_call,
            self._gen_message, self._gen_camera,
            self._gen_flashlight_on, self._gen_flashlight_off,
            self._gen_volume_up, self._gen_volume_down,
            self._gen_home, self._gen_back,
            self._gen_setting, self._gen_unknown,
        ]
        intent_map = {name: idx for idx, name in enumerate(INTENTS)}
        intent_names = list(intent_map.keys())

        # Explicit mapping: generator method → intent name
        # Avoids fragile substring matching that can produce mislabeled samples
        gen_to_intent = {}
        for gen in all_generators:
            name_upper = gen.__name__.upper()
            matched = None
            for intent_name in intent_map:
                # Match by extracting intent name from generator suffix
                # e.g. _gen_open_app → OPEN_APP
                suffix = name_upper.removeprefix("_GEN_")
                if suffix == intent_name:
                    matched = intent_name
                    break
            gen_to_intent[gen] = matched

        examples = []
        for _ in range(count):
            gen = random.choice(all_generators)
            intent_name = gen_to_intent.get(gen)
            if intent_name is None:
                intent_name = random.choice(intent_names)
            intent_idx = intent_map[intent_name]

            text = gen(1)[0]
            examples.append({"text": text, "intent": intent_name, "label": intent_idx})

        return examples

    def _add_noise(self, text: str) -> str:
        """Add minor noise/variations to text."""
        noise_ops = [
            lambda t: t + ".",
            lambda t: t + " please",
            lambda t: t.capitalize(),
            lambda t: t,
            lambda t: t.upper(),
            lambda t: t + " ji",
        ]
        return random.choice(noise_ops)(text)


if __name__ == "__main__":
    generator = IntentDatasetGenerator()
    examples = generator.generate(target=5000)
    path = generator.save("intents.json")
    generator.get_split()
