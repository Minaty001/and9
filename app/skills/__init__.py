"""
app/skills — Executable tools for agents.

Intent executor, YouTube/music handling, web search, research,
image generation, and miscellaneous task helpers.
"""

from app.skills.intent_executor import IntentExecutor

# YouTube / Music
from app.skills.youtube import (
    is_music_request, search_youtube, handle_music_request, extract_search_query,
)

# Tasks
from app.skills.tasks import (
    search_web, get_realtime_data, generate_image_task,
    get_time, get_time_date, get_system_info, get_news,
    handle_device_command,
)

# Research
from app.skills.research import (
    search_sources, fetch_page, summarize_source, synthesize_answer,
)

# Image generation
from app.skills.img import generate_image, list_generated_images

__all__ = [
    "IntentExecutor",
    "is_music_request", "search_youtube", "handle_music_request", "extract_search_query",
    "search_web", "get_realtime_data", "generate_image_task",
    "get_time", "get_time_date", "get_system_info", "get_news",
    "handle_device_command",
    "search_sources", "fetch_page", "summarize_source", "synthesize_answer",
    "generate_image", "list_generated_images",
]
