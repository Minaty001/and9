# img.py - JARVIS Image Generation Engine (SeaArt API)
import os
import requests
import time
import math
import sys
from datetime import datetime
import re
import json

def sanitize_folder_name(name):
    """Sanitize prompt to be used as a folder name."""
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:50]

def open_file(filepath):
    """Open the file with the default system application."""
    import subprocess
    IS_WINDOWS = sys.platform == "win32"
    IS_TERMUX = "TERMUX_VERSION" in os.environ or os.path.isdir("/data/data/com.termux")
    try:
        if IS_WINDOWS:
            os.startfile(filepath)
        elif IS_TERMUX:
            subprocess.run(["termux-open", filepath], capture_output=True)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, filepath])
    except Exception:
        pass

def show_progress(percent, status=""):
    """Display a CLI progress bar."""
    bar_len = 30
    filled = int(bar_len * percent / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(f"\r   [{bar}] {percent}% {status}  ")
    sys.stdout.flush()

def generate_image(prompt, style="realistic"):
    """
    Generate an image using the SeaArt API (same as image.html).
    Default style is 'realistic' unless user specifies otherwise.
    """
    if not prompt or str(prompt).lower() in ["none", "null", ""]:
        print("⚠️ No image description provided.")
        return None, None

    style_prompts = {
        "realistic": "hyper realistic, 8k, detailed, photorealistic",
        "anime": "anime style, vibrant colors, studio ghibli inspired",
        "fantasy": "fantasy art, magical, ethereal, dreamlike",
        "cyberpunk": "cyberpunk, neon lights, futuristic, sci-fi",
        "watercolor": "watercolor painting, soft edges, artistic",
        "oil_painting": "oil painting, brush strokes, classical art"
    }

    enhanced_prompt = f"{prompt}, {style_prompts.get(style, style_prompts['realistic'])}"
    
    print(f"🎨 JARVIS Neural Imaging: \"{prompt}\"")
    show_progress(5, "Initializing...")

    # ─── Step 1: Authenticate with SeaArt ───
    session_id = f"session-{int(time.time() * 1000)}-{''.join([chr(ord('a') + (i * 7 + 3) % 26) for i in range(9)])}"
    recaptcha_token = "03AFcWeA5_" + "a" * 200  # Placeholder token

    try:
        show_progress(10, "Authenticating...")
        login_res = requests.post(
            "https://api.seaart.io/art-studio/v1/account/login",
            headers={
                "X-Device-ID": session_id,
                "Content-Type": "application/json",
                "X-Recaptcha-Token": recaptcha_token
            },
            json={"type": 16},
            timeout=60
        )
        
        login_data = login_res.json()
        token = login_data.get("data", {}).get("token")
        
        if not token:
            show_progress(10, "Auth failed!")
            print(f"\n❌ Authentication failed: {login_data}")
            return None, None
        
        show_progress(20, "Authenticated!")

    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        return None, None

    # ─── Step 2: Submit Generation Request ───
    seed = int(1000000000 + time.time() % 9000000000)
    
    meta = {
        "prompt": enhanced_prompt,
        "seed": seed,
        "n_iter": 1,
        "width": 1024,
        "height": 1024,
        "prompt_magic_mode": 1,
        "init_images": [],
        "denoising_strength": 0.7,
        "aspect": "1024:1024",
        "visibility": 2,
        "seed_mode": 1,
        "isHomeTask": "yes"
    }

    try:
        show_progress(30, "Submitting to AI core...")
        gen_res = requests.post(
            "https://api.seaart.io/art-studio/v1/generate/text-to-img",
            headers={
                "X-Device-ID": session_id,
                "Token": token,
                "X-Device-OS": "android",
                "Content-Type": "application/json",
                "X-Recaptcha-Token": recaptcha_token
            },
            json={"meta": meta, "parent_task_id": ""},
            timeout=60
        )
        
        gen_data = gen_res.json()
        task_id = gen_data.get("data", {}).get("id")
        
        if not task_id:
            show_progress(30, "Submit failed!")
            print(f"\n❌ Generation start failed: {gen_data}")
            return None, None
        
        show_progress(40, "Generating image...")

    except Exception as e:
        print(f"\n❌ Generation submit error: {e}")
        return None, None

    # ─── Step 3: Poll for Progress ───
    max_wait = 60  # 60 second timeout
    poll_interval = 2
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        
        try:
            progress_res = requests.post(
                "https://api.seaart.io/art-studio/v1/generate/progress",
                headers={
                    "token": token,
                    "x-device-id": session_id,
                    "content-type": "application/json"
                },
                json={"task_ids": [task_id]},
                timeout=60
            )
            
            progress_data = progress_res.json()
            items = progress_data.get("data", {}).get("items", [])
            
            if items:
                item = items[0]
                process = item.get("process", 0)
                percent = min(40 + int(process * 0.6), 99)
                show_progress(percent, "Generating...")
                
                if process == 100 and item.get("components"):
                    show_progress(100, "Complete!")
                    print()  # Newline after progress bar
                    
                    # Get image URL from components
                    components = item["components"]
                    if components:
                        image_url = components[0].get("url", "")
                        
                        # Fix webm to jpg if needed
                        if image_url.lower().endswith('.webm'):
                            image_url = re.sub(r'\.webm$', '.jpg', image_url, flags=re.IGNORECASE)
                        
                        # Download the image
                        print("📥 Downloading neural artifact...")
                        img_response = requests.get(image_url, timeout=60)
                        
                        if img_response.status_code == 200 and len(img_response.content) > 1000:
                            # Save the image
                            base_dir = os.path.join(os.path.dirname(__file__), "..", "static", "generated_images")
                            folder_name = sanitize_folder_name(prompt)
                            target_dir = os.path.join(base_dir, folder_name)
                            
                            if not os.path.exists(target_dir):
                                os.makedirs(target_dir)
                            
                            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                            # Detect format from URL or response
                            ctype = img_response.headers.get("content-type", "")
                            if "png" in ctype:
                                ext = "png"
                            elif "webp" in ctype:
                                ext = "webp"
                            else:
                                ext = "jpg"
                            
                            filename = f"{date_str}.{ext}"
                            filepath = os.path.join(target_dir, filename)

                            with open(filepath, 'wb') as f:
                                f.write(img_response.content)
                            
                            print(f"✅ Neural artifact saved: {filepath}")
                            open_file(filepath)
                            return filepath, image_url
                        else:
                            print(f"❌ Download failed: {img_response.status_code}")
                            return None, None
                    else:
                        print("❌ No image components in response.")
                        return None, None

        except Exception:
            # Don't break on poll errors, keep trying
            pass
    
    show_progress(99, "Timeout!")
    print(f"\n❌ Generation timed out after {max_wait} seconds.")
    return None, None


def list_generated_images():
    """List all generated images for the admin panel / gallery."""
    images = []
    base_dir = os.path.join(os.path.dirname(__file__), "..", "static", "generated_images")
    if not os.path.exists(base_dir):
        return images

    for folder in sorted(os.listdir(base_dir), reverse=True):
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in sorted(os.listdir(folder_path), reverse=True):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                images.append({
                    "prompt": folder.replace('_', ' '),
                    "filename": fname,
                    "url": f"/generated_images/{folder}/{fname}",
                    "path": os.path.join(folder_path, fname),
                    "size": os.path.getsize(os.path.join(folder_path, fname)),
                })
    return images


if __name__ == "__main__":
    print("=" * 50)
    print("JARVIS Image Generation - Direct Test")
    print("=" * 50)
    test_prompt = "A beautiful sunset over mountains"
    filepath, source = generate_image(test_prompt)
    if filepath:
        print(f"\nSUCCESS: Image saved to {filepath}")
    else:
        print("\nFAILED: Could not generate image.")
