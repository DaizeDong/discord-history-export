"""Generate the public examples and all synthetic archive test records."""
import argparse
import json
from pathlib import Path

IDS = {name: str(700000000000000000 + n) for n, name in enumerate(
    ("guild", "category", "other_category", "channel", "other_channel", "thread", "other_thread"), 1)}
SECRET = "SYNTHETIC_CREDENTIAL_DO_NOT_USE"


def mocked_transport_environment_cases():
    """Synthetic ambient keys for inert fixture-scope and guard-preservation controls."""
    blocked = (
        "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_ALLOW_PROTOCOL", "GIT_TERMINAL_PROMPT",
        "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
        "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0", "GIT_CONFIG_KEY_1",
        "GIT_CONFIG_VALUE_1", "GIT_TRACE2_EVENT", "GIT_SSH_COMMAND", "GIT_FUTURE_OVERRIDE",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "SSH_COMMAND", "SSL_CERT_FILE",
        "SSL_CERT_DIR", "CURL_CA_BUNDLE", "CURL_SSL_BACKEND", "GH_HOST",
    )
    return {
        "blocked": [(key, value) for name in blocked for key in (name, name.lower())
                    for value in ("SYNTHETIC_OVERRIDE", "")],
        "preserved": {"GIT_OPTIONAL_LOCKS": "0", "GH_HOST": "github.com",
                      "PATH": "SYNTHETIC_PATH", "SYNTHETIC_UNRELATED": "preserve"},
    }


def ssh_alias_scenarios():
    """Synthetic SSH configurations evaluated by the accepted public proof API."""
    alias = 'synthetic-gh'
    identity = 'example/synthetic-discord-config'
    ordinary = 'Host synthetic-gh\n  HostName github.com\n'
    return {'alias': alias, 'identity': identity, 'origin': 'git@'+alias+':'+identity+'.git',
            'ordinary': ordinary, 'cases': [
                ['scp', 'git@'+alias+':'+identity+'.git', ordinary, True],
                ['ssh-url', 'ssh://git@'+alias+'/'+identity+'.git', ordinary, True],
                ['multiple-hosts', 'git@'+alias+':'+identity+'.git', 'Host unused synthetic-gh\n HostName github.com\n', True],
                ['equals', 'git@'+alias+':'+identity+'.git', 'Host synthetic-gh\n HostName = "github.com" # synthetic\n', False],
                ['active-commands', 'git@'+alias+':'+identity+'.git', ordinary+' ProxyCommand synthetic-no-execute\n LocalCommand synthetic-no-execute\n', False],
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
                ['first-value-preserved', 'git@'+alias+':'+identity+'.git', ordinary+'Host *\n HostName example.com\n', False],
                ['compact-equals', 'git@'+alias+':'+identity+'.git', 'Host=synthetic-gh\n HostName=github.com\n', True],
                ['global-hostname', 'git@'+alias+':'+identity+'.git', 'HostName github.com\n', True],
                ['case-insensitive', 'git@SYNTHETIC-GH:'+identity+'.git', 'hOsT Synthetic-Gh\n HOSTNAME GitHub.com\n', False],
                ['literal-brackets', 'git@'+alias+':'+identity+'.git', 'Host [s]ynthetic-gh\n HostName github.com\n', False],
                ['canonicalization', 'git@'+alias+':'+identity+'.git', ordinary+' CanonicalizeHostname yes\n', False],
                ['empty-host', 'git@'+alias+':'+identity+'.git', 'Host\n HostName github.com\n', False],
                ['ssh-other-user', 'ssh://other@'+alias+'/'+identity+'.git', ordinary, False],
                ['scp-other-user', 'other@'+alias+':'+identity+'.git', ordinary, False],
                ['https-user', 'https://git@github.com/'+identity+'.git', None, True],
                ['ssh-password', 'ssh://git:synthetic@'+alias+'/'+identity+'.git', ordinary, False],
                ['ssh-query', 'ssh://git@'+alias+'/'+identity+'.git?x=1', ordinary, False],
                ['ssh-fragment', 'ssh://git@'+alias+'/'+identity+'.git#x', ordinary, False],
                ['trailing-slash', 'git@'+alias+':'+identity+'.git/', ordinary, False],
            ]}


def source6_ssh_verifier_cases():
    return [('verified', None, False, True), ('rejected', 'synthetic unsafe configuration', False, False),
            ('unavailable', None, True, False)]


def source6_http_configuration_cases():
    """Synthetic shared-policy controls, preserving every configuration occurrence."""
    cases = [
        ('header', [('http.extraheader', 'Host: mirror.example.invalid')], False),
        ('header-scoped', [('http.https://github.com/.extraheader', 'Host: mirror.example.invalid')], False),
        ('header-reset', [('http.extraheader', 'Host: mirror.example.invalid'), ('http.extraheader', '')], False),
        ('header-empty', [('http.extraheader', '')], False),
        ('redirect', [('http.followredirects', 'true')], False),
        ('redirect-scoped', [('http.https://github.com/.followredirects', 'false')], False),
        ('redirect-reset', [('http.followredirects', 'true'), ('http.followredirects', '')], False),
        ('unknown', [('http.newtransportoption', 'synthetic-option')], False),
        ('unknown-scoped', [('http.https://github.com/.newtransportoption', 'synthetic-option')], False),
        ('unknown-empty', [('http.newtransportoption', '')], False),
        ('verification-disabled', [('http.sslverify', 'false')], False),
        ('verification-reset', [('http.sslverify', 'false'), ('http.sslverify', 'true')], False),
        ('verification-empty', [('http.sslverify', ''), ('http.sslverify', 'true')], False),
        ('remote-proxy-option', [('remote.origin.proxyauthmethod', 'synthetic-option')], False),
    ]
    for value in ('true', 'yes', 'on', '1'):
        for prefix, scope in (('http.', 'global'), ('http.https://github.com/.', 'scoped')):
            cases.append(('verification-' + value + '-' + scope,
                          [(prefix + 'sslverify', ' ' + value.upper() + ' ')], True))
    for option, value in (
        ('version', 'HTTP/2'), ('maxrequests', '5'), ('minsessions', '1'),
        ('postbuffer', '1048576'), ('lowspeedlimit', '100'), ('lowspeedtime', '30'),
        ('keepaliveidle', '60'), ('keepaliveinterval', '10'), ('keepalivecount', '3'),
    ):
        for prefix, scope in (('http.', 'global'), ('http.https://github.com/.', 'scoped')):
            cases.append(('performance-' + option + '-' + scope, [(prefix + option, value)], True))
    return cases


def source6_publication_cases():
    """Generate nominal/effective route pairs with explicit synthetic visibility."""
    private = 'AcmeOrg/synthetic-discord-config'
    other = 'AcmeOrg/synthetic-secondary-config'
    public = 'AcmeOrg/synthetic-public-config'
    unknown = 'AcmeOrg/synthetic-unknown-config'
    https = lambda name: 'https://github.com/' + name + '.git'
    cases = []
    for name, fetch, push, allowed in [
        ('https-private', private, private, True),
        ('public-push', private, public, False),
        ('unknown-push', private, unknown, False),
        ('rewritten-public-fetch', public, private, False),
    ]:
        cases.append({'id': name, 'nominal': https(private), 'allowed': allowed,
                      'routes': {'origin': {'fetch': [https(fetch)], 'push': [https(push)]}},
                      'visibility': {private: 'PRIVATE', other: 'PRIVATE', public: 'PUBLIC', unknown: 'UNKNOWN'},
                      'config': [], 'environment': {}})
    for name, route, allowed in [('secondary-private', other, True), ('secondary-public', public, False)]:
        case = {**cases[0], 'id': name, 'allowed': allowed,
                'routes': {**cases[0]['routes'], 'publication': {'fetch': [https(route)], 'push': [https(route)]}},
                'config': [('remote.pushdefault', 'publication')]}
        cases.append(case)
    for name, configuration, environment in [
        ('unknown-pushremote', [('branch.master.pushremote', 'unlisted-publication')], {}),
        ('custom-remote-command', [('remote.origin.vcs', 'synthetic-command')], {}),
        ('git-config-environment', [], {'GIT_CONFIG_COUNT': '1'}),
    ]:
        cases.append({**cases[0], 'id': name, 'allowed': False, 'config': configuration, 'environment': environment})
    for name, configuration, environment, ssh_config in [
        ('ssh-command-environment', [], {'GIT_SSH_COMMAND': 'synthetic-never-execute'}, None),
        ('ssh-command-config', [('core.sshcommand', 'synthetic-never-execute')], {}, None),
        ('ssh-active-proxy', [], {}, 'Host github.com\n User git\n ProxyCommand synthetic-never-execute\n'),
    ]:
        url = 'git@github.com:' + private + '.git'
        cases.append({**cases[0], 'id': name, 'allowed': False, 'nominal': url,
                      'routes': {'origin': {'fetch': [url], 'push': [url]}},
                      'config': configuration, 'environment': environment, 'ssh_config': ssh_config,
                      'safe_ssh_config': 'Host github.com\n User git\n' if ssh_config else None})
    for name, configuration, allowed in source6_http_configuration_cases():
        cases.append({**cases[0], 'id': 'http-' + name, 'allowed': allowed,
                      'config': configuration, 'http_policy': True})
    return cases


