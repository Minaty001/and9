// ═══════════════════════════════════════════════
// JARVIS Device Control — Android Accessibility
// ═══════════════════════════════════════════════

const DeviceControl = (() => {

    // ── App URL Schemes (120+ apps) ──
    const APPS = {
        // ── Shopping ──
        'amazon':           { url: 'https://amazon.in', name: 'Amazon' },
        'amazon pay':       { url: 'https://pay.amazon.in', name: 'Amazon Pay' },
        'ajio':             { url: 'https://ajio.com', name: 'Ajio' },
        'flipkart':         { url: 'https://flipkart.com', name: 'Flipkart' },

        // ── Games ──
        'bgmi':             { url: 'intent://#Intent;package=com.pubg.imobile;end', name: 'BGMI' },
        'battlegrounds':    { url: 'intent://#Intent;package=com.pubg.imobile;end', name: 'BGMI' },
        'pubg':             { url: 'intent://#Intent;package=com.pubg.imobile;end', name: 'PUBG' },
        'beta pubg':        { url: 'intent://#Intent;package=com.pubg.imobile.beta;end', name: 'Beta PUBG' },
        'solo leveling':    { url: 'https://play.google.com/store/search?q=solo+leveling+arise', name: 'Solo Leveling' },
        'indian train simulator': { url: 'intent://#Intent;package=com.on4games.its;end', name: 'Indian Train Simulator' },
        'fanfight':         { url: 'https://fanfight.com', name: 'FanFight' },

        // ── Browsers ──
        'brave':            { url: 'https://brave.com', name: 'Brave' },
        'browser':          { url: 'https://google.com', name: 'Browser' },
        'chrome':           { url: 'https://google.com', name: 'Chrome' },
        'chromebook':       { url: 'https://google.com', name: 'Chromebook' },
        'opera':            { url: 'https://opera.com', name: 'Opera' },

        // ── Utilities ──
        'clock':            { url: 'intent://#Intent;package=com.google.android.deskclock;end', name: 'Clock' },
        'compass':          { url: 'https://www.google.com/search?q=compass+online', name: 'Compass' },
        'contacts':         { url: 'intent://#Intent;package=com.google.android.contacts;end', name: 'Contacts' },
        'calculator':       { url: 'https://www.google.com/search?q=calculator', name: 'Calculator' },
        'cloneit':          { url: 'intent://#Intent;package=com.lenovo.anyshare.gps;end', name: 'CloneIt' },
        'easyshare':        { url: 'intent://#Intent;package=com.lenovo.anyshare.gps;end', name: 'EasyShare' },
        'recorder':         { url: 'intent://#Intent;package=com.google.android.apps.recorder;end', name: 'Recorder' },
        'lock':             { url: 'intent://#Intent;action=android.settings.SETTINGS;end', name: 'Lock Settings' },
        'settings':         { url: 'intent://#Intent;action=android.settings.SETTINGS;end', name: 'Settings' },

        // ── File Managers ──
        'file manager':     { url: 'intent://#Intent;package=com.google.android.apps.nbu.files;end', name: 'File Manager' },
        'files':            { url: 'intent://#Intent;package=com.google.android.apps.nbu.files;end', name: 'Files' },
        'files by google':  { url: 'intent://#Intent;package=com.google.android.apps.nbu.files;end', name: 'Files by Google' },
        'es file explorer':  { url: 'intent://#Intent;package=com.estrongs.android.pop;end', name: 'ES File Explorer' },
        'rar':              { url: 'intent://#Intent;package=com.rarlab.rar;end', name: 'RAR' },

        // ── AI / Chat ──
        'character ai':     { url: 'https://character.ai', name: 'Character AI' },
        'c ai':             { url: 'https://character.ai', name: 'Character AI' },
        'gemini':           { url: 'https://gemini.google.com', name: 'Gemini' },
        'gemini generator': { url: 'https://gemini.google.com', name: 'Gemini Generator' },
        'chatgpt':          { url: 'https://chat.openai.com', name: 'ChatGPT' },
        'vanced ai':        { url: 'https://play.google.com/store/search?q=vanced+ai', name: 'Vanced AI' },
        'ai application':   { url: 'https://play.google.com/store/search?q=ai+application', name: 'AI Application' },

        // ── Finance ──
        'digilocker':       { url: 'https://digilocker.gov.in', name: 'DigiLocker' },
        'dailypay':         { url: 'intent://#Intent;package=com.dailypay;end', name: 'DailyPay' },
        'do app':           { url: 'intent://#Intent;package=com.dailypay;end', name: 'DailyPay' },
        'google pay':       { url: 'intent://#Intent;package=com.google.android.apps.nbu.paisa.user;end', name: 'Google Pay' },
        'gpay':             { url: 'intent://#Intent;package=com.google.android.apps.nbu.paisa.user;end', name: 'GPay' },
        'home credit':      { url: 'https://homecredit.co.in', name: 'Home Credit' },
        'mobikwik':         { url: 'https://mobikwik.com', name: 'MobiKwik' },
        'phonepe':          { url: 'intent://#Intent;package=com.phonepe.app;end', name: 'PhonePe' },

        // ── Social ──
        'discord':          { url: 'https://discord.com/app', name: 'Discord' },
        'facebook':         { url: 'https://facebook.com', name: 'Facebook' },
        'instagram':        { url: 'https://instagram.com', name: 'Instagram' },
        'instapro':         { url: 'intent://#Intent;package=com.instapro;end', name: 'InstaPro' },
        'linkedin':         { url: 'https://linkedin.com', name: 'LinkedIn' },
        'messenger':        { url: 'https://messenger.com', name: 'Messenger' },
        'plus messenger':   { url: 'intent://#Intent;package=org.telegram.plus;end', name: 'Plus Messenger' },
        'reddit':           { url: 'https://reddit.com', name: 'Reddit' },
        'snapchat':         { url: 'https://snapchat.com', name: 'Snapchat' },
        'telegram':         { url: 'https://web.telegram.org', name: 'Telegram' },
        'twitter':          { url: 'https://x.com', name: 'Twitter' },
        'x':                { url: 'https://x.com', name: 'X' },
        'whatsapp':         { url: 'https://wa.me', name: 'WhatsApp' },
        'wa business':      { url: 'intent://#Intent;package=com.whatsapp.w4b;end', name: 'WA Business' },
        'whatsapp business': { url: 'intent://#Intent;package=com.whatsapp.w4b;end', name: 'WA Business' },
        'status saver':     { url: 'intent://#Intent;package=com.app.statussaver;end', name: 'Status Saver' },

        // ── Google ──
        'google':           { url: 'https://google.com', name: 'Google' },
        'gmail':            { url: 'https://mail.google.com', name: 'Gmail' },
        'mail':             { url: 'https://mail.google.com', name: 'Gmail' },
        'email':            { url: 'https://mail.google.com', name: 'Gmail' },
        'maps':             { url: 'https://maps.google.com', name: 'Google Maps' },
        'google maps':      { url: 'https://maps.google.com', name: 'Google Maps' },
        'drive':            { url: 'https://drive.google.com', name: 'Google Drive' },
        'photos':           { url: 'https://photos.google.com', name: 'Google Photos' },
        'play store':       { url: 'https://play.google.com/store', name: 'Play Store' },
        'find hub':         { url: 'https://play.google.com/store/search?q=find+hub', name: 'Find Hub' },
        'translate':        { url: 'https://translate.google.com', name: 'Translate' },
        'news':             { url: 'https://news.google.com', name: 'Google News' },
        'weather':          { url: 'https://weather.google.com', name: 'Weather' },

        // ── Communication ──
        'phone':            { url: 'tel:', name: 'Phone' },
        'messages':         { url: 'sms:', name: 'Messages' },

        // ── Media / Music ──
        'music':            { url: 'https://open.spotify.com', name: 'Music' },
        'spotify':          { url: 'https://open.spotify.com', name: 'Spotify' },
        'mx player':        { url: 'intent://#Intent;package=com.mxtech.videoplayer.ad;end', name: 'MX Player' },
        'mx player pro':    { url: 'intent://#Intent;package=com.mxtech.videoplayer.pro;end', name: 'MX Player Pro' },
        'poweramp':         { url: 'intent://#Intent;package=com.maxmpz.audioplayer;end', name: 'Poweramp' },
        'youtube':          { url: 'https://youtube.com', name: 'YouTube' },
        'yt studio':        { url: 'https://studio.youtube.com', name: 'YT Studio' },
        'youtube studio':   { url: 'https://studio.youtube.com', name: 'YT Studio' },
        'netflix':          { url: 'https://netflix.com', name: 'Netflix' },
        'video':            { url: 'intent://#Intent;package=com.google.android.apps.photos;end', name: 'Video' },
        'videos':           { url: 'https://youtube.com', name: 'Videos' },
        'video downloader hub': { url: 'intent://#Intent;package=free.tube.premium.advanced.download;end', name: 'Video Downloader Hub' },
        'shazam':           { url: 'https://shazam.com', name: 'Shazam' },

        // ── Dev / Coding ──
        'github':           { url: 'https://github.com', name: 'GitHub' },
        'html editor':      { url: 'intent://#Intent;package=com.nicedeveloper.htmleditor;end', name: 'HTML Editor' },
        'pydroid 3':        { url: 'intent://#Intent;package=ru.iiec.pydroid3;end', name: 'Pydroid 3' },
        'pydroid':          { url: 'intent://#Intent;package=ru.iiec.pydroid3;end', name: 'Pydroid 3' },
        'termux':           { url: 'intent://#Intent;package=com.termux;end', name: 'Termux' },
        'termux api':       { url: 'intent://#Intent;package=com.termux.api;end', name: 'Termux API' },
        'termux-api':       { url: 'intent://#Intent;package=com.termux.api;end', name: 'Termux API' },

        // ── Productivity ──
        'excel':            { url: 'https://office.live.com/start/Excel.aspx', name: 'Excel' },
        'mega notes':       { url: 'intent://#Intent;package=com.megamobile.notes;end', name: 'Mega Notes' },
        'notes':            { url: 'intent://#Intent;package=com.google.android.keep;end', name: 'Notes' },
        'link to windows':  { url: 'intent://#Intent;package=com.microsoft.appmanager;end', name: 'Link to Windows' },
        'onebox':           { url: 'intent://#Intent;package=com.one.box;end', name: 'OneBox' },
        'wondershare':      { url: 'https://wondershare.com', name: 'Wondershare' },

        // ── Cloud / Storage ──
        'mega':             { url: 'https://mega.nz', name: 'MEGA' },
        'jiocloud':         { url: 'intent://#Intent;package=com.jio.media.jiocloud;end', name: 'JioCloud' },
        'terabox':          { url: 'https://terabox.com', name: 'TeraBox' },
        'vivocloud':        { url: 'intent://#Intent;package=com.bbk.cloud;end', name: 'vivoCloud' },

        // ── Photo / Video Editing ──
        'picsart':          { url: 'https://picsart.com', name: 'Picsart' },
        'motion ninja':     { url: 'intent://#Intent;package=com.vlogstar.videoeditor;end', name: 'Motion Ninja' },

        // ── Security ──
        'kaspersky':        { url: 'intent://#Intent;package=com.kms.free;end', name: 'Kaspersky' },
        'gps emulator':     { url: 'intent://#Intent;package=com.rosteam.gpsemulator;end', name: 'GPS Emulator' },

        // ── Vivo / Device Specific ──
        'themes':           { url: 'intent://#Intent;package=com.bbk.theme;end', name: 'Themes' },
        'vivo store':       { url: 'intent://#Intent;package=com.vivo.appstore;end', name: 'vivo Store' },
        'v app store':      { url: 'intent://#Intent;package=com.vivo.appstore;end', name: 'V-App Store' },
        'v-app store':      { url: 'intent://#Intent;package=com.vivo.appstore;end', name: 'V-App Store' },
        'vi app':           { url: 'intent://#Intent;package=com.mventus.selfcare.activity;end', name: 'Vi App' },
        'idea':             { url: 'intent://#Intent;package=com.mventus.selfcare.activity;end', name: 'Idea/Vi' },
        'game center':      { url: 'intent://#Intent;package=com.vivo.game;end', name: 'Game Center' },

        // ── Jio ──
        'myjio':            { url: 'intent://#Intent;package=com.jio.myjio;end', name: 'MyJio' },
        'my jio':           { url: 'intent://#Intent;package=com.jio.myjio;end', name: 'MyJio' },

        // ── Custom / Misc ──
        'red-x rom':        { url: 'intent://#Intent;package=com.redxrom;end', name: 'RED-X ROM' },
        'red x rom':        { url: 'intent://#Intent;package=com.redxrom;end', name: 'RED-X ROM' },
        'redx rom box':     { url: 'intent://#Intent;package=com.redxrom;end', name: 'RED-X ROM Box' },
        'red-x rom box':    { url: 'intent://#Intent;package=com.redxrom;end', name: 'RED-X ROM Box' },
        'hifox':            { url: 'intent://#Intent;package=com.nicedeveloper.hifox;end', name: 'HiFoX' },
        'mahasar':          { url: 'intent://#Intent;package=com.mahasar;end', name: 'Mahasar' },
        'medisim':          { url: 'intent://#Intent;package=com.medisim;end', name: 'MediSim' },
        'meri lunder':      { url: 'intent://#Intent;package=com.merilunder;end', name: 'Meri Lunder' },
        'mobile1':          { url: 'intent://#Intent;package=com.mobile1;end', name: 'Mobile1' },
        'open health':      { url: 'intent://#Intent;package=com.openhealth;end', name: 'Open Health' },
        'root':             { url: 'intent://#Intent;package=com.roottool;end', name: 'Root Tool' },
        'root tool':        { url: 'intent://#Intent;package=com.roottool;end', name: 'Root Tool' },
        'taptap':           { url: 'https://taptap.io', name: 'TapTap' },
        'toolkit':          { url: 'intent://#Intent;package=com.toolkit;end', name: 'Toolkit' },
        'feedback':         { url: 'intent://#Intent;package=com.bbk.feedback;end', name: 'FeedBack' },
        'jarvis':           { url: '/', name: 'JARVIS (You\'re here!)' },
    };

    // ── Flashlight state ──
    let torchStream = null;
    let torchTrack = null;

    // ══════════════ Command Router ══════════════

    function handle(message) {
        const msg = message.toLowerCase().replace(/[.,!?]/g, '').replace(/\s+/g, ' ').trim();

        // Open app
        const openMatch = msg.match(/^(?:open|launch|start|go to)\s+(.+)$/);
        if (openMatch) return openApp(openMatch[1].trim());

        // Close app / go back
        if (/^(?:close|exit|go back|back)/.test(msg)) return goBack();

        // Play music
        const playMatch = msg.match(/^(?:play|play music|play song|play video)\s*(.*)$/);
        if (playMatch) return playMedia(playMatch[1].trim());

        // Search
        const searchMatch = msg.match(/^(?:search|search for|google|look up)\s+(.+)$/);
        if (searchMatch) return webSearch(searchMatch[1].trim());

        // Phone call
        const callMatch = msg.match(/^(?:call|dial|phone)\s+(.+)$/);
        if (callMatch) return makeCall(callMatch[1].trim());

        // Send message/SMS
        const smsMatch = msg.match(/^(?:send message|send sms|text|message)\s+(?:to\s+)?(.+)$/);
        if (smsMatch) return sendSMS(smsMatch[1].trim());

        // Navigate
        const navMatch = msg.match(/^(?:navigate to|directions to|take me to|go to location)\s+(.+)$/);
        if (navMatch) return navigate(navMatch[1].trim());

        // Flashlight
        if (/(?:flashlight|torch|flash)\s*(?:on|enable|start)/.test(msg)) return flashlight(true);
        if (/(?:flashlight|torch|flash)\s*(?:off|disable|stop)/.test(msg)) return flashlight(false);
        if (/(?:turn on|switch on)\s*(?:flashlight|torch|flash)/.test(msg)) return flashlight(true);
        if (/(?:turn off|switch off)\s*(?:flashlight|torch|flash)/.test(msg)) return flashlight(false);

        // Battery
        if (/(?:battery|charge|power)\s*(?:status|level|percentage|info)?/.test(msg)) return batteryStatus();

        // Volume
        if (/(?:volume up|increase volume|louder)/.test(msg)) return volumeControl('up');
        if (/(?:volume down|decrease volume|quieter|softer)/.test(msg)) return volumeControl('down');
        if (/(?:mute|silent|silence)/.test(msg)) return volumeControl('mute');
        if (/(?:unmute|sound on)/.test(msg)) return volumeControl('unmute');

        // Fullscreen
        if (/(?:fullscreen|full screen|immersive)/.test(msg)) return toggleFullscreen();

        // Share
        if (/^(?:share|share this)/.test(msg)) return shareContent(msg);

        // Time
        if (/(?:what time|current time|time now|what's the time)/.test(msg)) return getTime();

        // Date
        if (/(?:what date|today's date|what day|current date)/.test(msg)) return getDate();

        // Copy
        const copyMatch = msg.match(/^(?:copy)\s+(.+)$/);
        if (copyMatch) return copyText(copyMatch[1].trim());

        // Set alarm (opens clock app)
        if (/(?:set alarm|alarm|set timer|timer|stopwatch)/.test(msg)) return openClock();

        // Camera
        if (/(?:open camera|take photo|take picture|take selfie|camera)/.test(msg)) return openCamera();

        // Brightness (not possible from web)
        if (/(?:brightness)/.test(msg)) return notSupported('Brightness control');

        // WiFi/Bluetooth (not possible from web)
        if (/(?:wifi|wi-fi|bluetooth)/.test(msg)) return notSupported('WiFi/Bluetooth control');

        // Screenshot (not possible from web)
        if (/(?:screenshot|screen capture)/.test(msg)) return notSupported('Screenshot');

        // Not a device command
        return null;
    }

    // ══════════════ Actions ══════════════

    function openApp(appName) {
        const key = appName.toLowerCase().trim();
        const app = APPS[key];
        if (app) {
            window.open(app.url, '_blank');
            return { reply: `Opening ${app.name}.`, speak: `Opening ${app.name}` };
        }
        // Try as a URL
        if (key.includes('.')) {
            const url = key.startsWith('http') ? key : 'https://' + key;
            window.open(url, '_blank');
            return { reply: `Opening ${key}.`, speak: `Opening ${key}` };
        }
        // Search for the app
        window.open(`https://www.google.com/search?q=${encodeURIComponent(appName + ' app')}`, '_blank');
        return { reply: `Searching for ${appName}...`, speak: `Searching for ${appName}` };
    }

    function goBack() {
        return { reply: 'Going back.', speak: 'Going back' };
    }

    function playMedia(query) {
        if (!query || query === 'music' || query === 'song' || query === 'something') {
            // Open Spotify or YouTube Music
            window.open('https://open.spotify.com', '_blank');
            return { reply: 'Opening Spotify.', speak: 'Opening Spotify for music' };
        }

        // Check if they specified a platform
        const onYoutube = query.match(/(.+?)\s+on\s+youtube$/i);
        const onSpotify = query.match(/(.+?)\s+on\s+spotify$/i);

        if (onYoutube) {
            const q = onYoutube[1];
            window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`, '_blank');
            return { reply: `Playing "${q}" on YouTube.`, speak: `Playing ${q} on YouTube` };
        }

        if (onSpotify) {
            const q = onSpotify[1];
            window.open(`https://open.spotify.com/search/${encodeURIComponent(q)}`, '_blank');
            return { reply: `Searching "${q}" on Spotify.`, speak: `Searching ${q} on Spotify` };
        }

        // Default: search on YouTube
        window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`, '_blank');
        return { reply: `Playing "${query}" on YouTube.`, speak: `Playing ${query} on YouTube` };
    }

    function webSearch(query) {
        window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, '_blank');
        return { reply: `Searching for "${query}".`, speak: `Searching for ${query}` };
    }

    function makeCall(number) {
        // Clean the number
        const cleaned = number.replace(/[^0-9+]/g, '');
        if (cleaned) {
            window.location.href = `tel:${cleaned}`;
            return { reply: `Calling ${number}.`, speak: `Calling ${number}` };
        }
        return { reply: `I need a phone number to call.`, speak: `Please provide a phone number` };
    }

    function sendSMS(target) {
        const cleaned = target.replace(/[^0-9+]/g, '');
        if (cleaned) {
            window.location.href = `sms:${cleaned}`;
            return { reply: `Opening messages for ${target}.`, speak: `Opening messages` };
        }
        window.location.href = 'sms:';
        return { reply: 'Opening messages.', speak: 'Opening messages' };
    }

    function navigate(place) {
        window.open(`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(place)}`, '_blank');
        return { reply: `Getting directions to ${place}.`, speak: `Navigating to ${place}` };
    }

    async function flashlight(on) {
        try {
            if (on) {
                if (torchStream) {
                    return { reply: 'Flashlight is already on.', speak: 'Flashlight is already on' };
                }
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment' }
                });
                const track = stream.getVideoTracks()[0];
                await track.applyConstraints({ advanced: [{ torch: true }] });
                torchStream = stream;
                torchTrack = track;
                return { reply: '🔦 Flashlight ON.', speak: 'Flashlight on' };
            } else {
                if (torchTrack) {
                    torchTrack.stop();
                    torchTrack = null;
                }
                if (torchStream) {
                    torchStream.getTracks().forEach(t => t.stop());
                    torchStream = null;
                }
                return { reply: '🔦 Flashlight OFF.', speak: 'Flashlight off' };
            }
        } catch (e) {
            return { reply: 'Flashlight not available on this device.', speak: 'Flashlight not available' };
        }
    }

    async function batteryStatus() {
        try {
            if ('getBattery' in navigator) {
                const battery = await navigator.getBattery();
                const level = Math.round(battery.level * 100);
                const charging = battery.charging ? 'charging' : 'not charging';
                let timeInfo = '';
                if (battery.charging && battery.chargingTime !== Infinity) {
                    timeInfo = `. Full in ${Math.round(battery.chargingTime / 60)} minutes`;
                } else if (!battery.charging && battery.dischargingTime !== Infinity) {
                    timeInfo = `. ${Math.round(battery.dischargingTime / 60)} minutes remaining`;
                }
                return {
                    reply: `🔋 Battery: ${level}% (${charging})${timeInfo}.`,
                    speak: `Battery is at ${level} percent and ${charging}${timeInfo}`
                };
            }
            return { reply: 'Battery API not available.', speak: 'Cannot check battery on this browser' };
        } catch (e) {
            return { reply: 'Battery info unavailable.', speak: 'Battery info unavailable' };
        }
    }

    function volumeControl(action) {
        // Web can't control system volume, but we can provide guidance
        const tips = {
            'up': 'Use the volume buttons on the side of your phone to increase volume.',
            'down': 'Use the volume buttons on the side of your phone to decrease volume.',
            'mute': 'Use the volume button to mute, or toggle Do Not Disturb from quick settings.',
            'unmute': 'Use the volume button to unmute your device.',
        };
        return {
            reply: `🔊 ${tips[action]}`,
            speak: tips[action]
        };
    }

    function toggleFullscreen() {
        try {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
                return { reply: '🖥️ Fullscreen mode enabled.', speak: 'Fullscreen mode on' };
            } else {
                document.exitFullscreen();
                return { reply: '🖥️ Exited fullscreen.', speak: 'Exited fullscreen' };
            }
        } catch (e) {
            return { reply: 'Fullscreen not supported.', speak: 'Fullscreen not available' };
        }
    }

    async function shareContent(msg) {
        try {
            if (navigator.share) {
                await navigator.share({
                    title: 'JARVIS',
                    text: 'Check out JARVIS — AI Assistant',
                    url: window.location.href
                });
                return { reply: '📤 Share dialog opened.', speak: 'Sharing' };
            }
            return { reply: 'Share not supported on this browser.', speak: 'Sharing not available' };
        } catch (e) {
            return { reply: 'Share cancelled.', speak: 'Share cancelled' };
        }
    }

    function getTime() {
        const now = new Date();
        const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
        return { reply: `🕐 Current time: ${time}`, speak: `The current time is ${time}` };
    }

    function getDate() {
        const now = new Date();
        const date = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        return { reply: `📅 Today: ${date}`, speak: `Today is ${date}` };
    }

    async function copyText(text) {
        try {
            await navigator.clipboard.writeText(text);
            return { reply: `📋 Copied: "${text}"`, speak: `Copied to clipboard` };
        } catch (e) {
            return { reply: 'Clipboard access denied.', speak: 'Cannot copy, clipboard access denied' };
        }
    }

    function openClock() {
        // Try Android intent, fallback to Google search
        window.open('https://www.google.com/search?q=set+alarm', '_blank');
        return { reply: '⏰ Opening alarm/timer.', speak: 'Opening alarm' };
    }

    function openCamera() {
        // Create a hidden file input to trigger camera
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.capture = 'environment';
        input.click();
        return { reply: '📷 Opening camera.', speak: 'Opening camera' };
    }

    function notSupported(feature) {
        return {
            reply: `⚠️ ${feature} cannot be controlled from a web browser. Use your device settings.`,
            speak: `Sorry, ${feature} cannot be controlled from the browser. Please use your device settings.`
        };
    }

    async function handleRemoteAction(data) {
        if (data.intent) {
            if (window.AndroidBridge && window.AndroidBridge.executeIntent) {
                try {
                    window.AndroidBridge.executeIntent(JSON.stringify(data.intent));
                    return;
                } catch (e) {
                    console.error("Failed to execute intent via bridge:", e);
                }
            }
        }

        const metadata = data.metadata || data;
        const action = metadata.action;
        const payload = metadata.payload || {};

        if (action === 'set_alarm') {
            const hour = parseInt(payload.hour, 10) || 7;
            const minute = parseInt(payload.minute, 10) || 0;
            const label = payload.label || 'Jarvis Alarm';
            if (window.AndroidBridge && window.AndroidBridge.setAlarm) {
                window.AndroidBridge.setAlarm(hour, minute, label);
            } else {
                window.open(`https://www.google.com/search?q=set+alarm+for+${hour}:${minute}+called+${encodeURIComponent(label)}`, '_blank');
            }
        }
        else if (action === 'make_call') {
            const number = payload.number;
            if (window.AndroidBridge && window.AndroidBridge.makeCall) {
                window.AndroidBridge.makeCall(number);
            } else {
                window.location.href = `tel:${number}`;
            }
        }
        else if (action === 'call_contact') {
            const name = payload.name;
            if (window.AndroidBridge && window.AndroidBridge.getContacts) {
                const contactsStr = window.AndroidBridge.getContacts();
                const contacts = JSON.parse(contactsStr);
                const query = name.toLowerCase().trim();
                let matchedContact = null;
                for (const c of contacts) {
                    if (c.name.toLowerCase().includes(query)) {
                        matchedContact = c;
                        break;
                    }
                }
                if (matchedContact) {
                    responseText.textContent = `Calling ${matchedContact.name} (${matchedContact.number})...`;
                    speak(`Calling ${matchedContact.name}`);
                    window.AndroidBridge.makeCall(matchedContact.number);
                } else {
                    responseText.textContent = `I couldn't find ${name} in your contacts.`;
                    speak(`I couldn't find ${name} in your contacts.`);
                }
            } else {
                responseText.textContent = "Contacts access is not available on this browser.";
                speak("Contacts access is not available.");
            }
        }
        else if (action === 'create_file') {
            const path = payload.path;
            const content = payload.content;
            if (window.AndroidBridge && window.AndroidBridge.createFile) {
                const success = window.AndroidBridge.createFile(path, content);
                if (success) {
                    responseText.textContent = `File successfully created at ${path}`;
                    speak("File created successfully.");
                } else {
                    responseText.textContent = `Failed to create file at ${path}`;
                    speak("Failed to create file.");
                }
            } else {
                responseText.textContent = "File writing is only supported within the Android App.";
                speak("File operations are only supported in the app.");
            }
        }
        else if (action === 'read_file') {
            const path = payload.path;
            if (window.AndroidBridge && window.AndroidBridge.readFile) {
                const content = window.AndroidBridge.readFile(path);
                if (content === '__FILE_NOT_FOUND__') {
                    responseText.textContent = `File not found: ${path}`;
                    speak("File not found.");
                } else if (content.startsWith('__ERROR:')) {
                    responseText.textContent = `Error reading file: ${content}`;
                    speak("Error reading file.");
                } else {
                    responseText.textContent = `Content of ${path}:\n\n${content}`;
                    speak(`Reading file content.`);
                }
            } else {
                responseText.textContent = "File reading is only supported within the Android App.";
                speak("File operations are only supported in the app.");
            }
        }
        else if (action === 'list_directory') {
            const path = payload.path;
            if (window.AndroidBridge && window.AndroidBridge.listDirectory) {
                const filesStr = window.AndroidBridge.listDirectory(path);
                const files = JSON.parse(filesStr);
                if (files.length === 0) {
                    responseText.textContent = `No files found in directory: ${path}`;
                    speak("Directory is empty.");
                } else {
                    let lines = [`Files in ${path}:`];
                    for (const f of files) {
                        const type = f.isDirectory ? '📁' : '📄';
                        const size = f.isDirectory ? '' : ` (${f.size} bytes)`;
                        lines.push(`  ${type} ${f.name}${size}`);
                    }
                    responseText.textContent = lines.join('\n');
                    speak(`Found ${files.length} items.`);
                }
            } else {
                responseText.textContent = "Directory listing is only supported within the Android App.";
                speak("Directory listing is only supported in the app.");
            }
        }
        else if (action === 'delete_file') {
            const path = payload.path;
            if (window.AndroidBridge && window.AndroidBridge.deleteFile) {
                const success = window.AndroidBridge.deleteFile(path);
                if (success) {
                    responseText.textContent = `Deleted file: ${path}`;
                    speak("File deleted.");
                } else {
                    responseText.textContent = `Failed to delete file or file doesn't exist: ${path}`;
                    speak("Failed to delete file.");
                }
            } else {
                responseText.textContent = "File deletion is only supported within the Android App.";
                speak("File operations are only supported in the app.");
            }
        }
    }

    // ── Public API ──
    return { handle, handleRemoteAction };
})();
