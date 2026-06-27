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
            ("twitter", "twitter", "com.twitter.android"),
            ("facebook", "facebook", "com.facebook.katana"),
            ("uber", "uber", "com.ubercab"),
            ("zomato", "zomato", "com.application.zomato"),
            ("swiggy", "swiggy", "in.swiggy.android"),
            ("paytm", "paytm", "net.one97.paytm"),
            ("netflix", "netflix", "com.netflix.mediaclient"),
        ]

        self.contact_names = [
            "mummy", "papa", "bhai", "didi", "friend",
            "ammu", "abu", "mama", "mausi", "mom", "dad",
            "sister", "brother", "boss", "colleague", "doctor",
            "police", "driver", "helper", "john", "alice",
        ]

    def generate(self, target: int = 5000) -> list:
        """
        Generate the full dataset with at least `target` examples.
        Returns list of (text, intent_label_index) tuples.
        """
        # Generate examples for each intent
        generators = [
            (self._gen_open_app, "OPEN_APP", 800),
            (self._gen_close_app, "CLOSE_APP", 250),
            (self._gen_play_music, "PLAY_MUSIC", 450),
            (self._gen_pause_music, "PAUSE_MUSIC", 300),
            (self._gen_search_web, "SEARCH_WEB", 550),
            (self._gen_weather, "WEATHER", 400),
            (self._gen_time, "TIME", 400),
            (self._gen_date, "DATE", 300),
            (self._gen_reminder, "REMINDER", 450),
            (self._gen_call, "CALL", 550),
            (self._gen_message, "MESSAGE", 400),
            (self._gen_camera, "CAMERA", 300),
            (self._gen_flashlight_on, "FLASHLIGHT_ON", 300),
            (self._gen_flashlight_off, "FLASHLIGHT_OFF", 300),
            (self._gen_volume_up, "VOLUME_UP", 300),
            (self._gen_volume_down, "VOLUME_DOWN", 300),
            (self._gen_home, "HOME", 250),
            (self._gen_back, "BACK", 250),
            (self._gen_setting, "SETTING", 300),
            (self._gen_python_coding, "PYTHON_CODING", 1800),
            (self._gen_ai_news_models, "AI_NEWS_MODELS", 1800),
            (self._gen_capabilities, "CAPABILITIES", 1800),
            (self._gen_unknown, "UNKNOWN", 800),
        ]

        intent_map = {name: idx for idx, name in enumerate(INTENTS)}

        # Scale count to sum up to target
        total_default = sum(count for _, _, count in generators)
        scale = target / total_default

        examples = []
        for gen_func, intent_name, count in generators:
            scaled_count = int(count * scale)
            intent_idx = intent_map[intent_name]
            texts = gen_func(scaled_count)
            texts = self._ensure_count(texts, scaled_count)
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

    def _ensure_count(self, texts: list, count: int) -> list:
        """Ensure texts list contains exactly count elements by repeating or slicing."""
        if not texts:
            return ["dummy example"] * count
        return (texts * (count // len(texts) + 2))[:count]

    def _gen_python_coding(self, count: int) -> list:
        actions = [
            "read a file line by line", "write json data to a file", "sort a list of dictionaries by key",
            "find all prime numbers up to n", "reverse a string", "make an HTTP GET request",
            "parse a JSON string", "connect to a PostgreSQL database", "calculate the factorial of a number",
            "generate a random number between 1 and 100", "format a string with variables",
            "merge two dictionaries", "download an image from a URL", "create a class with inheritance",
            "remove duplicates from a list", "find the intersection of two lists",
            "convert a string to a datetime object", "check if a key exists in a dict",
            "get the current working directory", "execute a shell command", "convert celsius to fahrenheit",
            "check if string is palindrome", "sum all items in a list", "find the maximum value in a list",
            "group elements in a list", "flatten a nested list", "generate a UUID", "check if file exists",
            "read environment variables", "create a directory if not exists", "zip a folder", "unzip a file",
            "send an email via smtp", "hash a password with bcrypt", "serialize python object with pickle",
            "convert csv to json", "parse XML data", "validate email address format", "find regex matches in text",
            "replace substring in a string", "split string by delimiter", "strip whitespace from string",
            "count word frequency in text", "get length of a list", "convert list to string",
            "check if list is empty", "append elements to a list", "remove element by index",
            "pop element from list", "slice a list in python"
        ]

        action_gerunds = [
            "reading a file line by line", "writing json data to a file", "sorting a list of dictionaries",
            "finding prime numbers", "reversing a string", "making an HTTP GET request",
            "parsing JSON", "connecting to database", "calculating factorial", "generating random numbers",
            "merging dictionaries", "creating classes", "removing duplicates", "flattening lists",
            "hashing passwords", "parsing CSV", "validating emails", "using regex", "slicing lists"
        ]

        action_3rd_persons = [
            "reads a file line by line", "writes json data to a file", "sorts a list of dictionaries",
            "finds prime numbers", "reverses a string", "makes an HTTP GET request",
            "parses JSON", "calculates factorial", "generates random numbers", "merges two dicts",
            "removes duplicate items", "flattens list", "hashes a password", "converts csv to json"
        ]

        concepts = [
            "list comprehension", "decorators", "generators", "iterators", "lambda functions",
            "virtual environment", "dict comprehension", "args and kwargs", "dunder methods",
            "object-oriented programming", "multiprocessing", "threading", "context manager",
            "with statement", "dataclasses", "type hinting", "asyncio", "list slicing",
            "decorators with arguments", "global variables", "shallow vs deep copy", "mutable vs immutable",
            "try except blocks", "finally block", "custom exceptions", "logging module",
            "pip package manager", "requirements.txt", "docstrings", "pep 8 style guide",
            "f-strings", "walrus operator", "set operations", "tuple unpacking", "zip function",
            "enumerate function", "map and filter", "list vs tuple", "dict vs set", "classmethods and staticmethods",
            "property decorator", "super() function", "operator overloading", "multiple inheritance",
            "abstract base classes", "metaclasses", "memory management in python", "garbage collection"
        ]

        errors = [
            "IndentationError", "SyntaxError", "TypeError", "ValueError", "NameError",
            "AttributeError", "KeyError", "IndexError", "ZeroDivisionError", "FileNotFoundError",
            "ModuleNotFoundError", "RecursionError", "StopIteration", "ImportError", "RuntimeError",
            "AssertionError", "KeyboardInterrupt", "MemoryError", "OverflowError", "PermissionError"
        ]

        ml_actions = [
            "train a machine learning model", "split data into train and test sets", "calculate mean squared error",
            "normalize features using standard scaler", "build a convolutional neural network", "fine-tune a BERT model",
            "apply k-means clustering", "plot a confusion matrix", "compute cross-validation score",
            "save a trained model using joblib", "load a PyTorch model state dict", "create a custom PyTorch dataset",
            "define a loss function and optimizer", "perform grid search parameter tuning",
            "handle missing values in a pandas dataframe", "one-hot encode categorical features",
            "calculate precision recall and f1 score", "train a support vector machine", "implement gradient descent",
            "plot ROC curve", "calculate cosine similarity between vectors", "train a logistic regression",
            "fit a random forest classifier", "evaluate model on validation set", "preprocess text data for NLP",
            "tokenize input text using HuggingFace", "define a sequential model in Keras", "use early stopping during training",
            "compute gradient using PyTorch autograd", "plot learning curves of model training",
            "compute correlation matrix using pandas", "perform feature selection", "impute missing data",
            "detect outliers using Isolation Forest", "train a gradient boosting classifier", "apply principal component analysis PCA",
            "save PyTorch model", "load TensorFlow model", "train a deep learning model", "predict labels using scikit-learn",
            "get feature importances from random forest", "visualize decision boundary", "plot precision recall curve",
            "calculate area under ROC curve ROC AUC", "train an XGBoost model", "implement k-fold cross validation"
        ]

        ml_concepts = [
            "supervised learning", "unsupervised learning", "overfitting and underfitting", "regularization L1 and L2",
            "backpropagation", "activation functions ReLU and Sigmoid", "dropout regularization",
            "learning rate schedule", "transfer learning", "feature engineering", "principal component analysis PCA",
            "confusion matrix", "gradient boosting", "neural network architecture", "cross entropy loss",
            "stochastic gradient descent SGD", "adam optimizer", "batch normalization", "autoencoders",
            "recurrent neural networks RNN", "convolutional neural networks CNN", "generative adversarial networks GAN",
            "reinforcement learning", "decision trees", "random forest", "support vector machines SVM",
            "k-nearest neighbors KNN", "naive bayes classifier", "linear regression", "logistic regression",
            "hyperparameter optimization", "cross validation", "bias variance tradeoff", "precision recall tradeoff",
            "mean absolute error MAE", "mean squared error MSE", "root mean squared error RMSE",
            "transformer architecture", "attention mechanism", "self attention", "embeddings", "word2vec",
            "t-SNE visualization", "cosine similarity", "Euclidean distance", "loss functions",
            "optimizers", "learning rate decay", "weight decay", "momentum in SGD"
        ]

        ml_errors = [
            "ValueError shapes not aligned", "RuntimeError CUDA out of memory", "KeyError column not found",
            "ModuleNotFoundError sklearn", "ModuleNotFoundError tensorflow", "ModuleNotFoundError torch",
            "ValueError Found input variables with inconsistent numbers of samples",
            "NameError name pd is not defined", "NameError name np is not defined"
        ]

        actions.extend(ml_actions)
        concepts.extend(ml_concepts)
        errors.extend(ml_errors)

        templates = [
            "how to {action} in python",
            "write a python code to {action}",
            "python function for {action}",
            "how do I {action} in python",
            "python script to {action}",
            "create a python script that {action_gerund}",
            "write a function in python that {action_3rd_person}",
            "can you show me python code to {action}",
            "give me python code to {action}",
            "write code in python to {action}",
            "how {action} in python 3",
            "explain {concept} in python",
            "what is {concept} in python",
            "how does {concept} work in python",
            "python {concept} example",
            "show me an example of {concept} in python",
            "write a python script using {concept}",
            "python code demonstrating {concept}",
            "how to use {concept} in python",
            "explain the concept of {concept} in python",
            "fix python {error} error",
            "why am I getting {error} in python",
            "how to solve {error} in python",
            "python {error} error handling",
            "handle {error} exception in python",
            "python code to fix {error}",
            "what causes {error} in python",
            "debug python {error}",
            "python syntax for {concept}",
            "how to avoid {error} in python code"
        ]

        texts = []
        for t in templates:
            if "{action}" in t:
                for act in actions:
                    texts.append(t.format(action=act))
            elif "{action_gerund}" in t:
                for ger in action_gerunds:
                    texts.append(t.format(action_gerund=ger))
            elif "{action_3rd_person}" in t:
                for thd in action_3rd_persons:
                    texts.append(t.format(action_3rd_person=thd))
            elif "{concept}" in t:
                for con in concepts:
                    texts.append(t.format(concept=con))
            elif "{error}" in t:
                for err in errors:
                    texts.append(t.format(error=err))

        code_snippets = [
            "def my_function(x): return x * 2",
            "import os\nos.listdir('.')",
            "import numpy as np",
            "import pandas as pd",
            "import json",
            "with open('file.txt', 'r') as f: print(f.read())",
            "class MyClass:\n    def __init__(self):\n        pass",
            "[x**2 for x in range(10) if x % 2 == 0]",
            "lambda x, y: x + y",
            "try:\n    x = 1/0\nexcept ZeroDivisionError:\n    pass",
            "import torch\nimport torch.nn as nn\nclass Net(nn.Module):",
            "from sklearn.model_selection import train_test_split\nX_train, X_test = train_test_split(X)",
            "from sklearn.ensemble import RandomForestClassifier\nclf = RandomForestClassifier().fit(X, y)",
            "import tensorflow as tf\nmodel = tf.keras.Sequential()",
            "import pandas as pd\ndf = pd.read_csv('data.csv')",
            "loss = criterion(outputs, targets)\nloss.backward()\noptimizer.step()",
            "from sklearn.metrics import accuracy_score\nacc = accuracy_score(y_true, y_pred)"
        ]
        texts.extend(code_snippets)

        texts = [self._add_noise(t) for t in texts]
        random.shuffle(texts)
        return texts

    def _gen_ai_news_models(self, count: int) -> list:
        models = [
            "Gemini 3.5 Flash", "Gemini 2.0 Flash", "Gemini 1.5 Pro", "Gemini 3.5 Pro",
            "GPT-5", "GPT-4o", "GPT-4", "Claude 3.5 Sonnet", "Claude 4 Sonnet",
            "Claude 3.5 Opus", "Claude 4 Opus", "Llama 4", "Llama 3.1", "Llama 3.2",
            "DeepSeek-V3", "DeepSeek-R1", "DeepSeek-Coder", "Qwen 3", "Qwen 2.5-Coder",
            "Mistral Large 3", "Grok 3", "Grok 2", "Phi-4", "Command R+"
        ]
        
        actions = [
            "what is the release date of", "tell me about the performance of",
            "how to run {model} locally", "compare {model} with GPT-4o",
            "benchmark results of", "context window size of", "pricing of API for",
            "is {model} open source", "architecture of", "does {model} support reasoning",
            "how to fine tune", "download weights for", "running {model} on termux",
            "ollama support for", "system requirements for", "how many parameters in"
        ]

        news_topics = [
            "NVIDIA Blackwell Ultra GPUs", "NVIDIA H200 AI chips", "Apple iOS 19 AI features",
            "Apple Intelligence updates", "Google Gemini 3.5 announcements", "Google I/O 2026 AI releases",
            "DeepSeek open source model release", "Anthropic Claude 4 Opus launch", "GPT-5 release date and leak",
            "EU AI Act safety regulations", "Artificial General Intelligence AGI roadmap", "AI agents orchestration framework",
            "Sora v2 text-to-video generator", "Veo 2 video generation model", "Kling AI global release",
            "Suno v4 music generator", "Udio v2 text to music", "Midjourney v7 release date",
            "Stable Diffusion 3.5 release", "AI safety summit 2026", "neuromorphic hardware breakthrough",
            "quantum computing AI acceleration", "robotics transformer models RT-3", "humanoid robots powered by LLM"
        ]

        news_actions = [
            "what are the latest updates on", "what is the news about", "explain the recent announcement regarding",
            "tell me about", "latest news on", "what happened with", "is there any update on",
            "summarize the news about", "give me the latest trends in", "any recent breakthroughs in"
        ]

        templates = [
            "{action} {model}",
            "{news_action} {news_topic}",
            "what is the best AI model in 2026",
            "latest AI news today",
            "new LLM releases in 2026",
            "compare {model} and {other_model}",
            "explain the reasoning capabilities of {model}",
            "is {model} better than {other_model}",
            "latest AI news",
            "current state of AGI in 2026",
            "what are the top 10 models in HuggingFace right now",
            "which model has the largest context window in 2026"
        ]

        texts = []
        for t in templates:
            if "{action}" in t:
                for act in actions:
                    for mod in models[:10]:
                        texts.append(t.format(action=act, model=mod))
            elif "{news_action}" in t:
                for n_act in news_actions:
                    for topic in news_topics:
                        texts.append(t.format(news_action=n_act, news_topic=topic))
            elif "{model}" in t and "{other_model}" in t:
                for mod1 in models[:8]:
                    for mod2 in models[8:16]:
                        texts.append(t.format(model=mod1, other_model=mod2))
            elif "{model}" in t:
                for mod in models:
                    texts.append(t.format(model=mod))
            else:
                texts.append(t)

        news_snippets = [
            "Google announced Gemini 3.5 Flash with 2 million context length",
            "NVIDIA Blackwell GPUs are shipping in 2026",
            "DeepSeek-R1 reasoning model achieves parity with OpenAI o1 on math benchmarks",
            "Anthropic launches Claude 4 Opus with state of the art agentic capabilities",
            "OpenAI GPT-5 is scheduled for release in late 2026 according to insiders",
            "Apple iOS 19 introduces local agentic workflows powered by iOS-on-device LLM",
            "EU AI Act safety compliance rules become active in 2026",
            "Sora v2 released with photorealistic video generation up to 2 minutes"
        ]
        texts.extend(news_snippets)

        texts = [self._add_noise(t) for t in texts]
        random.shuffle(texts)
        return texts

    def _gen_capabilities(self, count: int) -> list:
        subjects = [
            "what can you do", "what tasks can you perform", "what are your features",
            "list your capabilities", "what functionalities do you have", "what can this app do",
            "what are the supported commands", "how can you help me", "what are your options",
            "what features do you support", "show me what you can do", "what is your purpose",
            "what tasks do you handle", "tell me your functionalities", "list your main features",
            "what can you automate", "what are you capable of", "what is your job",
            "show me your skills", "what skills do you have", "what actions can you take",
            "who made jarvis", "who created jarvis", "who built jarvis", "who is minaty",
            "who is the developer of jarvis", "what is the current status of jarvis"
        ]

        specifics = [
            "can you set alarms", "can you play music", "what apps can you open",
            "can you make phone calls", "can you send messages", "can you check the weather",
            "can you tell the time", "can you tell the date", "can you turn on flashlight",
            "can you control the volume", "can you write python code", "can you explain machine learning",
            "can you help with coding", "can you search the web", "can you recall memories",
            "can you remember things", "can you automate routines", "can you track habits",
            "is jarvis a prototype", "are you just a prototype", "is minaty building more features",
            "will jarvis get more functionalities", "will minaty add more functions", "is this assistant a prototype"
        ]

        hindi_variants = [
            "kya kar sakte ho", "tum kya kya kar sakte ho", "capabilities kya hain",
            "features kya hain tumhare", "kaam kya hai tumhara", "tumhari capabilities kya hain",
            "kya tum music chala sakte ho", "kya tum alarm laga sakte ho", "phone call kar sakte ho kya",
            "kya tum app khol sakte ho", "options kya hain", "commands kounsi support karte ho",
            "jarvis kisne banaya", "minaty koun hai", "jarvis prototype hai kya", "kya minaty aur features bana raha hai"
        ]

        templates = [
            "{subject}",
            "tell me {subject}",
            "show me {subject}",
            "can you list {subject}",
            "what are the details of {subject}",
            "do you have {subject}",
            "{specific}",
            "can you tell me if {specific}",
            "do you know if {specific}",
            "is it possible that {specific}",
            "{hindi}",
            "mujhe batao {hindi}",
            "aap {hindi}"
        ]

        texts = []
        for t in templates:
            if "{subject}" in t:
                for sub in subjects:
                    texts.append(t.format(subject=sub))
            elif "{specific}" in t:
                for spec in specifics:
                    texts.append(t.format(specific=spec))
            elif "{hindi}" in t:
                for hin in hindi_variants:
                    texts.append(t.format(hindi=hin))

        texts = [self._add_noise(t) for t in texts]
        random.shuffle(texts)
        return texts

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
                 "1 minute", "15 minute", "30 second", "after 5 min",
                 "5 seconds", "5 second", "after 5 seconds", "after 10 seconds",
                 "after 30 seconds", "10 seconds", "10 second"]
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
        """Generate out-of-scope / unknown examples, including math equations."""
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
            # Conversational greetings & chat
            "wassup bro", "yo what's up", "hey there", "namaste jarvis",
            "radhe radhe", "salaam", "adaab", "hello bot", "aur sunao",
            "kya chal raha hai", "kaisa chal raha hai sab", "sab badhiya?",
            "aur batao", "kuch naya batao", "how was your day", "din kaisa raha",
            "aaj tumne kya kiya", "kya kar rhe ho yaar",
            # Small talk & compliments
            "you are awesome", "you are very helpful", "thank you so much",
            "dhanyawad dost", "thanks a lot", "dil jeet liya tune",
            "bahut badiya kaam kiya", "very good job", "proud of you",
            "tum bahut samajhdar ho", "you are so smart", "gazab",
            # Philosophy, knowledge & LLM prompts
            "explain photosynthesis", "tell me about quantum computing",
            "write a code to print prime numbers", "help me draft an email",
            "what is the capital of India", "who is the prime minister",
            "calculate 25 * 40", "maths equation solve karo",
            "should I buy a house or rent", "give me relationship advice",
            "mujhe tension ho rahi hai", "career guidelines do",
            "how to cook biryani", "recipe for chicken tikka", "chai kaise banate hain",
            "who wrote the play hamlet", "tell me a fun fact", "history of space travel",
            "write a poem about stars", "create a story of a brave knight",
            # Decision-making helpers
            "kya mujhe abhi sona chahiye?", "should I work out today?",
            "is coding better than designing?", "what option is better?",
            "which phone should I buy", "best laptop under 50k", "suggest a good movie",
            "should I learn python or javascript", "give me a dynamic workout plan",
            "how do I improve my memory?", "how to prepare for a coding interview",
        ]
        
        # Dynamically generate math, human science/behavior, and history expressions
        math_ops = ["+", "-", "*", "/", "%", "**"]
        math_templates = [
            "calculate {a} {op} {b}",
            "what is {a} {op} {b}",
            "solve {a} {op} {b}",
            "maths equation {a} {op} {b}",
            "{a} {op} {b} is what",
            "{a} {op} {b} solve karo",
            "{a} {op} {b} kitna hoga",
            "value of {a} {op} {b}"
        ]
        
        behavior_actions = ["sleep", "dream", "cry", "laugh", "socialize", "procrastinate", "feel fear", "form habits", "cooperate", "compete"]
        behavior_concepts = ["cognitive dissonance", "operant conditioning", "social conformity", "neuroplasticity", "groupthink", "altruism", "bystander effect", "confirmation bias", "human psychology", "cognitive psychology", "behavioral science"]
        behavior_templates = [
            "explain {concept} in human psychology",
            "why do humans {action}?",
            "what is the scientific explanation for why humans {action}?",
            "explain human behavior concerning {concept}",
            "how does {concept} influence behavior",
            "what is the psychology behind {action}",
            "human science and behavior: {concept}",
            "why do we {action} when stressed"
        ]
        
        history_events = ["French Revolution", "World War 2", "Industrial Revolution", "Fall of Rome", "Ancient Egypt", "Renaissance", "Magna Carta", "Cold War", "Ottoman Empire", "Mauryan Empire", "American Civil War"]
        history_figures = ["Julius Caesar", "Napoleon", "Alexander the Great", "Mahatma Gandhi", "Abraham Lincoln", "Cleopatra", "Genghis Khan", "Ashoka the Great", "Winston Churchill"]
        history_templates = [
            "what happened during the {event}?",
            "explain the significance of {figure} in history",
            "top historical things about {event}",
            "history of {event}",
            "who was {figure} in historical context",
            "tell me about {figure}",
            "what caused the {event}",
            "list top historical facts about {event}"
        ]
        
        dyn_examples = []
        math_count = count // 4
        behavior_count = count // 4
        history_count = count // 4
        
        # 1. Math
        for _ in range(math_count):
            a = random.randint(1, 1000)
            b = random.randint(1, 1000)
            op = random.choice(math_ops)
            temp = random.choice(math_templates)
            dyn_examples.append(temp.format(a=a, b=b, op=op))
            
        # 2. Behavior
        for _ in range(behavior_count):
            action = random.choice(behavior_actions)
            concept = random.choice(behavior_concepts)
            temp = random.choice(behavior_templates)
            dyn_examples.append(temp.format(action=action, concept=concept))
            
        # 3. History
        for _ in range(history_count):
            event = random.choice(history_events)
            figure = random.choice(history_figures)
            temp = random.choice(history_templates)
            dyn_examples.append(temp.format(event=event, figure=figure))
            
        phrases = unknown_phrases * (count // len(unknown_phrases) + 2)
        random.shuffle(phrases)
        result = phrases[:count - len(dyn_examples)] + dyn_examples
        random.shuffle(result)
        return result

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
            self._gen_setting, self._gen_python_coding, self._gen_ai_news_models, self._gen_capabilities, self._gen_unknown,
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
