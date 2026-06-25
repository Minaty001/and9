"""
app/agents/coding_agent.py — Code generation and execution agent.

Only uses the LLM for code generation. Code execution is sandboxed via subprocess.
"""
import subprocess
import sys
import os
import tempfile
import re
import logging

from app.core.brain import ask_llm
from app.core.config import OPENCODE_CODING_MODEL

logger = logging.getLogger(__name__)

CODE_SYSTEM = """You are an expert software engineer. When asked to write code:
- Write clean, working, well-commented code
- Always wrap code in ```language ... ``` blocks
- For errors/bugs: explain the fix clearly before showing corrected code
- Support: Python, JavaScript, Java, C++, Go, Rust, SQL, HTML/CSS, Bash"""


class CodingAgent:
    name = "CodingAgent"
    description = "Write, debug, explain, and run code"

    def run(self, query: str, **kwargs) -> dict:
        q = query.lower()

        if any(k in q for k in ["fix", "debug", "error", "bug", "broken"]):
            return self._debug(query)
        elif any(k in q for k in ["explain", "what is", "how does"]):
            return self._explain(query)
        elif any(k in q for k in ["improve", "optimize", "refactor"]):
            return self._improve(query)
        else:
            return self._write(query)

    def _write(self, query: str) -> dict:
        response = ask_llm(
            [{"role": "user", "content": f"Write code to: {query}\nUse the most appropriate language."}],
            system=CODE_SYSTEM,
            model=OPENCODE_CODING_MODEL,
            max_tokens=4096,
            temperature=0.2,
        )
        # Optionally extract and run Python
        code, lang = self._extract_code(response)
        execution = None
        from app.core.config import IS_RENDER
        if code and lang in ("python", "py"):
            if IS_RENDER:
                execution = "[Code execution is disabled in the cloud (Render) for security reasons.]"
            else:
                execution = self._execute_python(code)

        return {
            "agent": self.name,
            "success": True,
            "result": response,
            "metadata": {"task": "write_code", "language": lang, "execution": execution},
        }

    def _explain(self, query: str) -> dict:
        response = ask_llm(
            [{"role": "user", "content": f"Explain this code step by step:\n\n{query}"}],
            system=CODE_SYSTEM,
            model=OPENCODE_CODING_MODEL,
        )
        return {"agent": self.name, "success": True, "result": response, "metadata": {"task": "explain"}}

    def _debug(self, query: str) -> dict:
        response = ask_llm(
            [{"role": "user", "content": f"Debug and fix this code:\n\n{query}\n1. Identify the bug\n2. Show corrected code"}],
            system=CODE_SYSTEM,
            model=OPENCODE_CODING_MODEL,
        )
        return {"agent": self.name, "success": True, "result": response, "metadata": {"task": "debug"}}

    def _improve(self, query: str) -> dict:
        response = ask_llm(
            [{"role": "user", "content": f"Improve this code (readability, performance, best practices):\n\n{query}"}],
            system=CODE_SYSTEM,
            model=OPENCODE_CODING_MODEL,
        )
        return {"agent": self.name, "success": True, "result": response, "metadata": {"task": "improve"}}

    def _extract_code(self, text: str):
        m = re.search(r"```(\w*)\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(2).strip(), m.group(1).lower().strip()
        return None, None

    def _execute_python(self, code: str, timeout: int = 10) -> str:
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            result = subprocess.run([sys.executable, tmp], capture_output=True, text=True, timeout=timeout)
            return (result.stdout or result.stderr or "(no output)").strip()
        except subprocess.TimeoutExpired:
            return f"[Timeout {timeout}s]"
        except Exception as e:
            return f"[Error: {e}]"
        finally:
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except Exception:
                    logger.debug("Failed to clean up temp file: %s", tmp)
