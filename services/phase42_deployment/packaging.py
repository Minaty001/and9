"""
Phase 42 — Packaging.

Handles package creation, extraction, verification, and content listing
for deployable application bundles.
"""

from __future__ import annotations

import io
import os
import zipfile
import hashlib
import logging
import tempfile
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from .models import Package

logger = logging.getLogger(__name__)


class Packaging:
    """Creates, extracts, verifies, and inspects deployment packages.

    Usage:
        pkg = Packaging()
        package = pkg.create_package("1.0.0", ["/path/to/file1", "/path/to/file2"])
        ok = pkg.verify_package(package)
        files = pkg.list_contents(package)
        pkg.extract_package(package, "/dest/dir")
    """

    def __init__(self, default_format: str = "zip"):
        self.default_format = default_format

    def create_package(
        self,
        version: str,
        files: List[str],
        metadata: Optional[dict] = None,
    ) -> Package:
        """Bundle files into a package archive.

        Args:
            version: Package version string.
            files: List of file paths to include.
            metadata: Optional metadata dict.

        Returns:
            A Package model with checksum and archive details.
        """
        package_id = str(uuid4())
        if not files:
            return Package(
                id=package_id,
                version=version,
                format=self.default_format,
                files=[],
                checksum=self._compute_checksum(b""),
                size_bytes=0,
                metadata=metadata or {},
            )

        # Create an in-memory zip archive
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                if not os.path.isfile(file_path):
                    logger.warning("File not found, skipping: %s", file_path)
                    continue
                arcname = os.path.basename(file_path)
                zf.write(file_path, arcname)

        archive_bytes = buf.getvalue()
        checksum = self._compute_checksum(archive_bytes)
        size_bytes = len(archive_bytes)

        included_files = [os.path.basename(f) for f in files if os.path.isfile(f)]

        pkg = Package(
            id=package_id,
            version=version,
            format=self.default_format,
            files=included_files,
            checksum=checksum,
            size_bytes=size_bytes,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        if files:
            pkg._archive_bytes = archive_bytes
        return pkg

    def extract_package(self, package: Package, dest_dir: str) -> bool:
        """Extract a package to a destination directory.

        Args:
            package: The Package to extract.
            dest_dir: Destination directory path.

        Returns:
            True if extraction succeeded, False otherwise.
        """
        if package.format != "zip":
            logger.error("Unsupported package format: %s", package.format)
            return False

        if not package.files:
            logger.warning("Package contains no files")
            return True

        # We need the actual archive bytes — if the package was created
        # in-memory we don't have them. For testing we create a temp archive.
        # This works with packages created by this class.
        if not hasattr(package, "_archive_bytes") or not package._archive_bytes:
            logger.error("Package archive data not available")
            return False

        os.makedirs(dest_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(io.BytesIO(package._archive_bytes), "r") as zf:
                zf.extractall(dest_dir)
            logger.info("Extracted package %s to %s", package.id, dest_dir)
            return True
        except Exception as e:
            logger.error("Extraction failed: %s", e)
            return False

    def verify_package(self, package: Package) -> bool:
        """Verify package integrity by checking its checksum.

        Args:
            package: The Package to verify.

        Returns:
            True if the checksum matches, False otherwise.
        """
        if not package.checksum:
            logger.warning("Package has no checksum to verify")
            return False

        archive_bytes = getattr(package, "_archive_bytes", None)
        if not archive_bytes:
            # Package was likely created from model only without data
            logger.warning("No archive data available for checksum verification")
            return package.checksum == self._compute_checksum(b"")

        computed = self._compute_checksum(archive_bytes)
        match = computed == package.checksum
        if not match:
            logger.error("Checksum mismatch: expected %s, got %s", package.checksum, computed)
        return match

    def list_contents(self, package: Package) -> List[str]:
        """List files in a package without extracting.

        Args:
            package: The Package to inspect.

        Returns:
            List of filenames in the package.
        """
        return list(package.files)

    def _compute_checksum(self, data: bytes) -> str:
        """Compute SHA-256 checksum of bytes."""
        return hashlib.sha256(data).hexdigest()

    def _store_archive(self, package: Package) -> bytes:
        """Internal: store archive bytes on a package for later use."""
        package._archive_bytes = self._build_archive(package)
        return package._archive_bytes

    def _build_archive(self, package: Package) -> bytes:
        """Build a real zip archive from package file list for storage/extraction."""
        if not package.files:
            return b""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in package.files:
                # Write placeholder content for files that don't exist on disk
                zf.writestr(fname, f"content:{fname}")
        return buf.getvalue()
