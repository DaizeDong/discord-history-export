"""Reorganize DCE `exportguild` output into a category/channel structure.

Input layout (DCE writes this — see SKILL.md Gotcha G1):
    raw/<discord_id>/*.{html,json}
    where <discord_id> is either a category ID (folder holds main channel files)
    or a channel ID (folder holds that channel's thread files).

Output layout (this script writes this):
    organized/<category_name>/<channel>.<ext>
    organized/<category_name>/<channel>_threads/<thread>.<ext>
    organized/INDEX.md

Usage:
    python reorganize.py <raw_dir> <organized_dir> <channels_txt>

where <channels_txt> is the output of:
    DiscordChatExporter.Cli channels -t <token> -g <guild_id>
"""
import re
import shutil
import sys
from pathlib import Path


def slug(s: str) -> str:
    """Filesystem-safe version of a name. Keep spaces; replace illegal chars."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip().rstrip(".")


def parse_channels(channels_txt: Path) -> dict[str, tuple[str, str]]:
    """channel_id -> (category, channel_name). Category '' for root-level channels."""
    m: dict[str, tuple[str, str]] = {}
    for line in channels_txt.read_text(encoding="utf-8").splitlines():
        if " | " not in line:
            continue
        chan_id, _, name = line.partition(" | ")
        name = name.strip()
        if " / " in name:
            cat, ch = name.split(" / ", 1)
        else:
            cat, ch = "", name
        m[chan_id.strip()] = (cat, ch)
    return m


def file_id(p: Path) -> str | None:
    """Extract the [<discord-id>] suffix from a filename."""
    m = re.search(r"\[(\d{15,25})\]", p.name)
    return m.group(1) if m else None


def strip_id(name: str) -> str:
    """Remove '[<id>]' suffix from a filename, preserving the extension."""
    m = re.match(r"^(.*?)\s*\[\d{15,25}\](\.[a-z]+)$", name)
    return f"{m.group(1)}{m.group(2)}" if m else name


def main(src_root: Path, dst_root: Path, channels_txt: Path) -> None:
    chan = parse_channels(channels_txt)
    dst_root.mkdir(parents=True, exist_ok=True)

    folders = sorted(p for p in src_root.iterdir() if p.is_dir())
    summary: list[tuple[str, str, str, int, str]] = []
    unmapped: list[str] = []

    for folder in folders:
        files = sorted(folder.iterdir())
        if not files:
            continue

        if folder.name in chan:
            cat, ch = chan[folder.name]
            target = dst_root / slug(cat or "_root_channels") / f"{slug(ch)}_threads"
            target.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copy2(f, target / f.name)
            summary.append((cat, ch, "threads", len(files), str(target.relative_to(dst_root))))
            continue

        cat_for_files = next(
            (chan[fid][0] for f in files if (fid := file_id(f)) and fid in chan),
            None,
        )
        if cat_for_files is None:
            unmapped.append(folder.name)
            target = dst_root / "_unknown" / folder.name
            target.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copy2(f, target / f.name)
            summary.append(("?", "?", "unknown", len(files), str(target.relative_to(dst_root))))
            continue

        target_dir = dst_root / slug(cat_for_files or "_root_channels")
        target_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, target_dir / strip_id(f.name))
        summary.append((cat_for_files, "(category)", "main", len(files), str(target_dir.relative_to(dst_root))))

    with (dst_root / "INDEX.md").open("w", encoding="utf-8") as fh:
        fh.write("# Discord export — folder map\n\n")
        fh.write("| Category | Channel | Type | Files | Path |\n|---|---|---|---:|---|\n")
        for cat, ch, kind, n, path in summary:
            fh.write(f"| {cat or '(root)'} | {ch} | {kind} | {n} | `{path}` |\n")
        if unmapped:
            fh.write("\n## Unmapped folder IDs\n\n")
            for fid in unmapped:
                fh.write(f"- `{fid}` (kept under `_unknown/`)\n")

    print(f"reorganized {len(folders)} folders into {dst_root}")
    if unmapped:
        print(f"  ({len(unmapped)} unmapped — see INDEX.md)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
