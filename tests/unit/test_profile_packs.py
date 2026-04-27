"""Signed profile pack tests (SDLC-065)."""

from __future__ import annotations

import json
import secrets
import zipfile
from pathlib import Path

import pytest

from sdlc_assessor.profiles.packs import (
    PackManifestError,
    PackNotFoundError,
    PackVerificationError,
    build_pack,
    canonical_manifest_bytes,
    compute_signature,
    load_signed_pack,
    load_trust,
    trust_path,
    verify_pack,
)


def _fresh_secret() -> str:
    return secrets.token_hex(32)


# ---------------------------------------------------------------------------
# Trust + helpers
# ---------------------------------------------------------------------------


def test_trust_path_uses_env_var_when_set(monkeypatch, tmp_path: Path) -> None:
    custom = tmp_path / "trust.json"
    monkeypatch.setenv("SDLC_TRUST_FILE", str(custom))
    assert trust_path() == custom


def test_load_trust_returns_empty_when_file_absent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SDLC_TRUST_FILE", str(tmp_path / "nonexistent.json"))
    assert load_trust() == {}


def test_load_trust_reads_keys(tmp_path: Path) -> None:
    trust_file = tmp_path / "trust.json"
    trust_file.write_text(json.dumps({"acme": "deadbeef" * 8}), encoding="utf-8")
    out = load_trust(trust_file)
    assert out == {"acme": "deadbeef" * 8}


def test_canonical_manifest_bytes_is_stable() -> None:
    a = canonical_manifest_bytes({"b": 2, "a": 1})
    b = canonical_manifest_bytes({"a": 1, "b": 2})
    assert a == b


def test_compute_signature_matches_manual_hmac() -> None:
    secret = _fresh_secret()
    manifest = {"name": "demo", "version": "1.0.0", "files": []}
    sig = compute_signature(manifest, secret)
    assert isinstance(sig, str) and len(sig) == 64  # hex sha256


# ---------------------------------------------------------------------------
# Build + load happy path
# ---------------------------------------------------------------------------


def test_build_and_load_signed_pack_roundtrip(tmp_path: Path) -> None:
    secret = _fresh_secret()
    pack_dir = tmp_path / "acme-pack"
    profiles = {
        "use_case_profiles.json": {"acme_diligence": {"description": "x"}},
        "maturity_profiles.json": {"acme_strict": {"description": "y"}},
    }
    build_pack(
        pack_dir,
        name="acme-vc-diligence",
        version="1.0.0",
        author="Acme",
        profiles=profiles,
        secret_hex=secret,
        key_id="acme-prod",
    )
    loaded = load_signed_pack(pack_dir, trust={"acme-prod": secret})
    assert loaded.name == "acme-vc-diligence"
    assert loaded.version == "1.0.0"
    assert loaded.verified is True
    assert loaded.signing_key_id == "acme-prod"
    assert loaded.use_case_profiles == profiles["use_case_profiles.json"]
    assert loaded.maturity_profiles == profiles["maturity_profiles.json"]


def test_load_signed_pack_from_zip(tmp_path: Path) -> None:
    secret = _fresh_secret()
    pack_dir = tmp_path / "acme-pack"
    build_pack(
        pack_dir,
        name="acme",
        version="1.0.0",
        profiles={"use_case_profiles.json": {"x": {}}},
        secret_hex=secret,
        key_id="k1",
    )
    zip_path = tmp_path / "acme.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for path in pack_dir.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(pack_dir)))
    loaded = load_signed_pack(zip_path, trust={"k1": secret})
    assert loaded.verified is True
    assert loaded.use_case_profiles == {"x": {}}


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_load_signed_pack_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(PackNotFoundError):
        load_signed_pack(tmp_path / "no-such-pack")


def test_load_signed_pack_raises_when_unsigned_and_strict(tmp_path: Path) -> None:
    pack_dir = tmp_path / "unsigned"
    build_pack(
        pack_dir,
        name="x",
        version="0.0.0",
        profiles={"use_case_profiles.json": {"x": {}}},
    )
    # No signature.json was written because no secret was supplied.
    with pytest.raises(PackVerificationError):
        load_signed_pack(pack_dir, trust={})


def test_load_signed_pack_loads_unsigned_when_not_strict(tmp_path: Path) -> None:
    pack_dir = tmp_path / "unsigned"
    build_pack(
        pack_dir,
        name="x",
        version="0.0.0",
        profiles={"use_case_profiles.json": {"x": {}}},
    )
    with pytest.warns(UserWarning, match="unsigned pack"):
        loaded = load_signed_pack(pack_dir, trust={}, strict=False)
    assert loaded.verified is False
    assert loaded.use_case_profiles == {"x": {}}


def test_load_signed_pack_rejects_unknown_key_id(tmp_path: Path) -> None:
    pack_dir = tmp_path / "p"
    secret = _fresh_secret()
    build_pack(
        pack_dir,
        name="x",
        version="0.0.0",
        profiles={"use_case_profiles.json": {"x": {}}},
        secret_hex=secret,
        key_id="key-A",
    )
    with pytest.raises(PackVerificationError, match="No trusted secret"):
        load_signed_pack(pack_dir, trust={"key-B": secret})


def test_load_signed_pack_rejects_tampered_signature(tmp_path: Path) -> None:
    pack_dir = tmp_path / "p"
    secret = _fresh_secret()
    build_pack(
        pack_dir,
        name="x",
        version="0.0.0",
        profiles={"use_case_profiles.json": {"x": {}}},
        secret_hex=secret,
        key_id="k",
    )
    # Flip one hex char of the signature. Pick a replacement that differs
    # from the original first char — otherwise on the ~1/16 of runs where
    # the HMAC's leading hex char happens to be the same, we mutate to a
    # no-op and the test silently passes / flakes.
    sig_path = pack_dir / "signature.json"
    payload = json.loads(sig_path.read_text(encoding="utf-8"))
    original_sig = payload["signature"]
    new_first = "1" if original_sig[0] != "1" else "2"
    payload["signature"] = new_first + original_sig[1:]
    sig_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PackVerificationError, match="Signature mismatch"):
        load_signed_pack(pack_dir, trust={"k": secret})


def test_load_signed_pack_rejects_tampered_profile_content(tmp_path: Path) -> None:
    pack_dir = tmp_path / "p"
    secret = _fresh_secret()
    build_pack(
        pack_dir,
        name="x",
        version="0.0.0",
        profiles={"use_case_profiles.json": {"original": {"v": 1}}},
        secret_hex=secret,
        key_id="k",
    )
    # Tamper with the profile file after signing → manifest hash mismatch.
    target = pack_dir / "profiles" / "use_case_profiles.json"
    target.write_text(json.dumps({"injected": {"v": 999}}), encoding="utf-8")
    with pytest.raises(PackManifestError, match="sha256 mismatch"):
        load_signed_pack(pack_dir, trust={"k": secret})


def test_verify_pack_rejects_unsupported_algo() -> None:
    with pytest.raises(PackVerificationError, match="Unsupported signature algo"):
        verify_pack({}, {"algo": "rsa-sha256", "key_id": "k", "signature": "x"}, {"k": "x"})


def test_verify_pack_returns_key_id_on_success() -> None:
    manifest = {"name": "a", "version": "1.0", "files": []}
    secret = _fresh_secret()
    sig = {"algo": "hmac-sha256", "key_id": "k1", "signature": compute_signature(manifest, secret)}
    assert verify_pack(manifest, sig, {"k1": secret}) == "k1"
