"""Reorganize immutable DCE source files inside a verified private Git companion.

Usage: python reorganize.py RAW_DIR ORGANIZED_DIR CHANNELS_TXT
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_core import ExportError, organize


def main(src_root, dst_root, channels_txt):
    return organize(Path(src_root), Path(dst_root), Path(channels_txt))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    try:
        result = main(*sys.argv[1:])
        print(f"Complete: {result['summary']['artifact_count']} verified artifacts; private companion {result['companion']}.")
    except ExportError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (OSError, UnicodeError):
        print("Archive I/O failed. Check source access and destination permissions.", file=sys.stderr)
        sys.exit(1)
