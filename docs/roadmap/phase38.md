# Phase 38: File Manager

## Purpose
File management capabilities for reading, writing, listing, and organizing files on the local filesystem. Originally planned as `services/phase38/`, this module provides controlled file system access for the assistant to manage user files, configuration data, and export outputs. The design emphasizes safety with path validation, size limits, and extension allowlists.

## Architecture
```
(Conceptual design — referenced from roadmap intent)

FileManagerService (planned)
  ├── read_file(path) → file content
  ├── write_file(path, content) → success
  ├── list_directory(path) → file listing
  ├── delete_file(path) → success
  ├── copy_file(src, dst) → success
  ├── move_file(src, dst) → success
  └── get_file_info(path) → {size, modified, type}

Safety constraints:
  - Path traversal detection (block .. and symlink escapes)
  - File size limits on read
  - Extension allowlist for write
  - Sandbox within allowed directories
```

## Code
```python
# Planned implementation (not yet built):
class FileManagerService:
    def read_file(self, path):
        safe_path = self._validate_path(path)
        if os.path.getsize(safe_path) > self._max_read_size:
            raise ValueError("File too large")
        with open(safe_path, "r") as f:
            return f.read()

    def _validate_path(self, path):
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self._allowed_base):
            raise PermissionError("Path outside allowed directory")
        return abs_path
```

## Location
`app/core/filemanager/` (not yet created — documented from roadmap intent)
