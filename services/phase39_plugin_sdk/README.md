# Phase 39: Plugin SDK

## Overview

Plugin system for registering, loading, unloading plugins with version management, sandbox execution, and lifecycle hooks.

## Architecture

```
Plugin SDK
     │
     ├── PluginLoader ◄──── Load/unload/reload plugins
     │                      Version checking, dependency resolution
     │
     ├── HookManager ◄──── Register/unregister/execute hooks
     │                      Lifecycle: on_initialize, on_shutdown, on_intent, etc.
     │
     └── Sandbox ◄──────── Safe execution with timeout
                          Import restrictions, resource limits
```

## Components

- **PluginLoader**: Load, unload, reload plugins; version checking; dependency resolution
- **HookManager**: Register, unregister, execute lifecycle hooks with priority ordering
- **Sandbox**: Execute plugin code with timeout and import restrictions
- **PluginSdkService**: ServiceBase wrapper with auto-discovery from plugin directory

## Usage

```python
from services.phase39_plugin_sdk import (
    PluginSdkService,
    PluginManifest,
    PluginHook,
    PluginState,
)

svc = PluginSdkService()
await svc.initialize()

# Load a plugin
manifest = PluginManifest(
    id="hello_plugin",
    name="Hello Plugin",
    version="1.0.0",
    hooks=["on_intent"],
)
svc.load_plugin(manifest)

# Register and execute hooks
hook = PluginHook(
    hook_type="on_intent",
    priority=100,
    handler="say_hello",
    plugin_id="hello_plugin",
)
svc.register_hook(hook)
results = svc.execute_hooks("on_intent", {"query": "hello"})

# Get plugin state
state = svc.get_plugin_state("hello_plugin")
```
