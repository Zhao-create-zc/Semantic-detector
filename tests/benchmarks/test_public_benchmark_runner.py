from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmarks.run_public_benchmark import load_catalog, sha256_file


def test_public_source_catalog_has_pinned_sources() -> None:
    catalog = load_catalog()
    assert {"iti-modbus-smoke-v1", "iti-dnp3-smoke-v1"} <= set(catalog)
    for source in catalog.values():
        assert len(source["source_commit"]) == 40
        assert source["download_url"].startswith("https://raw.githubusercontent.com/")
        assert source["source_commit"] in source["download_url"]
        assert source["license_or_terms"]
        assert source["redistribute_raw_capture"] is False


def test_sha256_file(tmp_path: Path) -> None:
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"abc")
    assert sha256_file(sample) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
