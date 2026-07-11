from pathlib import Path
import sys


if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.rag.vector_store import create_vector_store


if __name__ == "__main__":
    create_vector_store()
