# -*- coding: utf-8 -*-
"""
helix.storage
~~~~~~~~~~~~~

Warstwa trwałości dla Raft (Persistence Layer).
Zgodnie z "Paper", musimy persistować:
    - currentTerm
    - votedFor
    - log[] (Tu upraszczamy: brak pełnego logu w tej wersji demo, skupiamy się na wyborach)

Atomic Writes:
    Używamy techniki "write-rename" aby zapewnić atomowość zapisu pliku stanu.
"""

import json
import os
from pathlib import Path
from typing import Tuple, Optional

class RaftStorage:
    def __init__(self, node_id: int, data_dir: str = "./data"):
        self.node_id = node_id
        self.path = Path(data_dir) / f"node_{node_id}.state"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_state(self, term: int, voted_for: Optional[int]):
        """
        Zapisuje stan w sposób atomowy (odporny na crash w trakcie zapisu).
        """
        temp_path = self.path.with_suffix(".tmp")
        
        data = {
            "term": term,
            "voted_for": voted_for
        }
        
        # 1. Zapis do pliku tymczasowego
        with open(temp_path, "w") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno()) # Wymuszenie zapisu na dysk fizyczny
            
        # 2. Atomowa zamiana nazwy (OS rename)
        # To gwarantuje, że plik albo jest stary, albo nowy - nigdy uszkodzony.
        os.replace(temp_path, self.path)

    def load_state(self) -> Tuple[int, Optional[int]]:
        """Wczytuje (term, voted_for)."""
        if not self.path.exists():
            return 0, None
            
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                return data.get("term", 0), data.get("voted_for")
        except (json.JSONDecodeError, OSError):
            return 0, None
