"""AND9 — Package Resolver.

Resolves app names (including Hinglish aliases) to Android package names.
"""

from .package_resolver import PackageResolver, get_resolver

__all__ = ["PackageResolver", "get_resolver"]
