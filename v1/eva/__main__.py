"""Allows `python -m eva run ...`."""
from .cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
