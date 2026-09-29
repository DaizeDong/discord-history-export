"""Generate the public examples and all synthetic archive test records."""
import argparse
import json
from pathlib import Path

IDS = {name: str(700000000000000000 + n) for n, name in enumerate(
    ("guild", "category", "other_category", "channel", "other_channel", "thread", "other_thread"), 1)}
SECRET = "SYNTHETIC_CREDENTIAL_DO_NOT_USE"


def ssh_alias_scenarios():
    """Ordinary SSH aliases and conservative unsupported-config controls."""
    alias = 'synthetic-gh'
    identity = 'example/synthetic-discord-config'
    ordinary = 'Host synthetic-gh\n  HostName github.com\n'
    return {'alias': alias, 'identity': identity, 'origin': 'git@'+alias+':'+identity+'.git',
            'ordinary': ordinary, 'cases': [
                ['scp', 'git@'+alias+':'+identity+'.git', ordinary, True],
                ['ssh-url', 'ssh://git@'+alias+'/'+identity+'.git', ordinary, True],
                ['multiple-hosts', 'git@'+alias+':'+identity+'.git', 'Host unused synthetic-gh\n HostName github.com\n', True],
                ['equals', 'git@'+alias+':'+identity+'.git', 'Host synthetic-gh\n HostName = "github.com" # synthetic\n', True],
                ['inactive-commands', 'git@'+alias+':'+identity+'.git', ordinary+' ProxyCommand synthetic-no-execute\n LocalCommand synthetic-no-execute\n', True],
                ['literal-https', 'https://github.com/'+identity+'.git', None, True],
                ['literal-ssh', 'git@github.com:'+identity+'.git', None, True],
                ['unknown', 'git@unknown-synthetic:'+identity+'.git', ordinary, False],
                ['missing', 'git@'+alias+':'+identity+'.git', None, False],
                ['unrelated', 'git@'+alias+':'+identity+'.git', 'Host synthetic-gh\n HostName example.com\n', False],
                ['lookalike', 'git@'+alias+':'+identity+'.git', 'Host synthetic-gh\n HostName github.com.example.com\n', False],
                ['first-value', 'git@'+alias+':'+identity+'.git', 'Host *\n HostName example.com\n'+ordinary, False],
                ['negated', 'git@'+alias+':'+identity+'.git', 'Host * !synthetic-gh\n HostName github.com\n', False],
                ['match-exec', 'git@'+alias+':'+identity+'.git', ordinary+'Match exec "synthetic-no-execute"\n', False],
                ['include', 'git@'+alias+':'+identity+'.git', 'Include synthetic-config\n'+ordinary, False],
                ['malformed', 'git@'+alias+':'+identity+'.git', 'Host "synthetic-gh\n HostName github.com\n', False],
                ['https-alias', 'https://'+alias+'/'+identity+'.git', ordinary, False],
                ['bad-slug', 'git@'+alias+':example/repo/extra.git', ordinary, False],
                ['wildcard', 'git@'+alias+':'+identity+'.git', 'Host synthetic-*\n HostName github.com\n', True],
                ['first-value-preserved', 'git@'+alias+':'+identity+'.git', ordinary+'Host *\n HostName example.com\n', True],
                ['compact-equals', 'git@'+alias+':'+identity+'.git', 'Host=synthetic-gh\n HostName=github.com\n', True],
                ['global-hostname', 'git@'+alias+':'+identity+'.git', 'HostName github.com\n', True],
                ['case-insensitive', 'git@SYNTHETIC-GH:'+identity+'.git', 'hOsT Synthetic-Gh\n HOSTNAME GitHub.com\n', True],
                ['literal-brackets', 'git@'+alias+':'+identity+'.git', 'Host [s]ynthetic-gh\n HostName github.com\n', False],
                ['canonicalization', 'git@'+alias+':'+identity+'.git', ordinary+' CanonicalizeHostname yes\n', False],
                ['empty-host', 'git@'+alias+':'+identity+'.git', 'Host\n HostName github.com\n', False],
                ['ssh-other-user', 'ssh://other@'+alias+'/'+identity+'.git', ordinary, False],
                ['scp-other-user', 'other@'+alias+':'+identity+'.git', ordinary, False],
                ['https-user', 'https://git@github.com/'+identity+'.git', None, False],
                ['ssh-password', 'ssh://git:synthetic@'+alias+'/'+identity+'.git', ordinary, False],
                ['ssh-query', 'ssh://git@'+alias+'/'+identity+'.git?x=1', ordinary, False],
                ['ssh-fragment', 'ssh://git@'+alias+'/'+identity+'.git#x', ordinary, False],
                ['trailing-slash', 'git@'+alias+':'+identity+'.git/', ordinary, True],
            ]}


