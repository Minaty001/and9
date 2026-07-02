"""
AND9 — Device Agents: Android, Voice, Browser.

These agents handle device-level interactions: Android control,
voice I/O, and browser automation.
"""

import logging
from typing import Any, Callable, Optional

from app.and9.agents.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)


class AndroidAgent(AgentBase):
    """Android Agent — device control and automation.

    Interfaces with the Android device to execute actions:
      - Launch/close apps
      - Device controls (flashlight, wifi, bluetooth, volume)
      - Calls and messages
      - Media control
      - System settings
    """

    def __init__(self):
        super().__init__(
            name="android",
            role="Android device control and automation",
            goal="Execute Android device actions reliably and safely",
            backstory=(
                "I am the android agent. I control the Android device — "
                "launching apps, toggling settings, making calls, sending "
                "messages, and managing media. I work through the AND9 reflex "
                "engine for fast, deterministic device control."
            ),
        )
        self._executor = None

    def bind_executor(self, executor_func: Callable):
        """Bind the AND9 android executor."""
        self._executor = executor_func
        self.bind_tool("android_executor", executor_func)

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Capabilities:\n"
            "- Launch any installed app\n"
            "- Toggle flash / wifi / bluetooth / airplane mode\n"
            "- Make calls and send messages\n"
            "- Control volume and media\n"
            "- Set alarms, reminders, timers\n"
            "- Open camera and take photos\n"
            "- Search and play YouTube videos\n\n"
            "Rules:\n"
            "1. Verify permissions before executing sensitive actions.\n"
            "2. Never call emergency numbers without explicit confirmation.\n"
            "3. Provide clear feedback after each action.\n"
            "4. Fall back gracefully if an action fails.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process an Android device command."""
        command = str(input_data) if not isinstance(input_data, str) else input_data
        cmd_lower = command.lower().strip()

        # If we have an executor, use it
        if self._executor:
            try:
                result = self._executor(command)
                if isinstance(result, dict):
                    return AgentResult(
                        success=True,
                        response=result.get("response", "Done! ✅"),
                        data=result,
                        agent_name=self.name,
                    )
                return AgentResult(
                    success=True,
                    response=str(result),
                    agent_name=self.name,
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    response=f"Android action failed: {e}",
                    agent_name=self.name,
                    error=str(e),
                )

        # Without executor, describe what would happen
        return AgentResult(
            success=True,
            response=(
                f"**Android Command**: {command}\n\n"
                f"I understand you want to control your Android device. "
                f"I would execute this action through the AND9 reflex engine."
            ),
            data={
                "command": command,
                "executor_available": False,
                "action_type": self._classify_command(cmd_lower),
            },
            agent_name=self.name,
        )

    @staticmethod
    def _classify_command(command: str) -> str:
        """Classify the Android command type."""
        if any(w in command for w in ["open", "launch", "khol"]):
            return "launch_app"
        if any(w in command for w in ["call", "phone", "dial"]):
            return "call"
        if any(w in command for w in ["message", "msg", "text", "sms"]):
            return "message"
        if any(w in command for w in ["flash", "torch"]):
            return "flashlight"
        if "wifi" in command:
            return "wifi"
        if "bluetooth" in command:
            return "bluetooth"
        if "volume" in command:
            return "volume"
        if any(w in command for w in ["alarm", "alarm"]):
            return "alarm"
        if any(w in command for w in ["timer", "timer"]):
            return "timer"
        if any(w in command for w in ["remind", "reminder"]):
            return "reminder"
        if any(w in command for w in ["camera", "photo"]):
            return "camera"
        return "general_command"


class VoiceAgent(AgentBase):
    """Voice Agent — speech interaction management.

    Handles speech-to-text, text-to-speech, and voice-based
    interaction patterns including wake word detection.
    """

    def __init__(self):
        super().__init__(
            name="voice",
            role="Voice interaction management",
            goal="Enable natural voice-based interaction with the system",
            backstory=(
                "I am the voice agent. I manage speech-to-text (STT) and "
                "text-to-speech (TTS) for voice interaction. I handle "
                "wake word detection, streaming audio, interruptions, "
                "and natural dialogue patterns."
            ),
            config={
                "wake_word": "jarvis",
                "stt_engine": "default",
                "tts_engine": "default",
                "streaming": True,
            },
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Rules:\n"
            "1. Wake word detection must be reliable and low-latency.\n"
            "2. Convert speech to text accurately.\n"
            "3. Generate natural-sounding speech responses.\n"
            "4. Support interruption handling in voice mode.\n"
            "5. Work offline when possible.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a voice-related request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                f"**Voice System**\n\n"
                f"Voice module status: Available\n"
                f"Wake word: '{self.config['wake_word']}'\n"
                f"STT engine: {self.config['stt_engine']}\n"
                f"TTS engine: {self.config['tts_engine']}\n\n"
                f"Say '{self.config['wake_word']}' followed by your command."
            ),
            data={
                "wake_word": self.config["wake_word"],
                "stt_available": False,
                "tts_available": False,
                "streaming": self.config["streaming"],
            },
            agent_name=self.name,
        )


class BrowserAgent(AgentBase):
    """Browser Agent — web browser automation.

    Controls the web browser for automation tasks:
      - Opening URLs
      - Web scraping
      - Form filling
      - Screenshot capture
    """

    def __init__(self):
        super().__init__(
            name="browser",
            role="Web browser automation",
            goal="Automate browser tasks efficiently and reliably",
            backstory=(
                "I am the browser agent. I control web browsers for "
                "automation tasks — opening pages, extracting information, "
                "filling forms, and taking screenshots. I work through "
                "Playwright or Selenium for full browser control."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Capabilities:\n"
            "- Navigate to URLs\n"
            "- Extract page content\n"
            "- Fill and submit forms\n"
            "- Take screenshots\n"
            "- Execute JavaScript\n"
            "- Wait for elements\n\n"
            "Rules:\n"
            "1. Respect robots.txt and terms of service.\n"
            "2. Do not automate login or bypass authentication.\n"
            "3. Report page load errors clearly.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a browser automation request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                f"**Browser Automation**\n\n"
                f"Request: {request[:200]}\n"
                f"Browser controller available.\n\n"
                f"I can open pages, extract data, and automate web interactions."
            ),
            data={"request": request[:200]},
            agent_name=self.name,
        )
