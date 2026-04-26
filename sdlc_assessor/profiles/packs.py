"""Signed profile packs (SDLC-065).

A "profile pack" is a directory or zip file containing custom profile JSON
overlays plus a ``manifest.json`` and an HMAC-SHA256 signature. The loader
verifies the signature against a trust list of pre-shared keys before
applying any profiles, so an organisation can publish profile updates and
consumers can verify provenance without trusting the transport.

## Pack layout

    pack-name-1.0.0/
    ├── manifest.json
    ├── profiles/
    │   ├── use_case_profiles.json     (optional — partial overlay)
    │   ├── maturity_profiles.json     (optional)
    │   └── repo_type_profiles.json    (optional)
    └── signature.json

`manifest.json` shape:

    {
      "name": "acme-vc-diligence",
      "version": "1.0.0",
      "author": "Acme Security",
      "files": [
        {"path": "profiles/use_case_profiles.json", "sha256": "<hex>"},
        ...
      ],
      "key_id": "acme-prod"
    }

`signature.json` shape:

    {
      "algo": "hmac-sha256",
      "key_id": "acme-prod",
      "signature": "<hex of HMAC(SHA256(canonical_manifest), shared_secret)>"
    }

## Trust model

This is the v1 trust model. It uses HMAC-SHA256 with pre-shared symmetric
keys, indexed by ``key_id``:

- The trust file lives at ``$SDLC_TRUST_FILE`` or
  ``~/.config/sdlc-assessor/trust.json`` (default).
- It maps ``key_id → secret_hex`` (32+ random bytes encoded as hex).
- A pack verifies if HMAC-SHA256(canonical_manifest, secret) ==
  signature.signature for the trust entry matching ``signature.key_id``.

HMAC is symmetric — the trust file IS the signing key, treat it like one.
A future v2 trust model will switch to ed25519 (asymmetric), but that
requires a non-stdlib dep; deferred.

## Loading

``load_signed_pack(pack_path)`` returns a :class:`LoadedPack` with the
verified profile dictionaries. Pass ``strict=False`` to allow loading
unsigned packs with a warning (useful for local development).

A pack can be a directory or a ``.zip`` file. Tarballs are not supported
in v1 — adding them is a one-liner if needed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TRUST_PATH = Path.home() / ".config" / "sdlc-assessor" / "trust.json"
TRUST_FILE_ENV = "SDLC_TRUST_FILE"
PACK_FILE_NAMES = {"manifest.json", "signature.json"}


@dataclass(slots=True)
class LoadedPack:
    """The verified result of loading a profile pack."""

    name: str
    version: str
    use_case_profiles: dict = field(default_factory=dict)
    maturity_profiles: dict = field(default_factory=dict)
    repo_type_profiles: dict = field(default_factory=dict)
    verified: bool = False
    signing_key_id: str | None = None


class PackError(Exception):
    """Base class for any failure during pack loading or verification."""


class PackNotFoundError(PackError):
    pass


class PackVerificationError(PackError):
    pass


class PackManifestError(PackError):
    pass


# ---------------------------------------------------------------------------
# Trust list
# ---------------------------------------------------------------------------


def trust_path() -> Path:
    custom = os.environ.get(TRUST_FILE_ENV)
    return Path(custom) if custom else DEFAULT_TRUST_PATH


def load_trust(trust_file: Path | None = None) -> dict[str, str]:
    """Return ``{key_id: hex_secret}``. Empty dict if no trust file exists."""
    path = trust_file if trust_file is not None else trust_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(f"Cannot read trust file at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackError(f"Trust file at {path} must contain a JSON object")
    return {str(k): str(v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# Canonical manifest serialisation (deterministic across hosts)
# ---------------------------------------------------------------------------


def canonical_manifest_bytes(manifest: dict) -> bytes:
    """Sorted-key, no-whitespace JSON encoding for HMAC input."""
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_signature(manifest: dict, secret_hex: str) -> str:
    """Return the hex HMAC-SHA256 of ``manifest`` under ``secret_hex``."""
    secret = bytes.fromhex(secret_hex)
    digest = hmac.new(secret, canonical_manifest_bytes(manifest), hashlib.sha256).hexdigest()
    return digest


# ---------------------------------------------------------------------------
# Reading a pack from disk (directory or zip)
# ---------------------------------------------------------------------------


class _PackSource:
    """Adapter that exposes ``read_text(rel_path)`` for both dir and zip packs."""

    def __init__(self, kind: str, root: Path, zip_handle: zipfile.ZipFile | None = None) -> None:
        self.kind = kind  # "dir" | "zip"
        self.root = root
        self.zip_handle = zip_handle

    def read_text(self, rel: str) -> str:
        if self.kind == "dir":
            path = self.root / rel
            return path.read_text(encoding="utf-8")
        assert self.zip_handle is not None
        with self.zip_handle.open(rel, "r") as fh:
            return fh.read().decode("utf-8")

    def exists(self, rel: str) -> bool:
        if self.kind == "dir":
            return (self.root / rel).exists()
        assert self.zip_handle is not None
        try:
            self.zip_handle.getinfo(rel)
            return True
        except KeyError:
            return False


def _open_pack(pack_path: Path) -> _PackSource:
    if not pack_path.exists():
        raise PackNotFoundError(f"Pack not found: {pack_path}")
    if pack_path.is_dir():
        return _PackSource("dir", pack_path)
    if pack_path.suffix.lower() == ".zip" or zipfile.is_zipfile(pack_path):
        return _PackSource("zip", pack_path, zip_handle=zipfile.ZipFile(pack_path, "r"))
    raise PackError(
        f"Unsupported pack format: {pack_path}. Provide a directory or a .zip archive."
    )


# ---------------------------------------------------------------------------
# Verification + loading
# ---------------------------------------------------------------------------


def verify_pack(manifest: dict, signature: dict, trust: dict[str, str]) -> str:
    """Verify ``signature`` against ``manifest`` using ``trust``.

    Returns the matching key_id on success. Raises ``PackVerificationError``
    on any of: unknown algo, missing key_id in trust list, signature mismatch.
    """
    algo = signature.get("algo")
    if algo != "hmac-sha256":
        raise PackVerificationError(f"Unsupported signature algo: {algo!r}")
    key_id = signature.get("key_id")
    if not isinstance(key_id, str):
        raise PackVerificationError("signature.key_id missing or not a string")
    secret = trust.get(key_id)
    if secret is None:
        raise PackVerificationError(
            f"No trusted secret for key_id={key_id!r}; check {trust_path()}."
        )
    expected = compute_signature(manifest, secret)
    actual = signature.get("signature")
    if not isinstance(actual, str) or not hmac.compare_digest(expected, actual):
        raise PackVerificationError(
            f"Signature mismatch for pack signed by key_id={key_id!r}."
        )
    return key_id


def _validate_manifest_files(manifest: dict, source: _PackSource) -> None:
    """Confirm declared file hashes match on-disk content."""
    files = manifest.get("files") or []
    if not isinstance(files, list):
        raise PackManifestError("manifest.files must be a list")
    for entry in files:
        if not isinstance(entry, dict):
            raise PackManifestError("manifest.files entries must be objects")
        path = entry.get("path")
        expected = entry.get("sha256")
        if not isinstance(path, str) or not isinstance(expected, str):
            raise PackManifestError(
                f"Bad manifest entry (path/sha256 not strings): {entry!r}"
            )
        if not source.exists(path):
            raise PackManifestError(f"Manifest references missing file: {path}")
        actual = hashlib.sha256(source.read_text(path).encode("utf-8")).hexdigest()
        if actual != expected:
            raise PackManifestError(
                f"sha256 mismatch on {path}: manifest={expected} actual={actual}"
            )


def load_signed_pack(
    pack_path: str | Path,
    *,
    trust: dict[str, str] | None = None,
    strict: bool = True,
) -> LoadedPack:
    """Verify and load a profile pack.

    Args:
        pack_path: directory or .zip containing the pack.
        trust: ``{key_id: secret_hex}``. Defaults to the file at
            ``$SDLC_TRUST_FILE`` or ``~/.config/sdlc-assessor/trust.json``.
        strict: when True (default), an unsigned pack or a verification
            failure raises ``PackVerificationError``. When False, an
            unsigned pack loads with a warning and ``verified=False``.

    Returns:
        The :class:`LoadedPack` with ``verified=True`` on success.

    Raises:
        PackNotFoundError, PackManifestError, PackVerificationError, PackError.
    """
    pack_path = Path(pack_path)
    source = _open_pack(pack_path)

    if not source.exists("manifest.json"):
        raise PackManifestError(f"Pack at {pack_path} is missing manifest.json")
    try:
        manifest = json.loads(source.read_text("manifest.json"))
    except json.JSONDecodeError as exc:
        raise PackManifestError(f"manifest.json is not valid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PackManifestError("manifest.json must be a JSON object")

    name = str(manifest.get("name") or "<unnamed>")
    version = str(manifest.get("version") or "0.0.0")

    _validate_manifest_files(manifest, source)

    trust = trust if trust is not None else load_trust()

    verified = False
    signing_key_id: str | None = None
    if source.exists("signature.json"):
        signature = json.loads(source.read_text("signature.json"))
        signing_key_id = verify_pack(manifest, signature, trust)
        verified = True
    else:
        if strict:
            raise PackVerificationError(
                f"Pack at {pack_path} is unsigned; pass strict=False to load anyway."
            )
        warnings.warn(
            f"Loading unsigned pack {name}@{version} from {pack_path}; "
            "no provenance verification performed.",
            stacklevel=2,
        )

    use_case: dict = {}
    maturity: dict = {}
    repo_type: dict = {}
    for entry in manifest.get("files") or []:
        path = entry.get("path", "")
        if path.endswith("use_case_profiles.json"):
            use_case = json.loads(source.read_text(path))
        elif path.endswith("maturity_profiles.json"):
            maturity = json.loads(source.read_text(path))
        elif path.endswith("repo_type_profiles.json"):
            repo_type = json.loads(source.read_text(path))

    return LoadedPack(
        name=name,
        version=version,
        use_case_profiles=use_case,
        maturity_profiles=maturity,
        repo_type_profiles=repo_type,
        verified=verified,
        signing_key_id=signing_key_id,
    )


# ---------------------------------------------------------------------------
# Pack-building helper (used by tests + by operators producing packs)
# ---------------------------------------------------------------------------


def build_pack(
    pack_path: Path,
    *,
    name: str,
    version: str,
    profiles: dict[str, dict],
    secret_hex: str | None = None,
    key_id: str | None = None,
    author: str = "",
) -> None:
    """Write a pack to ``pack_path`` (a directory). Optionally signs it.

    ``profiles`` is a dict mapping the profile-file basename (e.g.
    ``"use_case_profiles.json"``) to its JSON contents. Only the four
    canonical names are recognised; others are ignored.
    """
    pack_path.mkdir(parents=True, exist_ok=True)
    profiles_dir = pack_path / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    files: list[dict] = []
    for filename, contents in profiles.items():
        if filename not in {
            "use_case_profiles.json",
            "maturity_profiles.json",
            "repo_type_profiles.json",
        }:
            continue
        rel_path = f"profiles/{filename}"
        text = json.dumps(contents, sort_keys=True)
        (pack_path / rel_path).write_text(text, encoding="utf-8")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        files.append({"path": rel_path, "sha256": sha})

    manifest: dict = {
        "name": name,
        "version": version,
        "author": author,
        "files": files,
    }
    if key_id:
        manifest["key_id"] = key_id

    (pack_path / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
    )

    if secret_hex and key_id:
        signature = {
            "algo": "hmac-sha256",
            "key_id": key_id,
            "signature": compute_signature(manifest, secret_hex),
        }
        (pack_path / "signature.json").write_text(
            json.dumps(signature, sort_keys=True, indent=2), encoding="utf-8"
        )


__all__ = [
    "LoadedPack",
    "PackError",
    "PackNotFoundError",
    "PackVerificationError",
    "PackManifestError",
    "build_pack",
    "canonical_manifest_bytes",
    "compute_signature",
    "load_signed_pack",
    "load_trust",
    "trust_path",
    "verify_pack",
]
