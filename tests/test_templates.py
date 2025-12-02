# tests/test_templates.py
"""
Simple smoke tests to ensure templates and generator import and basic generation works.
Run with: pytest -q
"""

from src import rule_templates
from src import generator_with_nl
import json
import os

def test_templates_exist():
    assert hasattr(rule_templates, "TEMPLATES")
    assert len(rule_templates.TEMPLATES) >= 1

def test_generator_creates_file(tmp_path):
    # use a temporary output file to avoid overwriting project data
    out_file = tmp_path / "temp_rules.jsonl"
    # call generator.generate but with small override using monkeypatch of OUT_FILE
    generator_with_nl.OUT_FILE = str(out_file)
    generator_with_nl.generate(n=5)
    assert out_file.exists()
    # quick schema check for first line
    with open(out_file, "r", encoding="utf8") as f:
        line = f.readline()
        j = json.loads(line)
        assert "rule_id" in j
        assert "conditions" in j
        assert "actions" in j
