"""
app/skills — Executable tools for agents.

Intent executor, YouTube/music handling, web search, research,
and miscellaneous task helpers.
"""

from app.skills.intent_executor import IntentExecutor

# YouTube / Music
from app.skills.youtube import (
    is_music_request, search_youtube, handle_music_request, extract_search_query,
)

# Tasks
from app.skills.tasks import (
    search_web, get_realtime_data,
    get_time, get_time_date, get_system_info, get_news,
    handle_device_command,
)
from app.skills.pc_control import handle_pc_command
from app.skills.audio_manager import handle_audio_command

# Research
from app.skills.research import (
    search_sources, fetch_page, summarize_source, synthesize_answer,
)

__all__ = [
    "IntentExecutor",
    "is_music_request", "search_youtube", "handle_music_request", "extract_search_query",
    "search_web", "get_realtime_data",
    "get_time", "get_time_date", "get_system_info", "get_news",
    "handle_device_command",
    "handle_pc_command", "handle_audio_command",
    "search_sources", "fetch_page", "summarize_source", "synthesize_answer",
]
