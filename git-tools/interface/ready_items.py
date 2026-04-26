#!/usr/bin/env python3
"""List Ready project items as JSON — pre-set interface for skill consumption."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_items import list_items

list_items(status="Ready", json_output=True)
