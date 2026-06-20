#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD_APK = ROOT / 'jarvis.apk'
WORK_DIR = ROOT / 'apk_work' / 'rebuild_assist'
FRAMEWORK = Path('/usr/share/android-framework-res/framework-res.apk')

if not OLD_APK.is_file():
    raise FileNotFoundError(f'Expected APK not found at {OLD_APK}')
if not FRAMEWORK.is_file():
    raise FileNotFoundError(f'Framework APK not found at {FRAMEWORK}')

if WORK_DIR.exists():
    shutil.rmtree(WORK_DIR)
WORK_DIR.mkdir(parents=True, exist_ok=True)

print('[1/5] Extracting...')
with zipfile.ZipFile(OLD_APK) as z:
    z.extractall(WORK_DIR / 'old')

MANIFEST = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.jarvis.app"
    android:versionCode="5"
    android:versionName="1.4">
    <uses-sdk android:minSdkVersion="28" android:targetSdkVersion="35" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <application
        android:label="JARVIS"
        android:icon="@drawable/icon"
        android:usesCleartextTraffic="true"
        android:theme="@android:style/Theme.NoTitleBar">
        
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".JarvisVoiceInteractionService"
            android:label="JARVIS Assistant"
            android:permission="android.permission.BIND_VOICE_INTERACTION"
            android:exported="true">
            <meta-data
                android:name="android.voice_interaction"
                android:resource="@xml/voice_interaction_service" />
            <intent-filter>
                <action android:name="android.service.voice.VoiceInteractionService" />
                <category android:name="android.intent.category.DEFAULT" />
            </intent-filter>
        </service>

        <service
            android:name=".JarvisVoiceInteractionSessionService"
            android:permission="android.permission.BIND_VOICE_INTERACTION"
            android:exported="true" />
            
    </application>
</manifest>'''

manifest_path = WORK_DIR / 'AndroidManifest.xml'
with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(MANIFEST)

# Write voice_interaction_service.xml
xml_dir = WORK_DIR / 'old' / 'res' / 'xml'
xml_dir.mkdir(parents=True, exist_ok=True)
VOICE_INT_XML = '''<?xml version="1.0" encoding="utf-8"?>
<voice-interaction-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:sessionService="com.jarvis.app.JarvisVoiceInteractionSessionService"
    android:supportsAssist="true"
    android:supportsLocalInteraction="true" />
'''
with open(xml_dir / 'voice_interaction_service.xml', 'w', encoding='utf-8') as f:
    f.write(VOICE_INT_XML)

print('[2/5] Packaging...')
r = subprocess.run([
    'aapt','package','-f','-M',str(manifest_path),
    '-S',str(WORK_DIR / 'old' / 'res'),
    '-I',str(FRAMEWORK),
    '-F',str(WORK_DIR / 'unaligned.apk'),
    '--min-sdk-version','28','--target-sdk-version','35'
], capture_output=True, text=True)
if r.returncode != 0: print(r.stderr[:500]); sys.exit(1)

print('[3/5] Adding dex...')
with zipfile.ZipFile(WORK_DIR / 'unaligned.apk', 'a') as apk:
    apk.write(WORK_DIR / 'old' / 'classes.dex', 'classes.dex')
    if (ROOT / 'apk_work' / 'classes2.dex').is_file():
        apk.write(ROOT / 'apk_work' / 'classes2.dex', 'classes2.dex')

print('[4/5] Zipalign...')
subprocess.run(['zipalign','-f','4',str(WORK_DIR / 'unaligned.apk'),str(WORK_DIR / 'aligned.apk')], check=True)

print('[5/5] Signing...')
ks = WORK_DIR / 'jarvis.keystore'
subprocess.run([
    'keytool','-genkeypair','-v','-keystore',str(ks),
    '-keyalg','RSA','-keysize','2048','-validity','10000',
    '-alias','jarvis','-storepass','jarvis123','-keypass','jarvis123',
    '-dname','CN=JARVIS,O=Jarvis,C=IN'
], capture_output=True, check=True)
final = WORK_DIR / 'final.apk'
subprocess.run([
    'apksigner','sign','--ks',str(ks),
    '--ks-pass','pass:jarvis123','--key-pass','pass:jarvis123',
    '--ks-key-alias','jarvis','--out',str(final),str(WORK_DIR / 'aligned.apk')
], check=True)

shutil.copy2(final, OLD_APK)
print()
r = subprocess.run(['aapt','dump','badging',str(OLD_APK)], capture_output=True, text=True)
for l in r.stdout.split(chr(10)):
    if 'permission' in l or 'package:' in l or 'service' in l: print(' ',l)
print()
print('Done! v1.4')