def source6_nested_destination_cases():
    return [{'id': kind + '-' + action, 'visibility': visibility, 'linked': kind == 'private-linked',
             'allowed': visibility == 'PRIVATE', 'action': action,
             'repository': 'AcmeOrg/synthetic-nested-' + kind + '-config'}
            for kind, visibility in [('private', 'PRIVATE'), ('private-linked', 'PRIVATE'),
                                     ('public', 'PUBLIC'), ('unknown', 'UNKNOWN')]
            for action in ('plan', 'execute')]


def source6_nested_repository(path, *, linked=False):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if linked:
        (path / '.git').write_text('gitdir: ../synthetic-admin/worktrees/nested\n', encoding='utf-8')
    else:
        (path / '.git').mkdir()
    return path


def source6_credential(root):
    path = Path(root) / 'synthetic-source6-credential.txt'
    path.write_text(SECRET, encoding='utf-8')
    return path


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


def html_archive(markup="", *, count="1"):
    """Generate the stable document sections of the supported exporter template."""
    return ('<!doctype html><html><head><meta charset="utf-8"></head><body>'
            '<div class="preamble"><div class="preamble__entries-container">'
            '<div class="preamble__entry">Acme</div>'
            '<div class="preamble__entry">synthetic-channel</div></div></div>'
            '<div class="chatlog">' + markup + '</div>'
            '<div class="postamble"><div class="postamble__entry">'
            'Exported ' + count + ' message(s)</div>'
            '<div class="postamble__entry">Timezone: UTC+0</div></div></body></html>')


def source7_html_cases():
    return [(name, True) for name in ('valid', 'empty-channel', 'optional-end-tags', 'grouped-count')] + [
        (name, False) for name in ('zero-byte', 'whitespace', 'plain-text', 'service-page',
                                  'fragment', 'missing-footer', 'unclosed-chatlog', 'comment-markers',
                                  'script-markers', 'template-markers', 'negative-count')]


def source7_html_content(case):
    valid = html_archive('<p>Synthetic message</p>')
    if case == 'valid':
        return valid
    if case == 'empty-channel':
        return html_archive(count='0')
    if case == 'optional-end-tags':
        return valid.removesuffix('</body></html>')
    if case == 'grouped-count':
        return html_archive('<p>Synthetic localized count control</p>', count='1\u202f000')
    if case == 'zero-byte':
        return ''
    if case == 'whitespace':
        return '\n \t\n'
    if case == 'plain-text':
        return 'Synthetic exporter error: service unavailable.'
    if case == 'service-page':
        return '<!doctype html><html><body><h1>Service unavailable</h1></body></html>'
    if case == 'fragment':
        return '<!doctype html><p>Synthetic message</p>'
    if case == 'missing-footer':
        return valid.partition('<div class="postamble">')[0]
    if case == 'unclosed-chatlog':
        return valid.replace('</div><div class="postamble">', '<div class="postamble">')
    if case == 'comment-markers':
        return '<!doctype html><!--' + valid + '-->'
    if case == 'script-markers':
        return '<!doctype html><script type="application/json">' + json.dumps(valid) + '</script>'
    if case == 'template-markers':
        return '<!doctype html><template>' + valid + '</template>'
    if case == 'negative-count':
        return html_archive(count='-1')
    raise ValueError('Unknown synthetic HTML case')


