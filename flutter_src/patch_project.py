import os
import shutil
import sqlite3
from datetime import datetime

def log_activity(query: str, intent: str, action: str, result: str, details: str):
    db_path = "/home/saifali/and9/activities.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO activities (timestamp, query, intent, action, result, details) VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, query, intent, action, result, details)
        )
        conn.commit()
        conn.close()
        print("Logged activity to database.")
    except Exception as e:
        print(f"Failed to log activity: {e}")

def patch():
    client_dir = "/home/saifali/and9/flutter_client"
    src_dir = "/home/saifali/and9/flutter_src"

    if not os.path.exists(client_dir):
        print(f"Client directory {client_dir} does not exist!")
        return False

    print("Copying main.dart...")
    shutil.copy(
        os.path.join(src_dir, "main.dart"),
        os.path.join(client_dir, "lib", "main.dart")
    )

    print("Copying AndroidManifest.xml...")
    manifest_dest = os.path.join(client_dir, "android", "app", "src", "main", "AndroidManifest.xml")
    os.makedirs(os.path.dirname(manifest_dest), exist_ok=True)
    shutil.copy(
        os.path.join(src_dir, "AndroidManifest.xml"),
        manifest_dest
    )

    print("Patching pubspec.yaml...")
    pubspec_path = os.path.join(client_dir, "pubspec.yaml")
    with open(pubspec_path, "r") as f:
        content = f.read()

    dependencies_marker = "dependencies:\n  flutter:\n    sdk: flutter"
    new_deps = (
        "dependencies:\n"
        "  flutter:\n"
        "    sdk: flutter\n"
        "  http: ^1.2.1\n"
        "  permission_handler: ^11.3.1\n"
        "  shared_preferences: ^2.2.3\n"
        "  url_launcher: ^6.3.0\n"
    )
    if dependencies_marker in content:
        content = content.replace(dependencies_marker, new_deps)
    else:
        # fallback if format is slightly different
        content = content.replace("dependencies:", "dependencies:\n  http: ^1.2.1\n  permission_handler: ^11.3.1\n  shared_preferences: ^2.2.3\n  url_launcher: ^6.3.0\n")

    with open(pubspec_path, "w") as f:
        f.write(content)

    print("Patching android/app/build.gradle.kts...")
    gradle_path = os.path.join(client_dir, "android", "app", "build.gradle.kts")
    if os.path.exists(gradle_path):
        with open(gradle_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            # Change minSdk = ... to minSdk = 28
            if "minSdk =" in line:
                indent = line[:line.find("minSdk =")]
                new_lines.append(f"{indent}minSdk = 28\n")
            # Change targetSdk = ... to targetSdk = 36
            elif "targetSdk =" in line:
                indent = line[:line.find("targetSdk =")]
                new_lines.append(f"{indent}targetSdk = 36\n")
            # Change compileSdk = ... to compileSdk = 36
            elif "compileSdk =" in line:
                indent = line[:line.find("compileSdk =")]
                new_lines.append(f"{indent}compileSdk = 36\n")
            # Change applicationId = ... to "com.jarvis.assistant.flutter"
            elif "applicationId =" in line:
                indent = line[:line.find("applicationId =")]
                new_lines.append(f'{indent}applicationId = "com.jarvis.assistant.flutter"\n')
            else:
                new_lines.append(line)

        with open(gradle_path, "w") as f:
            f.writelines(new_lines)
    else:
        print("Warning: build.gradle.kts not found!")

    print("Patching complete!")
    return True

if __name__ == "__main__":
    if patch():
        log_activity(
            query="create a apk which connected localhost:8000 and its has all permissions which its needs",
            intent="CREATE_FLUTTER_APK",
            action="patch_project",
            result="success",
            details="Patched Flutter client files with custom main.dart, permissions, and dependencies."
        )
