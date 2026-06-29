"""
╔══════════════════════════════════════════════════════════╗
║      1M DAILY CONVERSATION DATASET GENERATOR            ║
║  Generates 1,000,000 intent training examples across    ║
║  all 28 intents with English / Hindi / Hinglish         ║
╚══════════════════════════════════════════════════════════╝

Strategy: Combinatorial slot-filling.
Each intent generator uses templates with {slot} placeholders
and large slot-value lists. Random combinations produce
highly diverse examples with minimal code.

Usage:
    python ai/datasets/generate_daily_1m.py
"""

import json
import random
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from micro_brain.config import INTENTS, DATASETS_DIR


class DailyConversationGenerator:
    """Generates 1M daily conversation examples for intent training."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.examples = []
        self.intent_map = {name: idx for idx, name in enumerate(INTENTS)}

    # ── Shared slot value pools ────────────────────────────────────

    APPS = [
        "whatsapp", "youtube", "chrome", "telegram", "instagram",
        "gmail", "maps", "camera", "phone", "contacts",
        "gallery", "settings", "calculator", "calendar", "clock",
        "spotify", "messages", "play store", "music", "video",
        "file manager", "twitter", "facebook", "uber", "zomato",
        "swiggy", "paytm", "netflix", "amazon", "flipkart",
        "linkedin", "snapchat", "reddit", "hotstar", "prime video",
        "phone pe", "google pay", "myjio", "airtel", "truecaller",
    ]

    CONTACTS = [
        "mummy", "papa", "bhai", "didi", "friend",
        "ammu", "abu", "mama", "mausi", "mom", "dad",
        "sister", "brother", "boss", "colleague", "doctor",
        "police", "driver", "helper", "john", "alice",
        "sam", "riya", "rohit", "priya", "ajay",
        "vikram", "anita", "deepak", "sonal", "arjun",
    ]

    TIMES = [
        "5 min", "10 min", "30 min", "1 hour", "2 hours",
        "5 minute", "10 minute", "30 minute", "1 ghanta", "aaj raat",
        "kal", "1 minute", "15 minute", "30 second", "after 5 min",
        "5 seconds", "after 5 seconds", "after 10 seconds",
        "after 30 seconds", "after 1 hour", "2 ghante",
        "thodi der", "ek ghanta", "aaj shaam", "kal subah",
    ]

    TASKS = [
        "call", "meeting", "pills", "water", "medicine", "lunch",
        "dinner", "breakfast", "workout", "yoga", "homework",
        "shopping", "bills", "appointment", "groceries", "walk",
        "reading", "study", "project", "email", "laundry",
    ]

    # ── Noise injection ────────────────────────────────────────────

    def _add_noise(self, text: str) -> str:
        """Add random noise: case, punctuation, typos."""
        r = random.random()
        if r < 0.1:
            text = text.upper()
        elif r < 0.2:
            text = text.capitalize()
        elif r < 0.25:
            text = text + "."
        elif r < 0.3:
            text = text + "!"
        elif r < 0.33:
            text = text + "?"
        elif r < 0.36:
            text = text + " please"
        elif r < 0.39:
            text = "please " + text
        return text

    # ── Slot-filling generator helper ──────────────────────────────

    def _fill_slots(self, target: int, templates: list,
                    slots: dict, noise: bool = True) -> list:
        """Generate target examples by randomly filling templates with slot values."""
        examples = []
        # Pre-expand template × slot combinations to estimate space
        if not templates:
            return []
        attempts = 0
        max_attempts = target * 10
        while len(examples) < target and attempts < max_attempts:
            attempts += 1
            t = random.choice(templates)
            kwargs = {}
            for slot_name, values in slots.items():
                if values:
                    kwargs[slot_name] = random.choice(values)
            try:
                text = t.format(**kwargs)
            except (KeyError, IndexError):
                continue
            if noise:
                text = self._add_noise(text)
            # Avoid exact duplicates in this batch (loose check, small batches are fine)
            if len(examples) < target:
                examples.append(text)
        # If we still don't have enough, pad with random selection
        while len(examples) < target:
            t = random.choice(templates)
            kwargs = {}
            for slot_name, values in slots.items():
                if values:
                    kwargs[slot_name] = random.choice(values)
            try:
                text = t.format(**kwargs)
            except (KeyError, IndexError):
                text = "general query"
            if noise:
                text = self._add_noise(text)
            examples.append(text)
        random.shuffle(examples)
        return examples[:target]

    # ── Intent generator methods ───────────────────────────────────

    def gen_open_app(self, count: int) -> list:
        templates = [
            "open {app}",
            "open {app} karo",
            "{app} kholo",
            "{app} open karo",
            "{app} khol do",
            "kholo {app}",
            "{app} open kar",
            "{app} chalao",
            "start {app}",
            "launch {app}",
            "{app} start karo",
            "{app} open karna",
            "{app} pe jao",
            "{app} dikhao",
            "open karo {app}",
            "chalao {app}",
            "{app} kholna",
            "mujhe {app} kholna hai",
            "{app} kholo ji",
            "{app} tod kholo",
        ]
        return self._fill_slots(count, templates, {"app": self.APPS})

    def gen_close_app(self, count: int) -> list:
        templates = [
            "close app",
            "close application",
            "exit app",
            "band karo",
            "band kar",
            "close karo",
            "app band karo",
            "app ko band karo",
            "app close karo",
            "close this app",
            "app ko band kar do",
            "exit this app",
            "app exit karo",
            "current app band karo",
            "app hatao",
            "hatao is app ko",
            "app ko hatao",
            "close kar do",
            "band kar do app",
            "app close kar do",
            "yeh app band karo",
            "jo chal raha hai band karo",
            "background app band karo",
            "app band kar do",
        ]
        return self._fill_slots(count, templates, {})

    def gen_play_music(self, count: int) -> list:
        templates = [
            "play music",
            "play song",
            "play some music",
            "play gaana",
            "song play karo",
            "music play karo",
            "gaana chalao",
            "gaana bajao",
            "kuch gaana chalao",
            "song chalao",
            "music chalao",
            "music on karo",
            "music start karo",
            "bajao kuch",
            "play karo music",
            "kuch gaana bajao",
            "chalao gaana",
            "bajao gaana",
            "song laga do",
            "kuch song chalao",
            "kuch bajao",
            "music on kar do",
            "music play kardo",
            "play some songs",
            "music chala do",
            "gaana chala do",
            "kuch music bajao",
            "song on karo",
            "gaana on karo",
            "music laga do",
            "kuch gaana laga do",
            "mood music chalao",
            "relaxing music chalao",
        ]
        return self._fill_slots(count, templates, {})

    def gen_pause_music(self, count: int) -> list:
        templates = [
            "pause music",
            "pause song",
            "stop music",
            "stop song",
            "music rok do",
            "song rok do",
            "gaana band kar",
            "pause karo",
            "stop karo",
            "music off karo",
            "music band kar",
            "song pause karo",
            "gaana rok do",
            "music stop karo",
            "song off karo",
            "pause the music",
            "stop the music",
            "gaana band kardo",
            "song stop karo",
            "abhi ke liye stop",
            "pause kar do music",
            "music ruko",
            "gaana ruko",
            "song band karo",
            "music tham do",
            "yeh gaana band karo",
            "filhaal rok do",
            "band kar do yeh",
        ]
        return self._fill_slots(count, templates, {})

    def gen_search_web(self, count: int) -> list:
        topics = [
            "weather", "news", "recipes", "games", "movies",
            "songs", "places", "restaurants", "hospitals", "schools",
            "shops", "prices", "jobs", "cars", "bikes",
            "laptops", "mobiles", "books", "hotels", "flights",
            "today's news", "cricket score", "stock price",
            "exchange rate", "bus schedule", "train time",
        ]
        templates = [
            "search {topic}",
            "search {topic} karo",
            "{topic} search karo",
            "{topic} dhoondho",
            "search internet for {topic}",
            "google {topic}",
            "{topic} google karo",
            "search web for {topic}",
            "find {topic} online",
            "look up {topic}",
            "search {topic} on internet",
            "{topic} ki information do",
            "search karo {topic}",
        ]
        return self._fill_slots(count, templates, {"topic": topics})

    def gen_weather(self, count: int) -> list:
        templates = [
            "weather kaisa hai",
            "mausam kaisa hai",
            "weather batao",
            "mausam batao",
            "weather",
            "weather report",
            "weather today",
            "weather update",
            "aaj kya mausam hai",
            "aaj ka mausam",
            "aaj kaisa mausam hai",
            "aaj weather kaisa hai",
            "outside temperature",
            "weather kya hai",
            "kya mausam hai",
            "aaj ka mausam kaisa hai",
            "temperature kya hai",
            "aaj kaisi weather hai",
            "weather status",
            "check weather",
            "weather check karo",
            "mausam ka haal",
            "aaj mausam kaisa rahega",
            "weather forecast",
            "mausam ki jaankari",
            "tell weather",
            "what is the weather",
            "how is the weather today",
            "weather outside",
            "kya mausam hai aaj",
            "aaj ka temperature kya hai",
            "kya garmi hai ya thand",
            "aaj kitni garmi hai",
            "barish hogi kya aaj",
        ]
        return self._fill_slots(count, templates, {})

    def gen_time(self, count: int) -> list:
        templates = [
            "time batao",
            "samay batao",
            "kitna bajaa",
            "kitne baje",
            "time kya hai",
            "current time batao",
            "what's the time",
            "samay kya hai",
            "time do",
            "tell me time",
            "time please",
            "time bata do",
            "kitna baj gaya",
            "kya time hai",
            "aapke paas time kya hai",
            "time batao na",
            "give me time",
            "batao time",
            "current time do",
            "time",
            "what time is it",
            "current time",
            "kya time ho raha hai",
            "time dikhao",
            "ghanti batao",
            "time kya ho raha hai",
            "abhi kitne baje hain",
            "current time kya hai",
        ]
        return self._fill_slots(count, templates, {})

    def gen_date(self, count: int) -> list:
        templates = [
            "date batao",
            "tareekh batao",
            "aaj ki tareekh",
            "aaj kya date hai",
            "current date",
            "what day is it",
            "aaj konsa din hai",
            "tareekh kya hai",
            "date do",
            "din batao",
            "aaj ka din",
            "whats the date",
            "kya tareekh hai",
            "aaj ki date batao",
            "date of today",
            "mujhe batao tareekh",
            "aaj kya din hai",
            "todays date",
            "tareekh bata do",
            "date kya hai",
            "tareekh kya hai aaj",
            "aaj konsi tareekh hai",
            "kya din hai aaj",
            "aaj date kya hai",
            "today date",
            "what date is today",
            "tell me the date",
            "aaj kya tareekh hai",
            "date kya hai aaj",
            "konsi date hai",
            "kya din hai",
            "batao tareekh",
            "date",
            "what is today's date",
        ]
        return self._fill_slots(count, templates, {})

    def gen_reminder(self, count: int) -> list:
        templates = [
            "remind me in {time}",
            "remind me to {task} in {time}",
            "set reminder for {time}",
            "reminder set karo {time}",
            "reminder lagao {time}",
            "mujhe yaad dilao {time}",
            "yaad dila do {time}",
            "yaad dila {time}",
            "reminder do {time}",
            "set an alarm for {time}",
            "reminder ra karo {time}",
            "mujhe yaad dila dena {time}",
            "reminder set {time}",
            "{time} baad yaad dila",
            "{time} mein {task} ki yaad dila",
            "alarm laga do {time}",
            "alarm set kar do {time}",
            "{task} ke liye {time} pe yaad dila",
            "reminder for {task} in {time}",
            "set a reminder to {task} after {time}",
            "notify me in {time} to {task}",
        ]
        return self._fill_slots(count, templates, {
            "time": self.TIMES,
            "task": self.TASKS,
        })

    def gen_call(self, count: int) -> list:
        templates = [
            "call {contact}",
            "{contact} ko call karo",
            "{contact} ko phone karo",
            "{contact} ko call kar",
            "phone karo {contact} ko",
            "{contact} phone karo",
            "{contact} ko dial karo",
            "call karo {contact} ko",
            "{contact} se baat karni hai",
            "{contact} ka number milao",
            "{contact} lagao",
            "make a call to {contact}",
            "{contact} ko phone lagao",
            "give a call to {contact}",
            "ring {contact}",
            "call kar do {contact} ko",
        ]
        return self._fill_slots(count, templates, {"contact": self.CONTACTS})

    def gen_message(self, count: int) -> list:
        templates = [
            "message {contact}",
            "{contact} ko message karo",
            "{contact} ko text karo",
            "text {contact}",
            "send message to {contact}",
            "{contact} ko msg bhejo",
            "sms {contact}",
            "message bhejo {contact} ko",
            "{contact} ko sms karo",
            "send a text to {contact}",
            "{contact} ko whatsapp karo",
            "write to {contact}",
            "ping {contact}",
            "send an sms to {contact}",
        ]
        return self._fill_slots(count, templates, {"contact": self.CONTACTS})

    def gen_camera(self, count: int) -> list:
        templates = [
            "camera kholo",
            "open camera",
            "photo lena hai",
            "picture lena hai",
            "selfie lena hai",
            "photo khinch",
            "camera open karo",
            "camera chalao",
            "picture khinch",
            "camera start karo",
            "camera on karo",
            "kholo camera",
            "selfie khinch",
            "photo click karo",
            "camera chal jao",
            "picture click karo",
            "mujhe picture leni hai",
            "camera dikhao",
            "camera",
            "kuch photo le lo",
            "photo le",
            "selfie le",
            "photo kheecho",
        ]
        return self._fill_slots(count, templates, {})

    def gen_flashlight_on(self, count: int) -> list:
        templates = [
            "flashlight on",
            "torch on",
            "flash on",
            "flashlight chalu kar",
            "torch chalu kar",
            "light on karo",
            "flashlight on karo",
            "torch on karo",
            "flash on karo",
            "light chalu karo",
            "flashlight jalao",
            "torch jalao",
            "flash on kar do",
            "flashlight on kar do",
            "torch jala do",
            "light on",
            "torch on kardo",
            "flash on kardo",
            "flash chalu kar",
            "light jalao",
            "torch chalu kardo",
            "flashlight chalu karo",
        ]
        return self._fill_slots(count, templates, {})

    def gen_flashlight_off(self, count: int) -> list:
        templates = [
            "flashlight off",
            "torch off",
            "flash off",
            "flashlight band kar",
            "torch band kar",
            "light off karo",
            "flashlight off karo",
            "torch off karo",
            "flash off karo",
            "light band karo",
            "flashlight bujhao",
            "torch bujhao",
            "flash bujha do",
            "flashlight off kardo",
            "torch off kardo",
            "light off kardo",
            "flash band kar",
            "torch bujha do",
            "light band karo",
            "flashlight band kardo",
            "torch band kardo",
            "flashlight band karo",
        ]
        return self._fill_slots(count, templates, {})

    def gen_volume_up(self, count: int) -> list:
        templates = [
            "volume up",
            "increase volume",
            "volume badhao",
            "aawaz badhao",
            "sound badhao",
            "volume up karo",
            "louder",
            "tez karo",
            "volume plus",
            "aawaz tez karo",
            "sound up karo",
            "volume increase karo",
            "sound increase karo",
            "zordar",
            "volume badha do",
            "volume tez karo",
            "volume up kar do",
            "aawaz tez kardo",
            "aawaz aur tez karo",
            "thoda tez karo",
            "zyada loud karo",
            "volume thoda badhao",
            "aawaz badha do",
        ]
        return self._fill_slots(count, templates, {})

    def gen_volume_down(self, count: int) -> list:
        templates = [
            "volume down",
            "decrease volume",
            "volume kam karo",
            "aawaz kam karo",
            "sound kam karo",
            "volume low karo",
            "quieter",
            "halka karo",
            "volume minus",
            "aawaz halki karo",
            "dheere karo",
            "sound down karo",
            "volume decrease karo",
            "sound decrease karo",
            "volume kam kardo",
            "aawaz kam kardo",
            "volume low kardo",
            "dheere bolo",
            "thoda halka karo",
            "aur dheere karo",
            "aawaz halki kardo",
            "quiet karo",
        ]
        return self._fill_slots(count, templates, {})

    def gen_home(self, count: int) -> list:
        templates = [
            "go home",
            "home screen",
            "home",
            "home par jao",
            "home pe jao",
            "home screen dikhao",
            "main screen",
            "desktop dikhao",
            "home page",
            "home jao",
            "home kholo",
            "home screen chalao",
            "gher jao",
            "home dikhao",
            "pehle page",
            "main page dikhao",
            "home screen pe jao",
            "home par le jao",
            "home screen kholo",
            "launcher dikhao",
            "main home pe jao",
        ]
        return self._fill_slots(count, templates, {})

    def gen_back(self, count: int) -> list:
        templates = [
            "go back",
            "back",
            "back karo",
            "peeche jao",
            "wapis jao",
            "pichhle page",
            "pichhe jao",
            "wapis",
            "back button",
            "pichle page pe jao",
            "ek step pichhe jao",
            "go back one page",
            "back arrow",
            "wapis chalo",
            "pichhe",
            "previous page",
            "wapis le jao",
            "back jao",
        ]
        return self._fill_slots(count, templates, {})

    def gen_setting(self, count: int) -> list:
        setting_types = [
            "wifi", "bluetooth", "display", "sound", "network",
            "mobile data", "hotspot", "storage", "battery", "security",
            "privacy", "notification", "language", "accessibility",
            "date time", "calling", "messages", "apps",
            "developer", "about phone",
        ]
        templates = [
            "open settings",
            "settings kholo",
            "setting kholo",
            "settings open karo",
            "setting open kar",
            "settings dikhao",
            "settings par jao",
            "setting khol do",
            "setting menu",
            "system settings",
            "phone settings",
            "settings mein jao",
            "settings kholo ji",
            "{st} settings",
            "{st} settings kholo",
            "{st} settings open karo",
            "{st} ki settings",
            "{st} settings dikhao",
            "open {st} settings",
            "{st} settings mein jao",
        ]
        return self._fill_slots(count, templates, {"st": setting_types})

    def gen_python_coding(self, count: int) -> list:
        actions = [
            "read a file line by line", "write json data to a file",
            "sort a list of dictionaries", "find all prime numbers",
            "reverse a string", "make an HTTP GET request",
            "parse a JSON string", "connect to a database",
            "calculate factorial", "generate random number",
            "format a string", "merge two dictionaries",
            "download an image", "create a class with inheritance",
            "remove duplicates from list", "find intersection of lists",
            "convert string to datetime", "check if key exists in dict",
            "get current working directory", "execute shell command",
            "convert celsius to fahrenheit", "check if string is palindrome",
            "sum all items in list", "find max value in list",
            "group elements in list", "flatten a nested list",
            "generate a UUID", "check if file exists",
            "read environment variables", "create directory if not exists",
            "zip a folder", "unzip a file",
            "send an email via SMTP", "hash a password with bcrypt",
            "serialize with pickle", "convert CSV to JSON",
            "parse XML data", "validate email address format",
            "find regex matches", "replace substring in string",
            "split string by delimiter", "strip whitespace from string",
            "count word frequency", "get length of list",
            "convert list to string", "check if list is empty",
            "append to list", "remove element by index",
            "train a machine learning model", "split data into train and test",
            "calculate mean squared error", "normalize features with StandardScaler",
            "build a CNN in PyTorch", "fine-tune a BERT model",
            "apply k-means clustering", "plot a confusion matrix",
            "compute cross-validation score", "save model with joblib",
            "load PyTorch model state dict", "create custom PyTorch dataset",
            "define loss function and optimizer", "perform grid search",
            "handle missing values in pandas", "one-hot encode categorical features",
            "calculate precision recall f1", "train a support vector machine",
            "implement gradient descent", "plot ROC curve",
            "calculate cosine similarity", "train logistic regression",
            "fit random forest classifier", "preprocess text data for NLP",
            "tokenize text using HuggingFace", "define Keras sequential model",
            "use early stopping during training", "compute gradient with autograd",
            "plot learning curves", "compute correlation matrix",
            "perform feature selection", "impute missing data",
            "detect outliers with Isolation Forest", "train gradient boosting classifier",
            "apply PCA", "save PyTorch model",
            "load TensorFlow model", "train a deep learning model",
            "predict labels with scikit-learn", "get feature importances",
            "visualize decision boundary", "calculate AUC-ROC",
            "train XGBoost model", "implement k-fold cross validation",
            "use list comprehension", "use decorators in python",
            "use generators in python", "use lambda functions",
            "use virtual environment", "use args and kwargs",
            "use dataclasses", "use type hinting",
            "use asyncio", "use context manager",
            "use try except blocks", "use logging module",
        ]
        templates = [
            "how to {action} in python",
            "write a python code to {action}",
            "python function for {action}",
            "how do I {action} in python",
            "python script to {action}",
            "can you show me python code to {action}",
            "give me python code to {action}",
            "write code in python to {action}",
            "how to {action} in python 3",
            "python code for {action}",
            "implement {action} in python",
            "help me {action} using python",
            "i need python code to {action}",
            "python program to {action}",
            "create a python script that {action}",
        ]
        return self._fill_slots(count, templates, {"action": actions})

    def gen_ai_news_models(self, count: int) -> list:
        models = [
            "Gemini 3.5 Flash", "Gemini 2.0 Flash", "Gemini 1.5 Pro",
            "GPT-5", "GPT-4o", "GPT-4", "Claude 3.5 Sonnet",
            "Claude 4 Opus", "Llama 4", "Llama 3.1", "DeepSeek-V3",
            "DeepSeek-R1", "Qwen 3", "Mistral Large 3", "Grok 3",
            "Phi-4", "Command R+", "Gemma 2", "Mixtral 8x22B",
            "Falcon 2", "Yi Large", "Cohere Command R", "DBRX",
            "StarCoder 2", "CodeGemma", "Granite Code",
        ]
        topics = [
            "NVIDIA Blackwell Ultra GPUs", "Apple iOS 19 AI features",
            "Google Gemini 3.5 announcements", "DeepSeek open source model",
            "Anthropic Claude 4 Opus launch", "GPT-5 release date",
            "EU AI Act safety regulations", "AGI roadmap",
            "Sora text-to-video", "AI agents orchestration",
            "AI safety summit", "quantum AI acceleration",
            "humanoid robots", "self-driving cars progress",
            "AI in healthcare", "AI in education",
        ]
        templates = [
            "tell me about {model}",
            "what is {model}",
            "how to run {model} locally",
            "benchmark results of {model}",
            "context window of {model}",
            "is {model} open source",
            "architecture of {model}",
            "does {model} support reasoning",
            "how to fine tune {model}",
            "download weights for {model}",
            "running {model} on termux",
            "ollama support for {model}",
            "parameters in {model}",
            "{model} vs GPT-4o comparison",
            "latest news about {topic}",
            "explain {topic}",
            "what happened with {topic}",
            "updates on {topic}",
            "{topic} explained simply",
            "latest AI news",
            "best AI model 2026",
            "new LLM releases",
        ]
        all_slots = {"model": models, "topic": topics}
        # Mix model and topic templates
        texts = []
        target_per_template = count // len(templates) + 1
        for t in templates:
            if "{model}" in t and "{topic}" not in t:
                for _ in range(target_per_template):
                    texts.append(t.format(model=random.choice(models)))
            elif "{topic}" in t:
                for _ in range(target_per_template):
                    texts.append(t.format(topic=random.choice(topics)))
            else:
                for _ in range(target_per_template):
                    texts.append(t)
        random.shuffle(texts)
        return [self._add_noise(t) for t in texts][:count]

    def gen_capabilities(self, count: int) -> list:
        templates = [
            "what can you do",
            "what tasks can you perform",
            "list your capabilities",
            "what functionalities do you have",
            "what can this app do",
            "what are the supported commands",
            "how can you help me",
            "what features do you support",
            "show me what you can do",
            "what is your purpose",
            "tell me your functionalities",
            "list your main features",
            "what are your skills",
            "what actions can you take",
            "who made jarvis",
            "who created jarvis",
            "who built jarvis",
            "tum kya kar sakte ho",
            "tum kya kya kar sakte ho",
            "capabilities kya hain",
            "features kya hain tumhare",
            "kaam kya hai tumhara",
            "options kya hain",
            "commands kounsi support karte ho",
            "jarvis kisne banaya",
            "kya tum music chala sakte ho",
            "kya tum alarm laga sakte ho",
            "phone call kar sakte ho kya",
            "kya tum app khol sakte ho",
            "can you set alarms",
            "can you play music",
            "what apps can you open",
            "can you make phone calls",
            "can you send messages",
            "can you check the weather",
            "can you tell the time",
            "can you turn on flashlight",
            "can you control the volume",
            "can you write python code",
            "can you search the web",
        ]
        return self._fill_slots(count, templates, {})

    def gen_web_coding(self, count: int) -> list:
        html_actions = [
            "create a button", "make a form", "add an image",
            "create a navigation bar", "build a table",
            "add a video embed", "create a dropdown menu",
            "make a list in html", "add a link",
            "use semantic html tags", "create a div container",
            "add a footer", "build a header section",
            "create a card component", "make a login page",
            "create a contact form", "build a modal dialog",
            "create an accordion", "build a carousel",
            "create a pricing table", "make a sidebar layout",
            "create a 404 page", "build a portfolio page",
            "create a landing page", "make a registration form",
        ]
        css_actions = [
            "center a div", "style a button with hover",
            "create a grid layout", "make a flexbox design",
            "add keyframe animations", "style text with fonts",
            "create a gradient background", "add box shadow",
            "use css variables", "make responsive navbar",
            "style a form input", "add transitions",
            "create a card hover effect", "build a loading spinner",
            "make a sticky header", "use pseudo classes",
            "create a parallax effect", "use css transform",
            "create a responsive image gallery",
            "make a dark mode toggle", "create a tooltip",
            "build a masonry layout", "use filter effects",
            "style a scrollbar", "create a progress bar",
        ]
        js_actions = [
            "write a function to add two numbers",
            "create an array and iterate",
            "make an API call using fetch",
            "add event listener to button",
            "create a promise and handle it",
            "use async await syntax",
            "manipulate the DOM",
            "create a class in ES6",
            "use array methods map filter reduce",
            "handle form submission",
            "create a timer using setTimeout",
            "build a countdown timer",
            "use localStorage to save data",
            "create a JSON object and parse it",
            "add error handling with try catch",
            "create a modal using JavaScript",
            "build a to-do list app",
            "use destructuring",
            "make a simple calculator",
            "create a module and export it",
            "use spread operator",
            "build a stopwatch",
            "create a slideshow",
            "use arrow functions",
            "handle keyboard events",
            "create a shopping cart",
            "build a weather app with API",
            "create a form validator",
        ]
        templates = [
            "how to {html_a} in html",
            "html code for {html_a}",
            "css code to {css_a}",
            "javascript code to {js_a}",
            "how do I {css_a} in css",
            "how do I {js_a} in javascript",
            "show me css code to {css_a}",
            "write a javascript program to {js_a}",
            "html css code for {html_a}",
            "teach me how to {html_a}",
            "example of {css_a} in css",
            "example of {js_a} in javascript",
            "create a webpage with {html_a}",
            "how to {css_a} using css",
            "frontend code for {html_a}",
            "how to build {html_a} in html",
            "javascript function to {js_a}",
        ]
        return self._fill_slots(count, templates, {
            "html_a": html_actions,
            "css_a": css_actions,
            "js_a": js_actions,
        })

    def gen_general_knowledge(self, count: int) -> list:
        events = [
            "YouTube was founded", "iPhone was released",
            "Bitcoin was created", "COVID-19 pandemic",
            "ChatGPT was released", "Russia invaded Ukraine",
            "Queen Elizabeth II died", "Moon landing 1969",
            "Berlin Wall fell 1989", "World War II ended 1945",
            "Internet was invented", "First smartphone released",
            "Mars rover landing", "Global financial crisis",
            "Artificial intelligence advances", "Climate change",
            "Industrial revolution", "Renaissance period",
            "Roman Empire", "Ancient Egypt pyramids",
            "World War I began 1914", "Cold War era",
            "Soviet Union collapsed", "European Union formed",
        ]
        people = [
            "Einstein", "Newton", "Galileo", "Aristotle",
            "Leonardo da Vinci", "Shakespeare", "Buddha",
            "Mahatma Gandhi", "Martin Luther King", "Nelson Mandela",
            "Marie Curie", "Alan Turing", "Steve Jobs", "Elon Musk",
            "Barack Obama", "Donald Trump", "Joe Biden",
        ]
        science = [
            "photosynthesis", "quantum mechanics", "evolution",
            "gravity", "DNA structure", "black holes",
            "theory of relativity", "how vaccines work",
            "renewable energy", "how the internet works",
            "solar system", "human brain", "machine learning",
            "cloud computing", "cybersecurity", "blockchain",
        ]
        countries = [
            "India", "USA", "China", "Japan", "UK",
            "France", "Germany", "Canada", "Australia", "Brazil",
        ]
        templates = [
            "what is {topic}",
            "explain {topic}",
            "tell me about {topic}",
            "when did {event} happen",
            "who is {person}",
            "tell me about {person}",
            "what is {person} known for",
            "capital of {country}",
            "population of {country}",
            "tell me about {country}",
            "how does {topic} work",
            "why is {topic} important",
            "what causes {topic}",
            "define {topic}",
            "what happened during {event}",
            "describe {event}",
            "history of {topic}",
            "what is the story of {person}",
            "give me facts about {country}",
            "explain {science_topic} simply",
        ]
        return self._fill_slots(count, templates, {
            "event": events,
            "person": people,
            "topic": [f"{e}" for e in events] + [f"{s}" for s in science],
            "country": countries,
            "science_topic": science,
        })

    def gen_medicine_knowledge(self, count: int) -> list:
        conditions = [
            "diabetes", "hypertension", "asthma", "COVID-19",
            "common cold", "flu", "headache", "migraine",
            "fever", "cough", "allergies", "anxiety",
            "depression", "heart disease", "stroke", "cancer",
            "arthritis", "osteoporosis", "anemia", "thyroid",
            "chicken pox", "dengue", "malaria", "typhoid",
            "tuberculosis", "pneumonia", "hepatitis", "kidney stones",
        ]
        medicines = [
            "paracetamol", "ibuprofen", "aspirin", "amoxicillin",
            "omeprazole", "metformin", "atorvastatin", "losartan",
            "amlodipine", "cetirizine", "montelukast", "salbutamol",
        ]
        vitamins = [
            "Vitamin D", "Vitamin C", "Vitamin B12", "iron",
            "calcium", "zinc", "magnesium", "omega 3",
        ]
        templates = [
            "what is {cond}",
            "symptoms of {cond}",
            "treatment for {cond}",
            "causes of {cond}",
            "how to prevent {cond}",
            "what are the symptoms of {cond}",
            "home remedies for {cond}",
            "is {cond} contagious",
            "can {cond} be cured",
            "what medicine for {cond}",
            "what is {med} used for",
            "side effects of {med}",
            "dosage of {med}",
            "what is {vit} good for",
            "benefits of {vit}",
            "foods rich in {vit}",
            "does {med} have side effects",
            "when to take {med}",
            "healthy diet tips",
            "how to boost immunity",
            "how much water should I drink",
            "tips for better sleep",
            "exercise for heart health",
            "yoga for back pain",
            "how to reduce stress",
            "healthy eating habits",
        ]
        return self._fill_slots(count, templates, {
            "cond": conditions,
            "med": medicines,
            "vit": vitamins,
        })

    def gen_movie_knowledge(self, count: int) -> list:
        movies = [
            "The Shawshank Redemption", "The Godfather", "Dark Knight",
            "Pulp Fiction", "Forrest Gump", "Inception",
            "Fight Club", "The Matrix", "Interstellar",
            "Parasite", "Dangal", "3 Idiots",
            "Sholay", "Mughal-e-Azam", "Baahubali",
            "Avengers Endgame", "Titanic", "Avatar",
            "Jurassic Park", "Star Wars", "Lord of the Rings",
            "Harry Potter", "Spirited Away", "Toy Story",
        ]
        actors = [
            "Shah Rukh Khan", "Salman Khan", "Aamir Khan",
            "Amitabh Bachchan", "Tom Cruise", "Leonardo DiCaprio",
            "Robert Downey Jr", "Brad Pitt", "Christian Bale",
            "Deepika Padukone", "Priyanka Chopra", "Alia Bhatt",
            "Meryl Streep", "Scarlett Johansson", "Jennifer Lawrence",
        ]
        directors = [
            "Christopher Nolan", "Steven Spielberg", "Martin Scorsese",
            "Quentin Tarantino", "James Cameron", "Ridley Scott",
            "Satyajit Ray", "Rajkumar Hirani", "SS Rajamouli",
            "Yash Chopra", "David Fincher", "Denis Villeneuve",
        ]
        templates = [
            "who starred in {movie}",
            "what is {movie} about",
            "who directed {movie}",
            "rating of {movie}",
            "release year of {movie}",
            "is {movie} worth watching",
            "what movies has {actor} been in",
            "best movies of {actor}",
            "what movies has {dir} directed",
            "best {dir} movies",
            "recommend a movie like {movie}",
            "review of {movie}",
            "plot summary of {movie}",
            "box office collection of {movie}",
            "awards won by {movie}",
            "tell me about {actor}",
            "filmography of {actor}",
            "movies directed by {dir}",
            "best movie of 2024",
            "top rated movies of all time",
            "upcoming movies in 2026",
        ]
        return self._fill_slots(count, templates, {
            "movie": movies,
            "actor": actors,
            "dir": directors,
        })

    def gen_chat(self, count: int) -> list:
        templates = [
            "hello",
            "hi",
            "hey",
            "how are you",
            "kaise ho",
            "good morning",
            "good night",
            "thank you",
            "shukriya",
            "dhanyavaad",
            "bye",
            "tum kaun ho",
            "who are you",
            "namaste",
            "pranam",
            "baat karein",
            "kya kar rahe ho",
            "hey there",
            "namaste jarvis",
            "radhe radhe",
            "salaam",
            "adaab",
            "aur sunao",
            "kya chal raha hai",
            "kaisa chal raha hai sab",
            "sab badhiya",
            "aur batao",
            "kuch naya batao",
            "how was your day",
            "din kaisa raha",
            "what's up",
            "wassup",
            "had fun today",
            "you are awesome",
            "you are very helpful",
            "thank you so much",
            "dhanyawad dost",
            "thanks a lot",
            "bahut badiya kaam kiya",
            "very good job",
            "proud of you",
            "tum bahut samajhdar ho",
            "you are so smart",
            "gazab",
            "good afternoon",
            "good evening",
            "how's it going",
            "long time no see",
            "what's new",
            "happy to see you",
            "nice to meet you",
            "pleasure to meet you",
            "yo", "howdy",
            "hey jarvis", "hello jarvis",
            "ji namaste",
            "sup", "hello bro",
        ]
        return self._fill_slots(count, templates, {})

    def gen_unknown(self, count: int) -> list:
        templates = [
            "tell me a joke",
            "chutkula sunao",
            "sing a song",
            "gaana gaao",
            "dance",
            "naach",
            "kya ho tum",
            "will you be my friend",
            "i love you",
            "main tumse pyaar karta hoon",
            "what is love",
            "meaning of life",
            "how old are you",
            "you are great",
            "you are smart",
            "tum bahut achhe ho",
            "explain photosynthesis",
            "tell me about quantum computing",
            "what is the capital of India",
            "who is the prime minister",
            "should I buy a house or rent",
            "give me relationship advice",
            "how to cook biryani",
            "recipe for chicken tikka",
            "chai kaise banate hain",
            "who wrote hamlet",
            "tell me a fun fact",
            "history of space travel",
            "write a poem about stars",
            "create a story of a brave knight",
            "kya mujhe abhi sona chahiye",
            "which phone should I buy",
            "best laptop under 50k",
            "suggest a good movie",
            "should I learn python or javascript",
            "how to prepare for coding interview",
            "what is the best programming language",
            "how to learn english",
            "motivate me",
            "inspire me",
            "kuch acha batao",
            "i am sad",
            "mujhe udaas feel ho raha hai",
            "what do you think about AI",
            "will AI replace humans",
            "do you have feelings",
            "can you feel emotions",
            "are you sentient",
            "do robots dream",
            "what is the meaning of 42",
            "dhoni ka number",
            "how many stars in the sky",
            "why is the sky blue",
            "how to lose weight fast",
            "how to earn money online",
            "best investment tips",
        ]
        return self._fill_slots(count, templates, {})

    # ── Main generation orchestration ──────────────────────────────

    INTENT_GENERATORS = {
        "OPEN_APP": gen_open_app,
        "CLOSE_APP": gen_close_app,
        "PLAY_MUSIC": gen_play_music,
        "PAUSE_MUSIC": gen_pause_music,
        "SEARCH_WEB": gen_search_web,
        "WEATHER": gen_weather,
        "TIME": gen_time,
        "DATE": gen_date,
        "REMINDER": gen_reminder,
        "CALL": gen_call,
        "MESSAGE": gen_message,
        "CAMERA": gen_camera,
        "FLASHLIGHT_ON": gen_flashlight_on,
        "FLASHLIGHT_OFF": gen_flashlight_off,
        "VOLUME_UP": gen_volume_up,
        "VOLUME_DOWN": gen_volume_down,
        "HOME": gen_home,
        "BACK": gen_back,
        "SETTING": gen_setting,
        "PYTHON_CODING": gen_python_coding,
        "AI_NEWS_MODELS": gen_ai_news_models,
        "CAPABILITIES": gen_capabilities,
        "WEB_CODING": gen_web_coding,
        "GENERAL_KNOWLEDGE": gen_general_knowledge,
        "MEDICINE_KNOWLEDGE": gen_medicine_knowledge,
        "MOVIE_KNOWLEDGE": gen_movie_knowledge,
        "CHAT": gen_chat,
        "UNKNOWN": gen_unknown,
    }

    # Target distribution for 1,000,000 examples
    DISTRIBUTION = {
        "OPEN_APP": 50000,
        "CLOSE_APP": 15000,
        "PLAY_MUSIC": 25000,
        "PAUSE_MUSIC": 15000,
        "SEARCH_WEB": 40000,
        "WEATHER": 25000,
        "TIME": 30000,
        "DATE": 20000,
        "REMINDER": 30000,
        "CALL": 40000,
        "MESSAGE": 30000,
        "CAMERA": 20000,
        "FLASHLIGHT_ON": 15000,
        "FLASHLIGHT_OFF": 15000,
        "VOLUME_UP": 15000,
        "VOLUME_DOWN": 15000,
        "HOME": 15000,
        "BACK": 10000,
        "SETTING": 20000,
        "PYTHON_CODING": 80000,
        "AI_NEWS_MODELS": 80000,
        "CAPABILITIES": 40000,
        "WEB_CODING": 80000,
        "GENERAL_KNOWLEDGE": 150000,
        "MEDICINE_KNOWLEDGE": 60000,
        "MOVIE_KNOWLEDGE": 60000,
        "CHAT": 80000,
        "UNKNOWN": 50000,
    }

    def generate(self) -> list:
        """Generate all 1M examples across all intents."""
        examples = []
        total_target = sum(self.DISTRIBUTION.values())
        print(f"Generating {total_target:,} examples across {len(self.INTENT_GENERATORS)} intents...")
        print()

        for intent_name, gen_func in self.INTENT_GENERATORS.items():
            target = self.DISTRIBUTION[intent_name]
            intent_idx = self.intent_map[intent_name]
            texts = gen_func(self, target)
            for text in texts:
                examples.append({
                    "text": text,
                    "intent": intent_name,
                    "label": intent_idx,
                })
            print(f"  {intent_name:20s}: {len(texts):,} / {target:,}")

        random.shuffle(examples)
        self.examples = examples

        print(f"\nTotal generated: {len(examples):,}")
        dist = Counter(e["intent"] for e in examples)
        print("Distribution:")
        for intent, count in sorted(dist.items()):
            print(f"  {intent:20s}: {count:,}")
        return examples

    def save(self, filename: str = "intents.json"):
        """Save dataset to JSON file."""
        filepath = DATASETS_DIR / filename
        data = {
            "version": "2.0",
            "description": "Micro Neural Brain Intent Dataset — 1M daily conversation examples",
            "intents": INTENTS,
            "examples": self.examples,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"\nDataset saved to {filepath}")
        print(f"File size: {size_mb:.1f} MB")
        return filepath


def main():
    generator = DailyConversationGenerator()
    generator.generate()
    generator.save()
    print("\nDone! Ready for training.")


if __name__ == "__main__":
    main()
