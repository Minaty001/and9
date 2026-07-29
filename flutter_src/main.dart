import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JarvisApp());
}

class JarvisApp extends StatelessWidget {
  const JarvisApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JARVIS PCOS Client',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        primaryColor: const Color(0xFF00E5FF),
        scaffoldBackgroundColor: const Color(0xFF0A0E17),
        cardColor: const Color(0xFF151D2A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00E5FF),
          secondary: Color(0xFF8A2BE2),
          surface: Color(0xFF151D2A),
        ),
      ),
      home: const ChatScreen(),
    );
  }
}

class Message {
  final String text;
  final bool isUser;
  final String? agent;
  final String? imageUrl;
  final String? youtubeUrl;
  final String? intent;

  Message({
    required this.text,
    required this.isUser,
    this.agent,
    this.imageUrl,
    this.youtubeUrl,
    this.intent,
  });
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({Key? key}) : super(key: key);

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<Message> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  String _serverUrl = "http://10.0.2.2:8000";
  bool _isConnected = false;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
    _messages.add(Message(
      text: "System initialized. JARVIS PCOS ready at your service.",
      isUser: false,
      agent: "system",
    ));
    _requestAllPermissions();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _serverUrl = prefs.getString("server_url") ?? "http://10.0.2.2:8000";
    });
    _checkConnection();
  }

  Future<void> _saveSettings(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString("server_url", url);
    setState(() {
      _serverUrl = url;
    });
    _checkConnection();
  }

  Future<void> _checkConnection() async {
    try {
      final response = await http.get(Uri.parse("$_serverUrl/health")).timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data["status"] == "ok") {
          setState(() {
            _isConnected = true;
          });
          return;
        }
      }
    } catch (_) {}
    setState(() {
      _isConnected = false;
    });
  }

  Future<void> _requestAllPermissions() async {
    // Request typical permissions required by JARVIS
    Map<Permission, PermissionStatus> statuses = await [
      Permission.microphone,
      Permission.contacts,
      Permission.phone,
      Permission.notification,
      Permission.systemAlertWindow, // overlay
    ].request();
    
    // Check and log permissions
    debugPrint("Permission statuses: $statuses");
  }

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    _controller.clear();

    setState(() {
      _messages.add(Message(text: text, isUser: true));
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final response = await http.post(
        Uri.parse("$_serverUrl/api/chat"),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"message": text}),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _messages.add(Message(
            text: data["reply"] ?? "No response",
            isUser: false,
            agent: data["agent"],
            imageUrl: data["image_url"],
            youtubeUrl: data["youtube_url"],
            intent: data["intent"],
          ));
          _isConnected = true;
        });

        // If there's an intent, execute it via basic actions
        if (data["intent"] != null) {
          _handleIntent(data["intent"], data["metadata"]);
        }
      } else {
        setState(() {
          _messages.add(Message(
            text: "Error: Server returned code ${response.statusCode}",
            isUser: false,
            agent: "system",
          ));
        });
      }
    } catch (e) {
      setState(() {
        _messages.add(Message(
          text: "Failed to connect to backend: $e",
          isUser: false,
          agent: "system",
        ));
        _isConnected = false;
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
      _scrollToBottom();
    }
  }

  void _handleIntent(String intent, Map<String, dynamic>? metadata) async {
    // Basic native fallback handlers
    if (intent.startsWith("CALL")) {
      final phone = metadata?["phone"] ?? metadata?["number"];
      if (phone != null) {
        final url = Uri.parse("tel:$phone");
        if (await canLaunchUrl(url)) {
          await launchUrl(url);
        }
      }
    } else if (intent.startsWith("PLAY_VIDEO") || metadata?["youtube_url"] != null) {
      final videoUrl = metadata?["youtube_url"] ?? metadata?["url"];
      if (videoUrl != null) {
        final url = Uri.parse(videoUrl);
        if (await canLaunchUrl(url)) {
          await launchUrl(url, mode: LaunchMode.externalApplication);
        }
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showSettingsDialog() {
    final textController = TextEditingController(text: _serverUrl);
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text("JARVIS Server Configuration"),
          content: TextField(
            controller: textController,
            decoration: const InputDecoration(
              labelText: "Server Base URL",
              hintText: "http://10.0.2.2:8000",
              border: OutlineInputBorder(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text("Cancel"),
            ),
            ElevatedButton(
              onPressed: () {
                _saveSettings(textController.text.trim());
                Navigator.pop(context);
              },
              child: const Text("Save & Connect"),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.psychology, color: Color(0xFF00E5FF)),
            const SizedBox(width: 8),
            const Text(
              "JARVIS PCOS",
              style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSettingsDialog,
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4.0),
          child: Container(
            color: _isConnected ? const Color(0xFF00E5FF) : Colors.red,
            height: 2.0,
          ),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0A0E17), Color(0xFF121B2D)],
          ),
        ),
        child: Column(
          children: [
            // Status bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              color: const Color(0xFF151D2A),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    "Server: $_serverUrl",
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _isConnected ? Colors.green : Colors.red,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _isConnected ? "ONLINE" : "OFFLINE",
                        style: TextStyle(
                          color: _isConnected ? Colors.green : Colors.red,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            
            // Messages
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.all(16.0),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final msg = _messages[index];
                  return _buildMessageItem(msg);
                },
              ),
            ),

            if (_isLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8.0),
                child: SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),

            // Input Bar
            SafeArea(
              child: Container(
                padding: const EdgeInsets.all(8.0),
                decoration: const BoxDecoration(
                  color: Color(0xFF151D2A),
                  border: Border(top: BorderSide(color: Colors.white10)),
                ),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.security, color: Colors.blueAccent),
                      onPressed: _requestAllPermissions,
                      tooltip: "Request Permissions",
                    ),
                    Expanded(
                      child: TextField(
                        controller: _controller,
                        onSubmitted: _sendMessage,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(
                          hintText: "Enter command to JARVIS...",
                          hintStyle: TextStyle(color: Colors.white30),
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(horizontal: 8.0),
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.send, color: Color(0xFF00E5FF)),
                      onPressed: () => _sendMessage(_controller.text),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMessageItem(Message msg) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Align(
        alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          maxWidth: MediaQuery.of(context).size.width * 0.8,
          padding: const EdgeInsets.all(12.0),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16.0).copyWith(
              bottomRight: msg.isUser ? const Radius.circular(0) : const Radius.circular(16.0),
              topLeft: msg.isUser ? const Radius.circular(16.0) : const Radius.circular(0),
            ),
            gradient: msg.isUser
                ? const LinearGradient(
                    colors: [Color(0xFF0D47A1), Color(0xFF1976D2)],
                  )
                : const LinearGradient(
                    colors: [Color(0xFF212529), Color(0xFF343A40)],
                  ),
            border: Border.all(
              color: msg.isUser ? Colors.blue : const Color(0xFF00E5FF).withOpacity(0.3),
              width: msg.isUser ? 1.0 : 0.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (!msg.isUser && msg.agent != null)
                Padding(
                  padding: const EdgeInsets.bottom(4.0),
                  child: Text(
                    msg.agent!.toUpperCase(),
                    style: const TextStyle(
                      color: Color(0xFF00E5FF),
                      fontSize: 10.0,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.0,
                    ),
                  ),
                ),
              Text(
                msg.text,
                style: const TextStyle(color: Colors.white, fontSize: 14.5),
              ),
              if (msg.imageUrl != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8.0),
                    child: Image.network(
                      msg.imageUrl!,
                      loadingBuilder: (context, child, progress) {
                        if (progress == null) return child;
                        return const Center(child: CircularProgressIndicator());
                      },
                      errorBuilder: (context, error, stackTrace) {
                        return const Text(
                          "Failed to load image",
                          style: TextStyle(color: Colors.redAccent, fontSize: 12),
                        );
                      },
                    ),
                  ),
                ),
              if (msg.intent != null)
                Container(
                  margin: const EdgeInsets.only(top: 8.0),
                  padding: const EdgeInsets.all(6.0),
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(6.0),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.android, size: 14, color: Colors.green),
                      const SizedBox(width: 4),
                      Text(
                        "Executed: ${msg.intent}",
                        style: const TextStyle(
                          color: Colors.greenAccent,
                          fontSize: 11,
                          fontFamily: "monospace",
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