def records():
    return {
        "ids": IDS,
        "credential": SECRET,
        "channels": "\n".join(f"{IDS[key]} | Acme / {name}" for key, name in (
            ("channel", "general"), ("other_channel", "GENERAL"))) + "\n",
        "message": {"id": "700000000000000099", "content": "Synthetic Acme fixture", "attachments": []},
        "data_selections": selection_cases(),
    }


def selection_cases():
    """Paired destination cases keep every rejected selection beside its positive controls."""
    return [
        {"kind": kind, "exists": exists, "allowed": kind.startswith("private"),
         "repository": "AcmeOrg/synthetic-" + kind + "-config"}
        for kind in ("private-normal", "private-linked", "own-source", "public", "unknown", "unversioned", "file")
        for exists in (True, False)
    ]


def selected_destination(root, source_root, case):
    """Build synthetic Git markers only in the supplied temporary fixture root."""
    root = Path(root)
    kind = case["kind"]
    if kind == "own-source":
        source = Path(source_root)
        return (source if case["exists"] else source / "synthetic-missing-selection"), None
    selected_root = root / ("synthetic-selected-" + kind)
    selected_root.mkdir()
    if kind not in ("unversioned", "file"):
        marker = selected_root / ".git"
        if kind == "private-linked":
            marker.write_text("gitdir: ../synthetic-main/.git/worktrees/selected\n", encoding="utf-8")
        else:
            marker.mkdir()
    selected = selected_root / "data"
    if kind == "file":
        selected.write_text("SYNTHETIC_NON_DIRECTORY", encoding="utf-8")
        if not case["exists"]:
            selected = selected / "missing-child"
    elif case["exists"]:
        selected.mkdir()
    else:
        selected = selected / "missing-child"
    return selected, selected_root


def populate(root, *, formats=("html", "json"), channels=("channel", "other_channel"), media=True):
    """Return reproducible source files without borrowing local user data."""
    root = Path(root)
    fixture = records()
    for key in channels:
        channel_id = IDS[key]
        container = IDS["channel"] if "thread" in key else IDS["category"]
        parent = root / container
        parent.mkdir(parents=True, exist_ok=True)
        name = "repeated title" if "thread" in key else "general"
        stem = f"{name} [{channel_id}]"
        asset = stem + "_Files/nested/asset.bin"
        if media:
            path = parent / asset
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"SYNTHETIC_ASSET\x00\x01")
        if "html" in formats:
            (parent / (stem + ".html")).write_text(
                '<!doctype html><meta charset="utf-8"><p>Synthetic Acme fixture</p>'
                + (f'<img src="{asset}">' if media else ""), encoding="utf-8")
        if "json" in formats:
            message = dict(fixture["message"])
            message["attachments"] = [{"url": asset}] if media else []
            data = {"guild": {"id": IDS["guild"], "name": "Acme"},
                    "channel": {"id": channel_id, "name": name, "categoryId": container},
                    "messages": [message]}
            (parent / (stem + ".json")).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return fixture


def generated():
    return {
        "catalog.json": json.dumps(records(), indent=2) + "\n",
        "example.md": "# Generated synthetic example\n\n"
        "These Acme IDs and records are generated by `tools/make_fixtures.py`.\n\n"
        "```powershell\n"
        'python "$SkillDir/scripts/export_history.py" plan --exporter "$Exporter" '
        f'--credential-ref env:DISCORD_BOT_TOKEN --run-id synthetic-demo --guild-id {IDS["guild"]}\n'
        "```\n\n"
        "After reviewing that scope, replace `plan` with `execute`. The environment variable is set locally; "
        "its value is never part of this command. `$SkillDir` is the installed skill directory and "
        "`$Exporter` is an existing DiscordChatExporter CLI executable.\n",
    }


