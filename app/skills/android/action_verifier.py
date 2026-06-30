"""
AND9 — Action Verifier.
Pre-execution validation layer for dangerous actions (calls, messages, file deletion, etc.)
"""
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

DANGEROUS_ACTIONS = {
    "call", "make_call", "phone_call",
    "send_sms", "message",
    "delete", "delete_file",
    "write_file", "create_file",
    "open_app", "close_app"
}

# Sensitive apps list that require confirmation before launching
SENSITIVE_APPS = {
    "gpay", "google pay", "paytm", "phonepe", "yono", "bank", "settings", "installer", "amazon", "flipkart"
}

def verify_action(action: str, params: Dict[str, Any]) -> Tuple[bool, str, str]:
    """Verify if an action is dangerous and requires user confirmation.

    Args:
        action: Lowercase action name.
        params: Extracted parameters dictionary.

    Returns:
        Tuple of (needs_confirmation: bool, prompt: str, action_summary: str)
    """
    act = action.lower().strip()
    
    if act not in DANGEROUS_ACTIONS:
        return False, "", ""

    needs_confirm = True
    prompt = "Kya aap is action ko execute karna chahte hain?"
    summary = f"Execute {act}"

    if act in ("call", "make_call", "phone_call"):
        contact = params.get("contact_name") or params.get("contact") or ""
        number = params.get("phone_number") or params.get("number") or ""
        
        if contact and number:
            prompt = f"Kya aap {contact} ko {number} par call karna chahte hain?"
            summary = f"Call {contact} ({number})"
        elif contact:
            prompt = f"Kya aap {contact} ko call karna chahte hain?"
            summary = f"Call {contact}"
        elif number:
            prompt = f"Kya aap {number} par call karna chahte hain?"
            summary = f"Call {number}"
        else:
            prompt = "Aap kisko call karna chahte hain? Kripya naam ya number batayein."
            summary = "Call unknown recipient"

    elif act in ("send_sms", "message"):
        contact = params.get("contact_name") or params.get("contact") or ""
        number = params.get("phone_number") or params.get("number") or ""
        body = params.get("message_body") or params.get("body") or params.get("message") or ""
        
        recipient = contact or number or "unknown"
        if body:
            prompt = f"Kya aap {recipient} ko message bhejna chahte hain: '{body}'?"
            summary = f"Send SMS to {recipient}"
        else:
            prompt = f"Kya aap {recipient} ko khali message bhejna chahte hain?"
            summary = f"Send empty SMS to {recipient}"

    elif act in ("delete", "delete_file"):
        filename = params.get("filename") or params.get("path") or params.get("file") or ""
        if not filename:
            prompt = "Aap kaun si file delete karna chahte hain? Kripya file ka naam batayein."
            summary = "Delete unknown file"
        else:
            prompt = f"Kya aap file '{filename}' ko hamesha ke liye delete karna chahte hain?"
            summary = f"Delete file {filename}"

    elif act in ("write_file", "create_file"):
        filename = params.get("filename") or params.get("path") or params.get("file") or ""
        if not filename:
            prompt = "Aap kis file mein likhna chahte hain? Kripya file ka naam batayein."
            summary = "Write to unknown file"
        else:
            prompt = f"Kya aap file '{filename}' create ya write karna chahte hain?"
            summary = f"Write to file {filename}"

    elif act == "open_app":
        app_name = (params.get("app_name") or params.get("package_name") or "").lower()
        # Only confirm if it is a sensitive app
        is_sensitive = any(sensitive in app_name for sensitive in SENSITIVE_APPS)
        if is_sensitive:
            prompt = f"Kya aap sensitive app '{app_name}' ko open karna chahte hain?"
            summary = f"Open sensitive app {app_name}"
        else:
            needs_confirm = False
            prompt = ""
            summary = ""

    elif act == "close_app":
        prompt = "Kya aap active app ko close karna chahte hain?"
        summary = "Close active app"

    return needs_confirm, prompt, summary
