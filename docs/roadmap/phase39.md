# Phase 39: Plugin SDK

## Purpose
Plugin system enabling third-party extensions with a well-defined lifecycle, hook system, loader, and sandbox. `PluginBase` is the abstract base class all plugins must subclass (initialize, shutdown, get_metadata, plus optional on_intent/on_response/on_turn/on_error hooks). `PluginLoader` handles loading/unloading/reloading plugins with version checking, dependency resolution, and directory discovery. `LifecycleManager` manages state transitions (installed → enabled → disabled → unloaded) with validation. `HookManager` registers and executes lifecycle hooks with priority ordering. `Sandbox` provides resource limits (filesystem, network, execution restrictions) and timeout enforcement.

## Architecture
```
PluginBase (ABC)
  ├── initialize() — required
  ├── shutdown() — required
  ├── get_metadata() → dict — required
  ├── on_intent(context) — optional hook
  ├── on_response(context) — optional hook
  ├── on_turn(context) — optional hook
  ├── on_error(context) — optional hook
  └── validate(plugin_class) → bool

PluginLoader
  ├── load_plugin(manifest_or_path, plugin_class) → bool
  ├── unload_plugin(id) / reload_plugin(id)
  ├── get_loaded_plugins() → List[Dict]
  ├── discover_plugins() → List[PluginManifest]
  └── check_compatibility(version, api_version) → (bool, reason)

LifecycleManager
  ├── transition(plugin_id, new_state, reason) → bool
  ├── get_state(id) / get_history(id)
  └── Valid transitions: installed → enabled → disabled → unloaded

HookManager
  ├── register_hook(PluginHook) → bool
  ├── unregister_hook(type, plugin_id) → bool
  └── execute_hooks(hook_type, context) → List[Any]

Sandbox
  ├── restrict_filesystem(paths)
  ├── restrict_network(domains)
  ├── restrict_exec(commands)
  └── execute_with_limits(func, timeout) → result

Models: PluginManifest, PluginState, PluginHook
```

## Code
```python
class PluginBase(ABC):
    @abstractmethod
    def initialize(self): ...
    @abstractmethod
    def shutdown(self): ...
    @abstractmethod
    def get_metadata(self) -> Dict: ...

    def on_intent(self, context): return None  # optional hook

class PluginLoader:
    def load_plugin(self, manifest_or_path, plugin_class=None) -> bool:
        if isinstance(manifest_or_path, PluginBase):
            manifest = manifest_or_path.manifest
        if manifest.id in self._plugins: return False
        if self.enable_version_check:
            compatible, reason = self.check_compatibility(manifest.version, manifest.min_api_version)
            if not compatible: return False
        if plugin_class and not PluginBase.validate(plugin_class): return False
        self._plugins[manifest.id] = manifest
        return True

class LifecycleManager:
    def transition(self, plugin_id, new_state, reason="") -> bool:
        current = self._states.get(plugin_id)
        if current and new_state not in _VALID_TRANSITIONS.get(current.status, set()):
            return False
        self._states[plugin_id] = PluginState(status=new_state)
        return True
```

## Location
`app/core/plugin_sdk/` — plugin base, loader, lifecycle manager, hook manager, sandbox, models, service
