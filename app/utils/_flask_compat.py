"""Compatibility layer for Flask.

This module prefers the real Flask package when it is installed.
If Flask is unavailable, it provides a small in-process fallback that is
good enough for the repository's tests and local development of the core
JSON endpoints.
"""
from __future__ import annotations

import json
import logging
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlsplit

try:  # pragma: no cover - exercised only when Flask is installed
    from flask import (  # type: ignore
        Blueprint,
        Flask,
        Response,
        current_app,
        g,
        jsonify,
        render_template,
        request,
        session,
    )
except Exception:  # pragma: no cover - fallback is used in the test env
    _current_app: "Flask | None" = None

    class _ArgsDict(dict):
        def get(self, key, default=None, type=None):  # noqa: A002 - Flask API parity
            value = super().get(key, default)
            if value is default or type is None:
                return value
            try:
                return type(value)
            except Exception:
                return default

    class _RequestState:
        def __init__(self) -> None:
            self.headers: dict[str, Any] = {}
            self.args: _ArgsDict = _ArgsDict()
            self.remote_addr: str | None = None
            self.path: str = "/"
            self.method: str = "GET"
            self._json: Any = None
            self.data: bytes = b""

        def get_json(self, silent: bool = False) -> Any:
            if self._json is None and not silent:
                raise ValueError("No JSON payload attached to the request")
            return self._json

    _request_state = _RequestState()
    g = SimpleNamespace()
    session: dict[str, Any] = {}

    class _CurrentAppProxy:
        def __getattr__(self, name: str) -> Any:
            if _current_app is None:
                raise RuntimeError("Working outside of application context.")
            return getattr(_current_app, name)

        def __bool__(self) -> bool:
            return _current_app is not None

    current_app = _CurrentAppProxy()

    request = _request_state

    def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in (headers or {}).items():
            normalized[key] = value
        return normalized

    class Response:
        """Very small response object compatible with the test client."""

        def __init__(
            self,
            response: Any = b"",
            status: int = 200,
            mimetype: str = "text/html",
            headers: dict[str, Any] | None = None,
        ) -> None:
            self.status_code = status
            self.mimetype = mimetype
            self.headers = _normalize_headers(headers)
            self._body = response
            self.data = self._encode_body(response)
            if "Content-Type" not in self.headers:
                self.headers["Content-Type"] = mimetype

        @staticmethod
        def _encode_body(body: Any) -> bytes:
            if body is None:
                return b""
            if isinstance(body, bytes):
                return body
            if isinstance(body, str):
                return body.encode("utf-8")
            if isinstance(body, (dict, list, tuple)):
                return json.dumps(body).encode("utf-8")
            if isinstance(body, Iterable):
                try:
                    chunks = []
                    for chunk in body:
                        if isinstance(chunk, dict) and "data" in chunk:
                            payload = chunk["data"]
                            chunks.append(payload if isinstance(payload, bytes) else str(payload).encode("utf-8"))
                        else:
                            chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
                    return b"".join(chunks)
                except TypeError:
                    pass
            return str(body).encode("utf-8")

        @property
        def json(self) -> Any:
            if self.mimetype != "application/json" and "application/json" not in self.headers.get("Content-Type", ""):
                return None
            try:
                return json.loads(self.data.decode("utf-8"))
            except Exception:
                return None

        def get_json(self, silent: bool = False) -> Any:
            value = self.json
            if value is None and not silent:
                raise ValueError("Response does not contain JSON data")
            return value

        def set_data(self, data: bytes | str) -> None:
            self.data = data if isinstance(data, bytes) else data.encode("utf-8")


    def jsonify(*args: Any, **kwargs: Any) -> Response:
        if args and kwargs:
            payload = {"args": args, **kwargs}
        elif len(args) == 1:
            payload = args[0]
        elif args:
            payload = list(args)
        else:
            payload = kwargs
        return Response(json.dumps(payload), status=200, mimetype="application/json")


    @dataclass
    class _Route:
        rule: str
        methods: set[str]
        func: Callable[..., Any]
        endpoint: str
        regex: re.Pattern[str]
        converters: dict[str, Callable[[str], Any]]


    def _compile_rule(rule: str) -> tuple[re.Pattern[str], dict[str, Callable[[str], Any]]]:
        converters: dict[str, Callable[[str], Any]] = {}

        def repl(match: re.Match[str]) -> str:
            type_name = match.group("type")
            name = match.group("name")
            if type_name == "int":
                converters[name] = int
                return rf"(?P<{name}>\d+)"
            converters[name] = str
            return rf"(?P<{name}>[^/]+)"

        pattern = "^" + re.sub(r"<(?:(?P<type>[^:<>]+):)?(?P<name>[^<>]+)>", repl, rule.rstrip("/")) + "/?$"
        return re.compile(pattern), converters


    class _AppContext:
        def __init__(self, app: "Flask") -> None:
            self.app = app
            self._previous = None

        def __enter__(self) -> "Flask":
            global _current_app
            self._previous = _current_app
            _current_app = self.app
            return self.app

        def __exit__(self, exc_type, exc, tb) -> None:
            global _current_app
            _current_app = self._previous


    class Blueprint:
        def __init__(self, name: str, import_name: str) -> None:
            self.name = name
            self.import_name = import_name
            self._routes: list[_Route] = []

        def route(self, rule: str, methods: list[str] | None = None):
            methods_set = {m.upper() for m in (methods or ["GET"])}

            def decorator(func: Callable[..., Any]):
                regex, converters = _compile_rule(rule)
                self._routes.append(
                    _Route(
                        rule=rule,
                        methods=methods_set,
                        func=func,
                        endpoint=func.__name__,
                        regex=regex,
                        converters=converters,
                    )
                )
                return func

            return decorator


    class Flask:
        def __init__(
            self,
            import_name: str,
            template_folder: str | None = None,
            static_folder: str | None = None,
            static_url_path: str | None = None,
        ) -> None:
            self.import_name = import_name
            self.template_folder = template_folder
            self.static_folder = static_folder
            self.static_url_path = static_url_path
            self.config: dict[str, Any] = {}
            self.logger = logging.getLogger(import_name)
            self._routes: list[_Route] = []
            self._before_request: list[Callable[[], Any]] = []
            self._after_request: list[Callable[[Response], Response]] = []
            self._error_handlers: dict[int, Callable[[Exception], Any]] = {}

        def route(self, rule: str, methods: list[str] | None = None):
            methods_set = {m.upper() for m in (methods or ["GET"])}

            def decorator(func: Callable[..., Any]):
                regex, converters = _compile_rule(rule)
                self._routes.append(
                    _Route(
                        rule=rule,
                        methods=methods_set,
                        func=func,
                        endpoint=func.__name__,
                        regex=regex,
                        converters=converters,
                    )
                )
                return func

            return decorator

        def register_blueprint(self, blueprint: Blueprint, url_prefix: str = "") -> None:
            prefix = "/" + url_prefix.strip("/") if url_prefix else ""
            for route in blueprint._routes:
                combined = f"{prefix}{route.rule}"
                regex, converters = _compile_rule(combined)
                self._routes.append(
                    _Route(
                        rule=combined,
                        methods=route.methods,
                        func=route.func,
                        endpoint=f"{blueprint.name}.{route.endpoint}",
                        regex=regex,
                        converters=converters,
                    )
                )

        def before_request(self, func: Callable[[], Any]):
            self._before_request.append(func)
            return func

        def after_request(self, func: Callable[[Response], Response]):
            self._after_request.append(func)
            return func

        def errorhandler(self, code: int):
            def decorator(func: Callable[[Exception], Any]):
                self._error_handlers[code] = func
                return func

            return decorator

        @contextmanager
        def app_context(self):
            ctx = _AppContext(self)
            with ctx:
                yield self

        def _make_response(self, value: Any) -> Response:
            if isinstance(value, Response):
                return value
            if isinstance(value, tuple):
                body = value[0]
                status = 200
                headers: dict[str, Any] | None = None
                if len(value) >= 2:
                    if isinstance(value[1], int):
                        status = value[1]
                    elif isinstance(value[1], dict):
                        headers = value[1]
                    else:
                        try:
                            status = int(value[1])
                        except Exception:
                            headers = value[1]
                if len(value) >= 3:
                    headers = value[2]
                response = self._make_response(body)
                response.status_code = status
                if headers:
                    response.headers.update(headers)
                return response
            if isinstance(value, (dict, list)):
                return Response(json.dumps(value), status=200, mimetype="application/json")
            if isinstance(value, str):
                return Response(value, status=200, mimetype="text/html")
            if value is None:
                return Response("", status=204, mimetype="text/plain")
            return Response(str(value), status=200, mimetype="text/plain")

        def _dispatch(self, method: str, path: str, payload: Any = None, headers: dict[str, Any] | None = None) -> Response:
            global _current_app, g
            parsed = urlsplit(path)
            request.path = parsed.path or "/"
            request.method = method.upper()
            request.headers = _normalize_headers(headers)
            request.remote_addr = request.headers.get("X-Forwarded-For", "127.0.0.1")
            request.args = _ArgsDict({key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()})
            request._json = payload if isinstance(payload, (dict, list)) else None
            request.data = json.dumps(payload).encode("utf-8") if payload is not None else b""
            g = SimpleNamespace()

            previous_app = _current_app
            _current_app = self
            try:
                for before in self._before_request:
                    rv = before()
                    if rv is not None:
                        response = self._make_response(rv)
                        break
                else:
                    response = None
                    matched_any = False
                    for route in self._routes:
                        match = route.regex.match(request.path)
                        if not match:
                            continue
                        matched_any = True
                        if request.method not in route.methods:
                            continue
                        kwargs = {
                            key: route.converters.get(key, str)(value)
                            for key, value in match.groupdict().items()
                        }
                        response = self._make_response(route.func(**kwargs))
                        break
                    if response is None:
                        if matched_any:
                            handler = self._error_handlers.get(405)
                            if handler is not None:
                                response = self._make_response(handler(Exception("Method Not Allowed")))
                            else:
                                response = Response(json.dumps({"error": "method_not_allowed"}), status=405, mimetype="application/json")
                        else:
                            handler = self._error_handlers.get(404)
                            if handler is not None:
                                response = self._make_response(handler(Exception("Not Found")))
                            else:
                                response = Response(json.dumps({"error": "not_found"}), status=404, mimetype="application/json")

                for after in self._after_request:
                    response = after(response)
                    if not isinstance(response, Response):
                        response = self._make_response(response)
                return response
            except Exception as exc:  # pragma: no cover - exercised through the app
                handler = self._error_handlers.get(500)
                if handler is not None:
                    return self._make_response(handler(exc))
                return Response(json.dumps({"error": "internal_error", "message": str(exc)}), status=500, mimetype="application/json")
            finally:
                _current_app = previous_app

        def test_client(self):
            app = self

            class _Client:
                def get(self, path: str, headers: dict[str, Any] | None = None):
                    return app._dispatch("GET", path, headers=headers)

                def post(self, path: str, json: Any = None, headers: dict[str, Any] | None = None):
                    return app._dispatch("POST", path, payload=json, headers=headers)

                def delete(self, path: str, json: Any = None, headers: dict[str, Any] | None = None):
                    return app._dispatch("DELETE", path, payload=json, headers=headers)

                def put(self, path: str, json: Any = None, headers: dict[str, Any] | None = None):
                    return app._dispatch("PUT", path, payload=json, headers=headers)

                def patch(self, path: str, json: Any = None, headers: dict[str, Any] | None = None):
                    return app._dispatch("PATCH", path, payload=json, headers=headers)

            return _Client()

        def run(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("The Flask compatibility layer does not implement app.run().")


    def render_template(name: str, **kwargs: Any) -> str:
        app = _current_app
        search_roots = []
        if app is not None and app.template_folder:
            search_roots.append(app.template_folder)
        search_roots.append(os.path.join(os.getcwd(), "app", "templates"))
        search_roots.append(os.path.join(os.getcwd(), "templates"))
        for root in search_roots:
            candidate = os.path.join(root, name)
            if os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8", errors="replace") as handle:
                    return handle.read()
        return f"<template {name}>"
