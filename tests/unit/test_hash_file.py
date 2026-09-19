"""Tests for SHA-256 hash file helper."""

import os
import tempfile
import pytest
from semantic_detector.io.exporters import hash_file_sha256


def test_hash_file_sha256_known_content() -> None:
    """测试已知内容的 SHA-256 哈希值"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
        f.write('test content')
        temp_path = f.name
    
    try:
        result = hash_file_sha256(temp_path)
        expected = '6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72'
        assert result == expected
    finally:
        os.unlink(temp_path)


def test_hash_file_sha256_empty_file() -> None:
    """测试空文件的 SHA-256 哈希值"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
        temp_path = f.name
    
    try:
        result = hash_file_sha256(temp_path)
        expected = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        assert result == expected
    finally:
        os.unlink(temp_path)


def test_hash_file_sha256_not_found() -> None:
    """测试文件不存在"""
    with pytest.raises(FileNotFoundError):
        hash_file_sha256('nonexistent_file.txt')