def source7_apply_case(root, case):
    root = Path(root)
    for path in root.rglob('*.html'):
        path.write_text(source7_html_content(case), encoding='utf-8')
    if case == 'empty-channel':
        for path in root.rglob('*.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            data['messages'] = []
            path.write_text(json.dumps(data), encoding='utf-8')


def source7_legacy_complete(run, case):
    """Generate a byte-consistent historical receipt containing invalid HTML."""
    import hashlib
    run = Path(run)
    source7_apply_case(run / 'attempts', case)
    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for item in manifest['artifacts']:
        content = (run / item['path']).read_bytes()
        item.update(size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    manifest['files'] = []
    for path in sorted(run.rglob('*')):
        if path.is_file() and path != manifest_path:
            content = path.read_bytes()
            manifest['files'].append({'path': path.relative_to(run).as_posix(),
                                      'size_bytes': len(content),
                                      'sha256': hashlib.sha256(content).hexdigest()})
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


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
                html_archive('<p>Synthetic Acme fixture</p>'
                             + (f'<img src="{asset}">' if media else "")), encoding="utf-8")
        if "json" in formats:
            message = dict(fixture["message"])
            message["attachments"] = [{"url": asset}] if media else []
            data = {"guild": {"id": IDS["guild"], "name": "Acme"},
                    "channel": {"id": channel_id, "name": name, "categoryId": container},
                    "messages": [message]}
            (parent / (stem + ".json")).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return fixture


def source8_populate_tree(root, *, formats=("html", "json"),
                          channels=("channel", "other_channel"), media=False, empty=False):
    """Generate complete pairs in separate branches for inventory fault controls."""
    root = Path(root)
    for key in channels:
        branch = root / ("restricted" if key == "other_channel" else "readable")
        populate(branch, formats=formats, channels=(key,), media=media)
        if empty:
            source7_apply_case(branch, "empty-channel")
    return root / "restricted"


def source8_unrecorded_file(root):
    """Generate an extra file that cannot be omitted from an inventory."""
    target = Path(root) / "restricted" / "synthetic-unrecorded.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"SYNTHETIC_UNRECORDED_EVIDENCE\x00")
    return target.parent


def source9_css_cases():
    return [
        ("inline-double-missing", False), ("inline-single-missing", False),
        ("linked-missing", False), ("transitive-missing", False),
        ("url-import-missing", False), ("comment-separated-missing", False),
        ("quoted-present", True), ("uppercase-present", True),
        ("escaped-present", True), ("continued-present", True),
        ("transitive-present", True), ("cyclic-present", True),
        ("comment-only", True), ("unrelated-string", True),
        ("external-import", True),
    ]


def source9_populate_css(root, case):
    """Generate CSS dependency graphs with independently specified archive outcomes."""
    root = Path(root)
    root.mkdir()
    styles = {
        "inline-double-missing": '@import "missing.css";',
        "inline-single-missing": "@import 'missing.css';",
        "url-import-missing": '@import url("missing.css");',
        "comment-separated-missing": '@import/* synthetic comment */"missing.css";',
        "quoted-present": '@import "theme.css";',
        "uppercase-present": "@IMPORT 'theme.css' screen;",
        "escaped-present": '@import "th\\65 me.css";',
        "continued-present": '@import "the\\\nme.css";',
        "comment-only": '/* @import "missing.css"; */',
        "unrelated-string": "p::after { content: '@import \"missing.css\";'; }",
        "external-import": '@import "https://example.com/theme.css";',
    }
    files = {}
    if case in {"linked-missing", "transitive-missing", "transitive-present", "cyclic-present"}:
        markup = '<link rel="stylesheet" href="theme.css">'
        if case == "linked-missing":
            files["theme.css"] = '@import "missing.css";'
        else:
            files["theme.css"] = '@import "nested/second.css";'
            files["nested/second.css"] = ('@import "../theme.css";' if case == "cyclic-present"
                                           else '@import url("third.css");')
            if case == "transitive-present":
                files["nested/third.css"] = "p { color: navy; }"
    else:
        markup = "<style>" + styles[case] + "</style>"
        if case.endswith("present"):
            files["theme.css"] = "p { color: navy; }"
    (root / f"example [{IDS['channel']}].html").write_text(html_archive(markup), encoding="utf-8")
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def source9_guild_cases():
    return ["missing", "null", "empty", "null-id", "blank-id", "invalid-id",
            "wrong", "mixed-null", "matching"]


def source9_apply_guild(root, case):
    """Change only generated channel JSON, leaving unrelated manifests alone."""
    for path in sorted(Path(root).rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "channel" not in data or "messages" not in data:
            continue
        if case == "mixed-null" and str(data["channel"]["id"]) != IDS["other_channel"]:
            continue
        if case == "missing":
            data.pop("guild", None)
        else:
            data["guild"] = {
                "null": None, "mixed-null": None, "empty": {}, "null-id": {"id": None},
                "blank-id": {"id": ""}, "invalid-id": {"id": "synthetic-invalid"},
                "wrong": {"id": IDS["other_channel"]}, "matching": {"id": IDS["guild"]},
            }[case]
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def source9_legacy_guild(run, case):
    """Generate a self-consistent historical receipt with absent guild evidence."""
    import hashlib
    run = Path(run)
    source9_apply_guild(run / "attempts", case)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["artifacts"]:
        content = (run / item["path"]).read_bytes()
        item.update(size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        if item["format"] == "json":
            guild = json.loads(content).get("guild")
            item.pop("guild_id", None)
            if isinstance(guild, dict) and guild.get("id") is not None:
                item["guild_id"] = str(guild["id"])
    manifest["files"] = []
    for path in sorted(run.rglob("*")):
        if path.is_file() and path != manifest_path:
            content = path.read_bytes()
            manifest["files"].append({"path": path.relative_to(run).as_posix(),
                                      "size_bytes": len(content),
                                      "sha256": hashlib.sha256(content).hexdigest()})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def generated():
    return {
        "test_native_storage.py": native_storage_test_source(),
        "catalog.json": json.dumps(records(), indent=2) + "\n",
        "source15-cases.json": json.dumps({"links": source15_file_link_cases(), "archives": source15_archive_cases()}, indent=2) + "\n",
        "source16-cases.json": json.dumps({"links": source16_link_cases(), "archives": source16_archive_cases()}, indent=2) + "\n",
        "source14-cases.json": json.dumps(source14_stylesheet_cases(), indent=2) + "\n",
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
        html_archive(markup), encoding="utf-8")
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


def review10_hook(root, hook, source_body, target_kind):
    """Generate a consumer forwarder and an inert delegated guard for native hook checks."""
    root = Path(root)
    path = root / ".githooks" / hook
    path.parent.mkdir(parents=True)
    path.write_bytes(source_body)
    target = root / "guards/hooks" / hook
    target.parent.mkdir(parents=True)
    if target_kind == "directory":
        target.mkdir()
    elif target_kind != "missing":
        body = ("#!/bin/sh\nprintf '%s\\n' synthetic-guard-ran\nprintf 'arg:%s\\n' \"$@\"\n"
                "while IFS= read -r line; do printf 'stdin:%s\\n' \"$line\"; done\n"
                f"exit {7 if target_kind == 'failure' else 0}\n")
        target.write_text("" if target_kind == "empty" else body, encoding="utf-8", newline="\n")
    args = ["synthetic-first", "synthetic two words", "synthetic\\path"]
    stdin = "synthetic input\nsynthetic\\input\n"
    expected = ("synthetic-guard-ran\n" + "".join("arg:%s\n" % arg for arg in args)
                + "".join("stdin:%s\n" % line for line in stdin.splitlines()))
    return {"path": path, "args": args, "stdin": stdin, "expected_stdout": expected,
            "expected_exit": 7 if target_kind == "failure" else 0 if target_kind == "valid" else 1}



def source11_environment_cases():
    cases = [("clean", {}, True), ("ordinary-lock-setting", {"git_optional_locks": "1"}, True),
             ("canonical-host", {"gh_host": "github.com"}, True),
             ("wrong-host", {"gh_host": "example.com"}, False)]
    for key in ("SSL_CERT_FILE", "SSL_CERT_DIR", "CURL_CA_BUNDLE", "CURL_SSL_BACKEND"):
        for spelling, value in ((key, "synthetic-trust"), (key.lower(), "synthetic-trust"), (key, "")):
            cases.append((spelling + ("-empty" if not value else "-value"), {spelling: value}, False))
    return cases


def source11_transport_configs():
    return [
        ("http.version", "HTTP/2", True),
        ("http.sslcainfo", "synthetic-ca.pem", False),
        ("http.https://github.com/.sslcapath", "synthetic-ca", False),
        ("http.sslbackend", "synthetic-backend", False),
        ("http.sslverify", "false", False),
        ("http.schannelusesslcainfo", "true", False),
        ("http.pinnedpubkey", "synthetic-key.pem", False),
    ]


def source11_html_cases():
    return [(name, True) for name in ("valid", "ordinary-title", "void-self-closing", "textarea-before")] + [
        (name, False) for name in ("xmp", "title", "iframe", "noembed", "noframes", "plaintext",
                                  "script-self-closing", "style-self-closing", "textarea-self-closing",
                                  "template-self-closing", "div-self-closing")]


def source11_html_content(case):
    valid = html_archive(count="0")
    if case == "valid":
        return valid
    if case == "ordinary-title":
        return valid.replace("</head>", "<title>Synthetic channel</title></head>")
    if case == "void-self-closing":
        return valid.replace("<div class=\"chatlog\">", '<div class="chatlog"><br/><img src="data:image/png;base64,AA=="/>')
    if case == "textarea-before":
        return valid.replace("<body>", '<body><textarea><div class="preamble">Synthetic text</div></textarea>')
    if case in {"xmp", "title", "iframe", "noembed", "noframes", "plaintext"}:
        return valid.replace("<body>", "<body><" + case + ">").replace("</body>", "</" + case + "></body>")
    if case.endswith("-self-closing"):
        return valid.replace("<body>", "<body><" + case.removesuffix("-self-closing") + "/>")
    raise ValueError("Unknown source11 synthetic HTML case")


def source11_css_cases():
    return [
        ("literal-missing", 'body { background: url("tile.bin") }', False, False),
        ("literal-present", 'body { background: url("tile.bin") }', True, True),
        ("escaped-url-missing", 'body { background: u\\72l("tile.bin") }', False, False),
        ("escaped-url-present", 'body { background: u\\72l("tile.bin") }', True, True),
        ("escaped-uppercase-present", 'body { background: \\55RL("tile.bin") }', True, True),
        ("escaped-import-missing", '@\\69mport "tile.bin";', False, False),
        ("escaped-import-present", '@\\69mport "tile.bin";', True, True),
        ("escaped-import-url-missing", '@\\69mport u\\72l("tile.bin");', False, False),
        ("escaped-value-present", 'body { background: u\\72l("t\\69 le.bin") }', True, True),
        ("comment-only", '/* u\\72l("tile.bin") */', False, True),
        ("string-only", 'body::after { content: \'u\\72l("tile.bin")\'; }', False, True),
        ("different-identifier", 'body { synthetic-u\\72l("tile.bin") }', False, True),
    ]


def source11_workspace(root):
    root = Path(root)
    companion = root / "synthetic-companion"
    (companion / ".git").mkdir(parents=True)
    channels = root / "synthetic-channels.txt"
    channels.write_text(records()["channels"], encoding="utf-8")
    return {"companion": companion, "data": companion / "data", "channels": channels,
            "environment": {"DISCORD_HISTORY_EXPORT_DATA_DIR": str(companion / "data"),
                            "SYNTHETIC_BOT_TOKEN": SECRET},
            "exporter": "synthetic-exporter", "slug": "AcmeOrg/synthetic-review-config",
            "mutation": {"HTTPS_PROXY": "https://synthetic-proxy.example.com"}}


def source11_cli(exporter, action="execute", resume=False):
    result = [action, "--exporter", exporter, "--credential-ref", "env:SYNTHETIC_BOT_TOKEN",
              "--run-id", "synthetic-run", "--channel-id", IDS["channel"]]
    return result + (["--resume"] if resume else [])


def source11_archive(root, kind, case, formats=("html", "json")):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    channel = IDS["channel"]
    if "html" in formats:
        if kind == "html":
            markup = source11_html_content(case)
        elif kind == "legacy-html":
            markup = source7_html_content(case)
        elif kind == "css":
            markup = html_archive('<link rel="stylesheet" href="media/theme.css">', count="0")
            _, css, asset, _ = next(item for item in source11_css_cases() if item[0] == case)
            (root / "media").mkdir()
            (root / "media/theme.css").write_text(css, encoding="utf-8")
            if asset:
                (root / "media/tile.bin").write_bytes(b"SYNTHETIC_SOURCE11_ASSET")
        else:
            raise ValueError("Unknown source11 synthetic archive kind")
        (root / ("synthetic [" + channel + "].html")).write_text(markup, encoding="utf-8")
    if "json" in formats:
        record = {"guild": {"id": IDS["guild"]}, "channel": {"id": channel}, "messages": []}
        (root / ("synthetic [" + channel + "].json")).write_text(json.dumps(record), encoding="utf-8")


def source11_legacy_complete(run, kind, case):
    """Generate matching old receipts whose archive content now needs rejection."""
    import hashlib
    run = Path(run)
    if kind == "html":
        for path in (run / "attempts").rglob("*.html"):
            path.write_text(source11_html_content(case), encoding="utf-8")
    elif kind == "css":
        _, css, _, _ = next(item for item in source11_css_cases() if item[0] == case)
        for path in (run / "attempts").rglob("theme.css"):
            path.write_text(css, encoding="utf-8")
    else:
        raise ValueError("Unknown source11 legacy archive kind")
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["artifacts"]:
        content = (run / item["path"]).read_bytes()
        item.update(size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    manifest["files"] = []
    for path in sorted(run.rglob("*")):
        if path.is_file() and path != manifest_path:
            content = path.read_bytes()
            manifest["files"].append({"path": path.relative_to(run).as_posix(),
                                      "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")



def source12_svg_cases():
    return [(name, True) for name in ('svg-path', 'svg-use', 'svg-explicit', 'svg-title')] + [
        (name, False) for name in ('svg-unclosed', 'svg-wrong-close', 'svg-html-div',
                                   'html-script', 'html-style', 'html-template', 'html-div',
                                   'foreignobject-script', 'foreignobject-style', 'foreignobject-template', 'foreignobject-div')]


def source12_srcset_cases():
    data = 'data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%3E%3C/svg%3E'
    return [
        ('data-local', data + ' 1x, media/fallback.bin 2x', [data, 'media/fallback.bin']),
        ('data-comma-local', 'data:image/png;base64,QUJD, media/fallback.bin 2x',
         ['data:image/png;base64,QUJD', 'media/fallback.bin']),
        ('two-local', 'media/first.bin 1x, media/fallback.bin 2x', ['media/first.bin', 'media/fallback.bin']),
        ('compact-descriptors', 'media/first.bin 1x,media/fallback.bin 2x', ['media/first.bin', 'media/fallback.bin']),
        ('comma-in-url', 'media/first,second.bin 1x, media/fallback.bin 2x', ['media/first,second.bin', 'media/fallback.bin']),
        ('ascii-space', '\t' + data + '\n1x,\fmedia/fallback.bin\r2x', [data, 'media/fallback.bin']),
    ]


def source12_html_content(case):
    definitions = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">'
                   '<defs><symbol id="synthetic-icon" viewBox="0 0 16 16">'
                   '<path d="M1 1h6v6H1z" /></symbol></defs></svg>')
    reference = ('<svg class="synthetic-icon" viewBox="0 0 16 16">'
                 '<use href="#synthetic-icon" /></svg>')
    if case == 'svg-path':
        markup = definitions + '<p>Synthetic message</p>'
    elif case == 'svg-use':
        markup = '<div class="synthetic-message">' + reference + '<span>Synthetic message</span></div>'
    elif case == 'svg-explicit':
        markup = definitions.replace('<path d="M1 1h6v6H1z" />', '<path d="M1 1h6v6H1z"></path>') + reference.replace('<use href="#synthetic-icon" />', '<use href="#synthetic-icon"></use>')
    elif case == 'svg-title':
        markup = '<svg><title>Synthetic icon</title><path d="M0 0h1" /></svg>'
    elif case == 'svg-unclosed':
        markup = '<svg><path d="M0 0h1" />'
    elif case == 'svg-wrong-close':
        markup = '<svg><g><path d="M0 0h1" /></svg>'
    elif case == 'svg-html-div':
        markup = '<svg><div /></svg>'
    elif case.startswith('html-'):
        markup = '<' + case.removeprefix('html-') + ' />'
    elif case.startswith('foreignobject-'):
        markup = '<svg><foreignObject><' + case.removeprefix('foreignobject-') + ' /></foreignObject></svg>'
    else:
        base = case.removesuffix('-missing')
        _, value, _ = next(row for row in source12_srcset_cases() if row[0] == base)
        markup = '<img alt="Synthetic attachment" srcset="' + value + '">'
    document = html_archive(markup, count="0")
    return document.replace("<body>", "<body>" + definitions, 1) if case == "svg-use" else document


def source12_archive(root, case, formats=('html', 'json')):
    source11_archive(root, 'html', 'valid', formats)
    root = Path(root)
    if 'html' not in formats:
        return
    for path in root.glob('*.html'):
        path.write_text(source12_html_content(case), encoding='utf-8')
    base = case.removesuffix('-missing')
    item = next((row for row in source12_srcset_cases() if row[0] == base), None)
    if item:
        for relative in item[2]:
            if relative.startswith('data:') or (case.endswith('-missing') and relative == 'media/fallback.bin'):
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'SYNTHETIC_SOURCE12_MEDIA')


def source13_css_forms():
    """Literal expectations describe CSS resource tokens, including ignored strings."""
    return [
        ("string", 'image-set("ASSET" 1x)', ["ASSET"]),
        ("prefixed-case", '-WeBkIt-ImAgE-SeT("ASSET" 1x)', ["ASSET"]),
        ("escaped-name", r'im\61ge-set("ASSET" 1x)', ["ASSET"]),
        ("escaped-resource", r'image-set("t\69 le.bin" 1x)', ["tile.bin"]),
        ("mixed", 'image-set("ASSET" 1x, url("ALTERNATE") 2x)', ["ASSET", "ALTERNATE"]),
        ("typed-gradient", 'image-set("ASSET" type("image/png") 1x, linear-gradient(red, blue) 2x)', ["ASSET"]),
        ("comment-single", "image-set(/* synthetic */ 'ASSET' 1x, /* ignored */ url('ALTERNATE') 2x)", ["ASSET", "ALTERNATE"]),
        ("nested", 'cross-fade(image-set("ASSET" 1x), linear-gradient(red, blue), 50%)', ["ASSET"]),
        ("remote-type", 'image-set("https://example.com/tile.png" type("image/png") 1x)', ["https://example.com/tile.png"]),
        ("data", 'image-set("data:image/png;base64,QUJD" 1x)', ["data:image/png;base64,QUJD"]),
        ("fragment", 'image-set("#synthetic-image" 1x)', ["#synthetic-image"]),
        ("comment", '/* image-set("absent.bin" 1x) */ none', []),
        ("ordinary-string", "'image-set(\"absent.bin\" 1x)'", []),
        ("unrelated-function", 'synthetic-image-set("absent.bin" 1x)', []),
        ("descriptor-string", 'image-set(url("https://example.com/tile.png") type("absent.bin") 1x)', ["https://example.com/tile.png"]),
    ]


def source13_css_cases():
    cases = []
    for form, expression, references in source13_css_forms():
        # Every form gets linked CSS. Representative forms also cover all entry paths.
        placements = ["linked"]
        if form in {"string", "mixed", "escaped-name", "typed-gradient"}:
            placements += ["style-element", "style-attribute", "recursive-linked"]
        local = [ref for ref in references if ref in {"ASSET", "ALTERNATE", "tile.bin"}]
        for placement in placements:
            for present in ([False, True] if local else [False]):
                prefix = "media/" if placement.startswith("style-") else ""
                css = expression.replace("ASSET", prefix + "tile.bin").replace("ALTERNATE", prefix + "alternate.bin")
                expected = [ref.replace("ASSET", prefix + "tile.bin").replace("ALTERNATE", prefix + "alternate.bin")
                            for ref in references]
                cases.append({"name": form + "-" + placement + ("-present" if present else "-missing"),
                              "kind": "css", "form": form, "placement": placement,
                              "css": css, "references": expected,
                              "asset_names": ["tile.bin"] + (["alternate.bin"] if "ALTERNATE" in local else []),
                              "needs_assets": bool(local), "present": present,
                              "allowed": present or not local})
    return cases


def source13_svg_cases():
    local = "media/tile.bin"
    variants = [
        ("image", '<svg xmlns:xlink="http://www.w3.org/1999/xlink"><image xlink:href="RESOURCE"/></svg>', local, True),
        ("image-uppercase", '<SVG><IMAGE XLINK:HREF="RESOURCE"/></SVG>', local, True),
        ("use", '<svg><use xlink:href="RESOURCE#synthetic-symbol"/></svg>', local, True),
        ("filter-image", '<svg><filter><feImage xlink:href="RESOURCE"/></filter></svg>', local, True),
        ("ordinary-href", '<svg><image href="RESOURCE"/></svg>', local, True),
        ("nested-svg", '<svg><foreignObject><svg><image xlink:href="RESOURCE"/></svg></foreignObject></svg>', local, True),
        ("fragment", '<svg><use xlink:href="RESOURCE"/></svg>', "#synthetic-symbol", False),
        ("remote", '<svg><image xlink:href="RESOURCE"/></svg>', "https://example.com/tile.png", False),
        ("data", '<svg><image xlink:href="RESOURCE"/></svg>', "data:image/png;base64,QUJD", False),
        ("html-context", '<span xlink:href="RESOURCE">Synthetic text</span>', local, False),
        ("integration-context", '<svg><foreignObject><span xlink:href="RESOURCE">Synthetic text</span></foreignObject></svg>', local, False),
        ("unknown-prefix", '<svg xmlns:other="http://www.w3.org/1999/xlink"><image other:href="RESOURCE"/></svg>', local, False),
        ("post-svg-html", '<svg><path d="M0 0h1"/></svg><span xlink:href="RESOURCE">Synthetic text</span>', local, False),
    ]
    cases = []
    for name, markup, resource, needs_asset in variants:
        for present in ([False, True] if needs_asset else [False]):
            cases.append({"name": "svg-" + name + ("-present" if present else "-missing"),
                          "kind": "svg", "markup": markup.replace("RESOURCE", resource),
                          "present": present, "needs_assets": needs_asset,
                          "asset_names": ["tile.bin"], "allowed": present or not needs_asset})
    return cases


def source13_archive(root, case, formats=("html", "json")):
    """Generate synthetic complete envelopes and declarative dependency variants."""
    from html import escape
    root = Path(root)
    source11_archive(root, "html", "valid", formats)
    if "html" not in formats:
        return
    if case["kind"] == "css":
        css = "body { background-image: " + case["css"] + "; }"
        placement = case["placement"]
        if placement == "style-element":
            markup = "<style>" + css + "</style>"
            asset_dir = root / "media"
        elif placement == "style-attribute":
            markup = '<div style="' + escape("background-image: " + case["css"], quote=True) + '">Synthetic</div>'
            asset_dir = root / "media"
        else:
            markup = '<link rel="stylesheet" href="media/theme.css">'
            asset_dir = root / "media"
            asset_dir.mkdir(parents=True, exist_ok=True)
            if placement == "recursive-linked":
                (asset_dir / "theme.css").write_text('@import "nested/theme.css";', encoding="utf-8")
                asset_dir = asset_dir / "nested"
                asset_dir.mkdir(parents=True, exist_ok=True)
            (asset_dir / "theme.css").write_text(css, encoding="utf-8")
    else:
        markup = case["markup"]
        asset_dir = root / "media"
    document = html_archive(markup, count="0")
    for path in root.glob("*.html"):
        path.write_text(document, encoding="utf-8")
    if case["present"] and case["needs_assets"]:
        asset_dir.mkdir(parents=True, exist_ok=True)
        for name in case["asset_names"]:
            (asset_dir / name).write_bytes(b"SYNTHETIC_SOURCE13_ASSET")


def source13_valid_replay_case(case):
    """Generate a complete no-asset control before adding a missing dependency."""
    if case["kind"] == "css":
        return dict(case, css='image-set("https://example.com/tile.png" 1x)',
                    references=["https://example.com/tile.png"],
                    present=False, needs_assets=False, allowed=True)
    return dict(case, markup='<svg><image xlink:href="https://example.com/tile.png"/></svg>',
                present=False, needs_assets=False, allowed=True)


def source13_complete_with_missing_dependency(run, case):
    """Generate self-consistent old completion receipts from a valid no-asset run."""
    import hashlib
    run = Path(run)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    attempt = run / "attempts" / ("%04d" % manifest["attempt"])
    source13_archive(attempt / "raw/html", case, ("html",))
    source13_archive(attempt / "organized/archive/html", case, ("html",))
    for item in manifest["artifacts"]:
        content = (run / item["path"]).read_bytes()
        item.update(size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    manifest["files"] = []
    for path in sorted(run.rglob("*")):
        if path.is_file() and path != manifest_path:
            content = path.read_bytes()
            manifest["files"].append({"path": path.relative_to(run).as_posix(),
                                      "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def source14_css_role_cases():
    """Generate CSS resource roles without changing the existing string-list API."""
    return [
        ("quoted-import", '@import "theme";', ["theme"], ["theme"]),
        ("url-import", '@import url("theme");', ["theme"], ["theme"]),
        ("bare-url-import", '@import URL(theme);', ["theme"], ["theme"]),
        ("escaped-import", r'@\69mport/**/u\72l("theme");', ["theme"], ["theme"]),
        ("import-and-image", '@import "theme"; p { background:url(tile); }', ["theme", "tile"], ["theme"]),
        ("ordinary-url", 'p { background:url(theme); }', ["theme"], []),
        ("image-set", 'p { background:image-set("theme" 1x); }', ["theme"], []),
        ("ordinary-string", 'p::before {content:"@import theme";}', [], []),
        ("comment", '/* @import "theme"; */', [], []),
        ("remote-import", '@import "https://example.com/theme";', ["https://example.com/theme"], ["https://example.com/theme"]),
    ]


def source14_stylesheet_cases():
    """Generate complete and incomplete local stylesheet graphs, including role promotion."""
    first, second = IDS["channel"], IDS["other_channel"]
    cases = []

    def emit(name, markup, assets, allowed=True, *, other_markup=None, owners=None, business=True):
        files = {"synthetic [" + first + "].html": html_archive(markup, count="0").encode("utf-8")}
        if other_markup is not None:
            files["synthetic [" + second + "].html"] = html_archive(other_markup, count="0").encode("utf-8")
        files.update({path: value.encode("utf-8") if isinstance(value, str) else value
                      for path, value in assets.items()})
        owner_map = {path: [first] for path in assets}
        if owners:
            owner_map.update(owners)
        cases.append({"name": name, "allowed": allowed, "business": business and other_markup is None,
                      "files": {path: value.hex() for path, value in sorted(files.items())},
                      "owners": owner_map})

    def dependency(name, markup, assets, leaf="media/tile.bin"):
        for present in (False, True):
            current = dict(assets)
            if present:
                current[leaf] = b"SYNTHETIC_SOURCE14_ASSET\x00\xff"
            emit(name + ("-present" if present else "-missing"), markup, current, present)

    dependency("link-extensionless", '<link rel="stylesheet" href="media/theme">',
               {"media/theme": 'p{background:url("tile.bin");}'})
    dependency("link-other-suffix", '<link rel="stylesheet" href="media/theme.txt">',
               {"media/theme.txt": 'p{background:url("tile.bin");}'})
    dependency("link-rel-token-and-query", '<link href="media/theme?rev=2#part" rel="alternate StYlEsHeEt">',
               {"media/theme": 'p{background:url("tile.bin");}'})
    dependency("inline-quoted-import", '<style>@import "media/theme";</style>',
               {"media/theme": 'p{background:url("tile.bin");}'})
    dependency("inline-url-import", '<style>@import url("media/theme");</style>',
               {"media/theme": 'p{background:url("tile.bin");}'})
    dependency("inline-escaped-import", r'<style>@\69mport/**/u\72l("media/theme");</style>',
               {"media/theme": 'p{background:url("tile.bin");}'})
    dependency("recursive-quoted-import", '<link rel="stylesheet" href="media/root.css">',
               {"media/root.css": '@import "nested/theme";',
                "media/nested/theme": 'p{background:url("tile.bin");}'}, "media/nested/tile.bin")
    dependency("recursive-url-import", '<link rel="stylesheet" href="media/root">',
               {"media/root": '@import url("nested/theme.dat");',
                "media/nested/theme.dat": 'p{background:url("tile.bin");}'}, "media/nested/tile.bin")
    dependency("three-stylesheets", '<link rel="stylesheet" href="media/root">',
               {"media/root": '@import "middle";', "media/middle": '@import url("leaf.dat");',
                "media/leaf.dat": 'p{background:url("tile.bin");}'})
    dependency("self-import-cycle", '<link rel="stylesheet" href="media/theme">',
               {"media/theme": '@import "theme";p{background:url("tile.bin");}'})
    dependency("two-import-cycle", '<link rel="stylesheet" href="media/a">',
               {"media/a": '@import "b";', "media/b": '@import url("a");p{background:url("tile.bin");}'})
    dependency("late-role-same-owner", '<img src="media/theme"><link rel="stylesheet" href="media/root.css">',
               {"media/theme": 'p{background:url("tile.bin");}', "media/root.css": '@import "theme";'})
    dependency("ordinary-css-suffix", '<img src="media/theme.css">',
               {"media/theme.css": 'p{background:url("tile.bin");}'})

    for name, markup in [
            ("ordinary-image", '<img src="media/blob">'),
            ("ordinary-anchor", '<a href="media/blob">Synthetic</a>'),
            ("ordinary-icon", '<link rel="icon" href="media/blob">'),
            ("ordinary-inline-url", '<style>p{background:url("media/blob");}</style>'),
            ("ordinary-image-set", '<style>p{background:image-set("media/blob" 1x);}</style>')]:
        emit(name, markup, {"media/blob": 'p{background:url("missing.bin");}'})
    emit("ordinary-binary", '<img src="media/blob">', {"media/blob": b"\xff\x00SYNTHETIC_BINARY"})
    emit("non-css-style", '<style type="text/plain">@import "missing";</style>', {})
    emit("remote-import", '<style>@import url("https://example.com/theme");</style>', {})
    emit("missing-direct-stylesheet", '<link rel="stylesheet" href="media/missing">', {}, False)
    emit("escaping-transitive-asset", '<link rel="stylesheet" href="media/theme">',
         {"media/theme": 'p{background:url("../../outside.bin");}'}, False, business=False)
    emit("invalid-utf8-stylesheet", '<link rel="stylesheet" href="media/theme">',
         {"media/theme": b"\xff\xfeSYNTHETIC_INVALID_UTF8"}, False, business=False)
    emit("unowned-ordinary-asset", "", {"media/blob": b"SYNTHETIC_UNREFERENCED"}, False, business=False)
    shared = {"media/root.css": '@import "shared";', "media/shared": '@import "nested";',
              "media/nested": 'p{background:url("tile.bin");}',
              "media/tile.bin": b"SYNTHETIC_SHARED"}
    owners = {"media/shared": sorted([first, second]), "media/nested": sorted([first, second]),
              "media/tile.bin": sorted([first, second])}
    emit("shared-owner-promotion", '<link rel="stylesheet" href="media/root.css">', shared,
         other_markup='<img src="media/shared">', owners=owners, business=False)
    reverse = dict(owners, **{"media/root.css": [second]})
    emit("shared-owner-reverse-order", '<img src="media/shared">', shared,
         other_markup='<link rel="stylesheet" href="media/root.css">', owners=reverse, business=False)
    return cases


def source14_archive(root, case, formats=("html", "json")):
    """Materialize only generator-owned synthetic data for ordinary business-path tests."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if "html" in formats:
        for relative, encoded in case["files"].items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes.fromhex(encoded))
    if "json" in formats:
        record = {"guild": {"id": IDS["guild"]}, "channel": {"id": IDS["channel"]}, "messages": []}
        (root / ("synthetic [" + IDS["channel"] + "].json")).write_text(
            json.dumps(record), encoding="utf-8")



def source15_file_link_cases():
    """Generate portable links and forbidden machine-local file URLs."""
    return [
        {"name": "file-localhost", "link": "file://localhost/synthetic/missing.bin", "result": "absolute"},
        {"name": "file-server", "link": "file://server/synthetic/missing.bin", "result": "absolute"},
        {"name": "file-localhost-empty-path", "link": "file://localhost", "result": "absolute"},
        {"name": "file-server-empty-path", "link": "file://server", "result": "absolute"},
        {"name": "file-root", "link": "file:///synthetic/missing.bin", "result": "absolute"},
        {"name": "file-single-slash", "link": "file:/synthetic/missing.bin", "result": "absolute"},
        {"name": "file-relative-form", "link": "file:media/asset.bin", "result": "absolute"},
        {"name": "file-mixed-case", "link": "FiLe://LoCaLhOsT/C:/synthetic/missing.bin", "result": "absolute"},
        {"name": "file-encoded-path", "link": "file://server/synthetic/missing%20asset.bin", "result": "absolute"},
        {"name": "http", "link": "http://example.com/synthetic.bin", "result": "external"},
        {"name": "https", "link": "https://example.com/synthetic.bin", "result": "external"},
        {"name": "protocol-relative", "link": "//example.com/synthetic.bin", "result": "absolute"},
        {"name": "data", "link": "data:image/png;base64,U1lOVEg=", "result": "external"},
        {"name": "fragment", "link": "#synthetic", "result": "external"},
        {"name": "portable", "link": "media/asset.bin", "result": "local"},
        {"name": "portable-query-fragment", "link": "media/asset.bin?revision=1#synthetic", "result": "local"},
        {"name": "portable-missing", "link": "media/missing.bin", "result": "missing"},
        {"name": "absolute-path", "link": "/synthetic/missing.bin", "result": "absolute"},
    ]


def source15_archive_cases():
    """Put authority-bearing file URLs through complete synthetic HTML and CSS."""
    cases = []
    first = IDS["channel"]
    for context in ("image", "anchor", "inline-css", "linked-css"):
        for kind, allowed in (("file-localhost", False), ("file-server", False),
                              ("https", True), ("protocol-relative", False),
                              ("portable-present", True), ("portable-missing", False)):
            assets = {}
            if kind.startswith("file-"):
                authority = "localhost" if kind == "file-localhost" else "server"
                link = "file://" + authority + "/synthetic/missing.bin"
            elif kind == "https":
                link = "https://example.com/synthetic.bin"
            elif kind == "protocol-relative":
                link = "//example.com/synthetic.bin"
            else:
                link = "asset.bin" if context == "linked-css" else "media/asset.bin"
                if kind == "portable-present":
                    assets["media/asset.bin"] = b"SYNTHETIC_SOURCE15_ASSET"
            if context == "image":
                markup = '<img src="' + link + '">'
            elif context == "anchor":
                markup = '<a href="' + link + '">Synthetic attachment</a>'
            elif context == "inline-css":
                markup = '<style>p{background:url("' + link + '");}</style>'
            else:
                markup = '<link rel="stylesheet" href="media/theme.css">'
                assets["media/theme.css"] = ('p{background:url("' + link + '");}').encode("utf-8")
            files = {"synthetic [" + first + "].html": html_archive(markup, count="0").encode("utf-8"),
                     **assets}
            cases.append({"name": context + "-" + kind, "allowed": allowed,
                          "repair": context + "-portable-present",
                          "files": {path: content.hex() for path, content in sorted(files.items())},
                          "owners": {path: [first] for path in assets}})
    return cases


def source16_link_cases():
    """Generate URI controls for archives opened directly from local storage."""
    return [
        {"name": "network-localhost", "link": "//localhost/synthetic.bin", "result": "absolute"},
        {"name": "network-server", "link": "//server/synthetic.bin", "result": "absolute"},
        {"name": "network-host-only", "link": "//example.com", "result": "absolute"},
        {"name": "network-query", "link": "//example.com/synthetic.bin?rev=1#part", "result": "absolute"},
        {"name": "explicit-http", "link": "http://example.com/synthetic.bin", "result": "external"},
        {"name": "explicit-https", "link": "https://example.com/synthetic.bin", "result": "external"},
        {"name": "explicit-http-host", "link": "https://example.com", "result": "external"},
        {"name": "present-relative", "link": "media/asset.bin", "result": "local"},
        {"name": "present-relative-query", "link": "media/asset.bin?rev=1#part", "result": "local"},
        {"name": "missing-relative", "link": "media/missing.bin", "result": "missing"},
    ]


def source16_archive_cases():
    """Generate base-URL scope controls with opposite portable-link outcomes."""
    cases = []
    filename = "synthetic [" + IDS["channel"] + "].html"
    image = '<img src="media/asset.bin">'
    image_assets = {"media/asset.bin": b"SYNTHETIC_SOURCE16_ASSET"}
    relative_assets = {**image_assets, "media/base.bin": b"SYNTHETIC_SOURCE16_BASE"}

    def emit(name, markup="", *, head="", assets=None, allowed=True, issue=None):
        content = html_archive(markup, count="0").replace("</head>", head + "</head>", 1)
        files = {filename: content.encode("utf-8"), **(assets or {})}
        cases.append({"name": name, "allowed": allowed, "issue": issue,
                      "repair": "portable-image",
                      "files": {path: data.hex() for path, data in sorted(files.items())},
                      "owners": {path: [IDS["channel"]] for path in (assets or {})}})

    emit("canonical")
    emit("portable-image", image, assets=image_assets)
    emit("explicit-http-image", '<img src="http://example.com/synthetic.bin">')
    emit("explicit-https-image", '<img src="https://example.com/synthetic.bin">')
    emit("network-localhost-image", '<img src="//localhost/synthetic.bin">',
         allowed=False, issue="absolute local link")
    emit("network-server-anchor", '<a href="//server/synthetic.bin">Synthetic</a>',
         allowed=False, issue="absolute local link")
    emit("active-relative-head", image, head='<base href="media/base.bin">',
         assets=relative_assets, allowed=False, issue="unsupported base href")
    emit("active-relative-body", '<base href="media/base.bin">' + image,
         assets=relative_assets, allowed=False, issue="unsupported base href")
    for name, head in [
        ("active-empty-base", '<base href="">'),
        ("active-valueless-base", '<base href>'),
        ("active-file-base", '<base href="file:///synthetic/">'),
        ("active-network-base", '<base href="//example.com/synthetic/">'),
        ("active-http-base", '<base href="http://example.com/">'),
        ("active-https-base", '<base href="https://example.com/">'),
        ("active-mixed-case-base", '<BaSe HrEf="https://example.com/">'),
        ("first-empty-then-relative", '<base href=""><base href="media/base.bin">'),
        ("first-relative-then-https", '<base href="media/base.bin"><base href="https://example.com/">'),
        ("first-target-then-href", '<base target="_blank"><base href="https://example.com/">'),
        ("inert-then-active", '<template><base href="media/missing.bin"></template><base href="https://example.com/">'),
    ]:
        emit(name, image, head=head, assets=image_assets,
             allowed=False, issue="unsupported base href")
    emit("target-only-base", image, head='<base target="_blank">', assets=image_assets)
    emit("no-href-base", image, head='<base>', assets=image_assets)
    emit("inert-template-base", '<template><base href="media/missing.bin"></template>' + image,
         assets=image_assets)
    emit("escaped-base-text", '&lt;base href="media/missing.bin"&gt;' + image, assets=image_assets)
    emit("script-base-text", '<script>const synthetic = \'<base href="media/missing.bin">\';</script>' + image,
         assets=image_assets)
    emit("svg-base", '<svg><base href="media/missing.bin"/></svg>' + image, assets=image_assets)
    emit("svg-html-base", '<svg><foreignObject><base href="https://example.com/"></foreignObject></svg>',
         allowed=False, issue="unsupported base href")
    return cases


def source16_replay_seed(case):
    """Keep each generated asset while removing the unsupported URL semantics."""
    files = dict(case["files"])
    filename = "synthetic [" + IDS["channel"] + "].html"
    markup = "".join('<a href="' + path + '">Synthetic asset</a>'
                     for path in sorted(files) if path != filename)
    files[filename] = html_archive(markup, count="0").encode("utf-8").hex()
    return dict(case, name=case["name"] + "-seed", allowed=True, issue=None, files=files)


def source16_legacy_complete(run, case):
    """Generate internally consistent old receipts for the invalid current HTML."""
    import hashlib
    run = Path(run)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    attempt = run / "attempts" / ("%04d" % manifest["attempt"])
    source14_archive(attempt / "raw/html", case, ("html",))
    source14_archive(attempt / "organized/archive/html", case, ("html",))
    for item in manifest["artifacts"]:
        content = (run / item["path"]).read_bytes()
        item.update(size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    manifest["files"] = []
    for path in sorted(run.rglob("*")):
        if path.is_file() and path != manifest_path:
            content = path.read_bytes()
            manifest["files"].append({"path": path.relative_to(run).as_posix(),
                                      "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def native_storage_test_source():
    """Return the complete synthetic native storage regression module."""
    return '"""Generated native Git storage controls; recreate with tools/make_fixtures.py."""\nfrom datetime import datetime, timezone, timedelta\nimport hashlib\nimport importlib.util\nimport json\nimport os\nfrom pathlib import Path\nimport subprocess\n\nimport pytest\n\nROOT = Path(__file__).resolve().parents[2]\nSCRIPTS = ROOT / "skills/discord-history-export/scripts"\nSLUG = "acmeorg/synthetic-discord-config"\n\n\nclass NativeCompanion:\n    def __init__(self, root, monkeypatch):\n        self.root, self.monkeypatch = root, monkeypatch\n        self.home = root / "home"\n        self.home.mkdir()\n        self.repository = root / "companion"\n        self.environment = {key: value for key, value in os.environ.items()\n                            if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}}\n        self.environment.update(HOME=str(self.home), USERPROFILE=str(self.home),\n                                GIT_AUTHOR_NAME="Synthetic User", GIT_AUTHOR_EMAIL="user1@example.com",\n                                GIT_COMMITTER_NAME="Synthetic User", GIT_COMMITTER_EMAIL="user1@example.com")\n        self.native_run = subprocess.run\n        self.git("init", "--template=", str(self.repository), cwd=root)\n        self.git("config", "remote.origin.url", "https://github.com/" + SLUG + ".git")\n        tree = self.git("hash-object", "-t", "tree", "-w", "--stdin", input="").stdout.strip()\n        commit = self.git("commit-tree", tree, "-m", "Synthetic empty companion").stdout.strip()\n        self.git("update-ref", "HEAD", commit)\n        for key in list(os.environ):\n            monkeypatch.delenv(key)\n        for key, value in self.environment.items():\n            if not key.startswith("GIT_"):\n                monkeypatch.setenv(key, value)\n        self.receipt = self.home / ".pii-guard/visibility.json"\n        self.receipt.parent.mkdir()\n        self.visibility()\n        self.calls = []\n        monkeypatch.setattr(subprocess, "run", self.run)\n        spec = importlib.util.spec_from_file_location("native_discord_core", SCRIPTS / "export_core.py")\n        self.core = importlib.util.module_from_spec(spec)\n        spec.loader.exec_module(self.core)\n\n    def git(self, *arguments, cwd=None, input=None):\n        result = self.native_run(["git", *arguments], cwd=cwd or self.repository, env=self.environment,\n                                 input=input, capture_output=True, text=True, encoding="utf-8")\n        assert result.returncode == 0, (arguments, result.returncode, result.stderr)\n        return result\n\n    def visibility(self, state="PRIVATE", age=0):\n        stamp = datetime.now(timezone.utc) - timedelta(days=age)\n        self.receipt.write_text(json.dumps({"_refreshed": stamp.isoformat(), SLUG: state, "acmeorg/synthetic-public": "PUBLIC"}), encoding="utf-8")\n\n    def run(self, arguments, **kwargs):\n        self.calls.append((list(map(str, arguments)), dict(kwargs)))\n        if arguments[0] == "git":\n            return self.native_run(arguments, **kwargs)\n        if arguments[0] == "gh":\n            # The old consumer queried gh; this synthetic response exposes that dependency.\n            return subprocess.CompletedProcess(arguments, 0, json.dumps({\n                "visibility": "PRIVATE", "nameWithOwner": SLUG}), "")\n        raise AssertionError("Only local Git reads are permitted during storage proof")\n\n    def files(self):\n        return {str(path.relative_to(self.repository)): hashlib.sha256(path.read_bytes()).hexdigest()\n                for path in self.repository.rglob("*") if path.is_file()}\n\n\n@pytest.fixture\ndef native(tmp_path, monkeypatch):\n    return NativeCompanion(tmp_path, monkeypatch)\n\n\n@pytest.mark.parametrize("relative", [".", "data/future", "data/exact.json"])\ndef test_native_private_receipt_needs_no_network_or_writes(native, relative):\n    target = native.repository / relative\n    before = native.files()\n    assert native.core.private_destination(target) == (target.resolve(), SLUG)\n    assert native.files() == before\n    assert native.calls and all(args[0] == "git" for args, _ in native.calls)\n    queries = [args[1:] for args, _ in native.calls if "check-ignore" in args]\n    assert ["check-ignore", "--no-index", "-q", "--", relative] in queries\n\n\ndef test_native_unborn_private_repository_is_rejected(native):\n    native.git("update-ref", "-d", "HEAD")\n    with pytest.raises(native.core.ExportError):\n        native.core.private_destination(native.repository / "data/new.json")\n\n\n@pytest.mark.parametrize("relative,pattern", [\n    ("data/secret.json", "data/secret.json\\n"),\n    ("data/missing/file.json", "data/missing/\\n"),\n    ("data/tracked.json", "data/tracked.json\\n"),\n])\ndef test_native_exact_ignored_destination_is_rejected(native, relative, pattern):\n    if "tracked" in relative:\n        target = native.repository / relative\n        target.parent.mkdir()\n        target.write_text("synthetic record\\n", encoding="utf-8")\n        blob = native.git("hash-object", "-w", str(target)).stdout.strip()\n        native.git("update-index", "--add", "--cacheinfo", "100644," + blob + "," + relative)\n    (native.repository / ".gitignore").write_text(pattern, encoding="utf-8")\n    before = native.files()\n    with pytest.raises(native.core.ExportError):\n        native.core.private_destination(native.repository / relative)\n    assert native.files() == before\n\n\n@pytest.mark.parametrize("state,age", [("PUBLIC", 0), ("UNKNOWN", 0), ("PRIVATE", 90)])\ndef test_native_invalid_local_receipt_is_rejected_without_gh(native, state, age):\n    native.visibility(state, age)\n    with pytest.raises(native.core.ExportError):\n        native.core.private_destination(native.repository / "data/new.json")\n    assert all(args[0] == "git" for args, _ in native.calls)\n\n\ndef test_native_linked_private_worktree_is_supported(native):\n    linked = native.root / "linked"\n    native.git("worktree", "add", "--detach", str(linked))\n    assert (linked / ".git").is_file()\n    target = linked / "data/future.json"\n    assert native.core.private_destination(target) == (target.resolve(), SLUG)\n    assert not target.parent.exists()\n\n\ndef test_native_hardlinked_existing_output_is_rejected(native):\n    original, alias = native.repository / "original", native.repository / "alias"\n    original.write_text("synthetic content", encoding="utf-8")\n    os.link(original, alias)\n    with pytest.raises(native.core.ExportError):\n        native.core.private_destination(alias)\n    assert not native.calls\n\n\ndef test_native_public_nested_companion_is_rejected(native):\n    nested = native.repository / "data/nested"\n    nested.mkdir(parents=True)\n    native.git("init", "--template=", str(nested))\n    native.git("config", "remote.origin.url", "https://github.com/acmeorg/synthetic-public.git", cwd=nested)\n    with pytest.raises(native.core.ExportError):\n        native.core.private_topology(native.repository / "data")\n\n\ndef test_native_private_source_repository_name_is_rejected(native):\n    slug = "acmeorg/discord-history-export"\n    native.git("config", "remote.origin.url", "https://github.com/" + slug + ".git")\n    native.receipt.write_text(json.dumps({"_refreshed": datetime.now(timezone.utc).isoformat(), slug: "PRIVATE"}))\n    with pytest.raises(native.core.ExportError):\n        native.core.private_destination(native.repository / "data")\n\n\ndef test_native_existing_ignored_artifact_is_rechecked(native):\n    data = native.repository / "data"\n    data.mkdir()\n    (data / "existing.json").write_text("synthetic archive\\n", encoding="utf-8")\n    (native.repository / ".gitignore").write_text("data/existing.json\\n", encoding="utf-8")\n    before = native.files()\n    with pytest.raises(native.core.ExportError):\n        native.core.private_topology(data)\n    assert native.files() == before\n\n\ndef native_export(native, mutate_after_probe=False, observations=None):\n    """Load the complete runner with a generated exporter and real local Git proof."""\n    import sys\n    spec = importlib.util.spec_from_file_location("native_storage_fixtures", ROOT / "tools/make_fixtures.py")\n    generated = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(generated)\n    exporter = native.root / "synthetic-exporter"\n    exporter.write_text("synthetic intercepted executable", encoding="utf-8")\n    credential = native.root / "synthetic-credential"\n    credential.write_text(generated.SECRET, encoding="utf-8")\n    reads = []\n    original_read = Path.read_text\n\n    def read(path, *args, **kwargs):\n        if path == credential:\n            reads.append(path)\n        return original_read(path, *args, **kwargs)\n\n    native.monkeypatch.setattr(Path, "read_text", read)\n    native.monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", str(native.repository / "data"))\n\n    def run(arguments, **kwargs):\n        args = list(map(str, arguments))\n        if args[0] != str(exporter):\n            return native.run(arguments, **kwargs)\n        if observations is not None:\n            observations.setdefault("exporter_calls", []).append(args[1:])\n        if "--version" in args:\n            output = "2.47"\n        elif "--help" in args:\n            output = "Synthetic export command"\n            if mutate_after_probe:\n                native.git("config", "remote.origin.url", "https://github.com/acmeorg/synthetic-public.git")\n        else:\n            fmt = "json" if args[args.index("-f") + 1] == "Json" else "html"\n            target = Path(args[args.index("-o") + 1].partition("%t")[0])\n            generated.populate(target, formats=(fmt,), channels=("channel",))\n            output = ""\n        return subprocess.CompletedProcess(arguments, 0, output, "")\n\n    native.monkeypatch.setattr(subprocess, "run", run)\n    native.monkeypatch.setitem(sys.modules, "export_core", native.core)\n    spec = importlib.util.spec_from_file_location("native_storage_history", SCRIPTS / "export_history.py")\n    history = importlib.util.module_from_spec(spec)\n    previous = list(sys.path)\n    try:\n        spec.loader.exec_module(history)\n    finally:\n        sys.path[:] = previous\n    arguments = ["execute", "--exporter", str(exporter), "--credential-ref", "file:" + str(credential),\n                 "--run-id", "synthetic-run", "--channel-id", generated.IDS["channel"]]\n    return history, arguments, reads\n\n\ndef test_native_ignored_dynamic_raw_files_cannot_report_complete(native):\n    (native.repository / ".gitignore").write_text("**/raw/**/*.html\\n", encoding="utf-8")\n    history, arguments, reads = native_export(native)\n    assert history.main(arguments) == 1\n    run = native.repository / "data/runs/synthetic-run"\n    result = json.loads((run / "manifest.json").read_text(encoding="utf-8"))\n    assert result["status"] == "partial"\n    assert any((run / "attempts/0001/raw").rglob("*.html"))\n    assert not (run / "attempts/0001/organized").exists()\n\n\ndef test_native_route_change_during_exporter_probe_precedes_credentials(native):\n    history, arguments, reads = native_export(native, mutate_after_probe=True)\n    assert history.main(arguments) == 1\n    assert reads == []\n    assert not (native.repository / "data").exists()\n\n\ndef test_native_absent_data_directory_ignore_is_rejected_without_creation(native):\n    target = native.repository / "data/not-created"\n    (native.repository / ".gitignore").write_text("data/not-created/\\n", encoding="utf-8")\n    native.monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", str(target))\n    before = native.files()\n    with pytest.raises(native.core.ExportError):\n        native.core.resolve_data_dir()\n    assert native.files() == before\n    assert not target.exists()\n\n\n@pytest.mark.parametrize("relative", [".", "data/not-created"])\ndef test_native_future_directory_and_repository_root_remain_supported(native, relative):\n    target = native.repository / relative\n    native.monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", str(target))\n    before = native.files()\n    assert native.core.resolve_data_dir() == (target.resolve(), SLUG)\n    assert native.files() == before\n\n\ndef test_native_directory_only_ignore_does_not_reject_an_exact_file(native):\n    target = native.repository / "data/exact.json"\n    (native.repository / ".gitignore").write_text("data/exact.json/\\n", encoding="utf-8")\n    before = native.files()\n    assert native.core.private_destination(target) == (target.resolve(), SLUG)\n    assert native.files() == before\n    assert not target.exists()\n\n\ndef test_native_ignored_empty_directory_in_existing_tree_is_rejected(native):\n    target = native.repository / "data"\n    (target / "empty").mkdir(parents=True)\n    (native.repository / ".gitignore").write_text("data/empty/\\n", encoding="utf-8")\n    before = native.files()\n    with pytest.raises(native.core.ExportError):\n        native.core.private_topology(target)\n    assert native.files() == before\n\n\n@pytest.mark.parametrize("relative", ["raw/html", "raw/json", "organized/archive"])\ndef test_native_known_output_directory_ignore_precedes_probes_credentials_and_writes(native, relative):\n    (native.repository / ".gitignore").write_text("**/" + relative + "/\\n", encoding="utf-8")\n    observations = {}\n    history, arguments, reads = native_export(native, observations=observations)\n    before = native.files()\n    assert history.main(arguments) == 1\n    assert reads == []\n    assert observations.get("exporter_calls", []) == []\n    assert native.files() == before\n    assert not (native.repository / "data").exists()\n\n\ndef test_native_exact_file_directory_pattern_allows_complete_export(native):\n    (native.repository / ".gitignore").write_text("**/channels.txt/\\n", encoding="utf-8")\n    history, arguments, reads = native_export(native)\n    assert history.main(arguments) == 0\n    assert len(reads) == 1\n    run = native.repository / "data/runs/synthetic-run"\n    result = json.loads((run / "manifest.json").read_text(encoding="utf-8"))\n    assert result["status"] == "complete"\n    assert any((run / "attempts/0001/raw/html").rglob("*.html"))\n    assert any((run / "attempts/0001/raw/json").rglob("*.json"))\n'


def bind_public_boundary(core, root, runner, states, environment=None):
    """Bind the real public proof to generated receipts and intercepted local Git."""
    from datetime import datetime, timezone
    from types import SimpleNamespace
    original_load = getattr(core, "fixture_boundary_loader", core.load_boundary)
    core.fixture_boundary_loader = original_load
    observations = []

    class Proxy:
        def __init__(self, original, **overrides):
            self.original, self.overrides = original, overrides

        def __getattr__(self, name):
            return self.overrides[name] if name in self.overrides else getattr(self.original, name)

    def load():
        boundary = original_load()
        if environment is not None:
            boundary.os = Proxy(boundary.os, environ=environment)

        def run(arguments, **kwargs):
            if arguments[0] != "git":
                raise AssertionError("The private proof may only invoke local Git")
            arguments = ["git", "-C", str(kwargs["cwd"]), *arguments[1:]]
            return runner(arguments, **kwargs)

        boundary.subprocess = Proxy(boundary.subprocess, run=run)
        prove = boundary.prove_private_companion

        def public_proof(destination, visibility_map=None):
            receipt = Path(root) / "synthetic-visibility.json"
            receipt.write_text(json.dumps({"_refreshed": datetime.now(timezone.utc).isoformat(), **states()}),
                               encoding="utf-8")
            proof = prove(destination, visibility_map=receipt)
            observations.append(SimpleNamespace(destination=Path(destination), proof=proof))
            return proof

        boundary.prove_private_companion = public_proof
        return boundary

    core.load_boundary = load
    return observations


def bind_synthetic_ssh_profile(monkeypatch, configuration):
    """Use standard-library OS seams to isolate the shared parser's file sources."""
    import ctypes
    import os
    configuration = Path(configuration)
    home = configuration.parent.parent
    for key in ("HOME", "USERPROFILE", "ProgramData"):
        monkeypatch.setenv(key, str(home))
    if os.name == "nt":
        def profile(window, folder, token, flags, buffer):
            buffer.value = str(home)
            return 0
        monkeypatch.setattr(ctypes.windll.shell32, "SHGetFolderPathW", profile)
    else:
        import pwd
        from types import SimpleNamespace
        monkeypatch.setattr(pwd, "getpwuid", lambda uid: SimpleNamespace(pw_dir=str(home)))
    original_read = Path.read_bytes
    observations = {"reads": []}

    def read(path):
        if path == configuration:
            content = original_read(path)
            observations["reads"].append(content)
            return content
        if path.name in {"config", "ssh_config"} and (
                path.parent.name == ".ssh" or path.parent.name == "ssh"):
            return b""
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "tests" / "fixtures")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in generated().items():
        (args.out / name).write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