def stylesheet_cases():
    return [
        ("visible-text", '<p>Example url(missing.bin)</p>', False),
        ("code-example", '<code>background: url(missing.bin)</code>', False),
        ("script-content", '<script>const example = "url(missing.bin)";</script>', False),
        ("html-comment", '<!-- Example url(missing.bin) -->', False),
        ("unrelated-attribute", '<p data-example="url(missing.bin)">Example</p>', False),
        ("css-comment", '<style>/* Example url(missing.bin) */</style>', False),
        ("css-string", '<style>p::after { content: "url(missing.bin)"; }</style>', False),
        ("non-css-style", '<style type="text/plain">url(missing.bin)</style>', False),
        ("style-element", '<style>p { background: url("asset.bin"); }</style>', True),
        ("style-attribute", '<p style="background: URL( asset.bin )">Example</p>', True),
        ("linked-css", '<link rel="stylesheet" href="theme.css">', True),
    ]


def populate_stylesheet_case(root, case, *, include_asset=True):
    root = Path(root)
    root.mkdir()
    name, markup, needs_asset = case
    (root / f"example [{IDS['channel']}].html").write_text(
        '<!doctype html><meta charset="utf-8">' + markup, encoding="utf-8")
    if name == "linked-css":
        (root / "theme.css").write_text('p { background: url("asset.bin"); }', encoding="utf-8")
    if needs_asset and include_asset:
        (root / "asset.bin").write_bytes(b"SYNTHETIC_CSS_ASSET\x00\x01")


def populate_destination_topology(root, case):
    root = Path(root)
    directory = {
        "exact-file-ancestor": f"room [{IDS['channel']}].json",
        "casefold-file-ancestor": f"ROOM [{IDS['channel']}].JSON",
        "valid-normalization": "room-data",
    }[case]
    for relative, channel in [("room.json", "channel"),
                              (f"{directory}/child [{IDS['other_channel']}].json", "other_channel")]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"channel": {"id": IDS[channel]},
                                    "messages": [records()["message"]]}), encoding="utf-8")



def probe_environment_cases():
    """Generate platform-sensitive credential names, with unrelated keys as controls."""
    environment = {key: SECRET for key in (
        "DISCORD_TOKEN", "discord_token", "Discord_Token",
        "Discord_Bot_Token", "DISCORD_BOT_TOKEN", "discord_bot_token")}
    environment["SYNTHETIC_KEEP"] = "synthetic-public-control"
    return [{"platform": platform, "kind": kind, "environment": dict(environment),
             "excluded": list(environment)[:-1] if platform == "nt" and kind == "env"
             else ["DISCORD_TOKEN", "discord_token", "Discord_Token"] if platform == "nt"
             else ["DISCORD_TOKEN", "Discord_Bot_Token"] if kind == "env"
             else ["DISCORD_TOKEN"]}
            for platform in ("nt", "posix") for kind in ("env", "file")]


def replay_receipt_cases():
    return ["omit-channel", "duplicate-html", "duplicate-pair", "omit-media", "raw-path", "wrong-source"]


def altered_replay_receipt(manifest, case):
    """Generate internally consistent receipt alterations while leaving archives untouched."""
    result = json.loads(json.dumps(manifest))
    entries = result["artifacts"]
    if case == "omit-channel":
        entries = [item for item in entries if item["channel_id"] != IDS["channel"]]
    elif case == "duplicate-html":
        entries.append(dict(next(item for item in entries if item["format"] == "html")))
    elif case == "duplicate-pair":
        entries.extend(dict(next(item for item in entries if item["format"] == fmt)) for fmt in ("html", "json"))
    elif case == "omit-media":
        entries = [item for item in entries if item["format"] != "media"]
    elif case == "raw-path":
        for item in entries:
            item["path"] = item["source"]
    elif case == "wrong-source":
        entries[0]["source"] = "attempts/9999/raw/synthetic-missing.json"
    else:
        raise ValueError("Unknown synthetic receipt alteration")
    result["artifacts"] = entries
    result["summary"] = {"artifact_count": len(entries),
                         "html_count": sum(item["format"] == "html" for item in entries),
                         "json_count": sum(item["format"] == "json" for item in entries),
                         "media_count": sum(item["format"] == "media" for item in entries),
                         "message_count": sum(item.get("message_count", 0) for item in entries if item["format"] == "json")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "tests" / "fixtures")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in generated().items():
        (args.out / name).write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
