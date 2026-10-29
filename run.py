#!/usr/bin/env python3
"""Entry point: python3 run.py [port]  (default 8765). No dependencies."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from app.server import main

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
