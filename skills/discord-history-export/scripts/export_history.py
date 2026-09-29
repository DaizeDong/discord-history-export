"""Plan or execute an authorized Discord bot export without exposing credentials."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_core import (ExportError, NUMERIC_ID, contains, digest, files_under,
                         inspect_archive, json_bytes, organize, resolve_data_dir, summarize, validate_channel_sets)

# Official release source binds the token option to this environment variable.
# See reference/credential-transport.md for immutable upstream evidence.
SUPPORTED_ENV_RELEASES = {"2.47"}


def credential_reference(reference):
    kind, separator, value = reference.partition(":")
    if separator and kind == "env" and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        return kind, value
    if separator and kind == "file" and value and Path(value).is_absolute():
        return kind, value
    raise ExportError("Credential reference must be env:VARIABLE_NAME or file:ABSOLUTE_PATH; never supply the value.")


def credential_value(reference):
    kind, name = credential_reference(reference)
    try:
        value = os.environ.get(name, "") if kind == "env" else Path(name).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise ExportError("Credential file is unavailable. Check the local reference and file permissions.") from None
    value = value.strip()
    if not value or any(character.isspace() for character in value) or "\x00" in value:
        raise ExportError("Credential is empty or malformed. Initialize the local reference, then retry.")
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "execute"))
    parser.add_argument("--exporter", required=True)
    parser.add_argument("--credential-ref", required=True)
    parser.add_argument("--run-id", required=True)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--guild-id")
    scope.add_argument("--channel-id")
    parser.add_argument("--after")
    parser.add_argument("--before")
    parser.add_argument("--media", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", args.run_id) or args.run_id.endswith("."):
        raise ExportError("Run ID must be one safe filename component without traversal or a trailing dot.")
    if args.run_id.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        raise ExportError("Run ID cannot be a reserved device filename.")
    if not NUMERIC_ID.fullmatch(args.guild_id or args.channel_id):
        raise ExportError("Guild or channel ID must be numeric.")
    dates = []
    for value in (args.after, args.before):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
        except ValueError:
            raise ExportError("Date limits must be valid ISO dates or timestamps.") from None
        dates.append(parsed)
    if all(dates):
        try:
            invalid = dates[0] >= dates[1]
        except TypeError:
            raise ExportError("Use matching timezone notation for both date limits.") from None
        if invalid:
            raise ExportError("--after must precede --before.")
    credential_reference(args.credential_ref)
    return args


def configuration(args):
    return {"run_id": args.run_id, "exporter": args.exporter,
            "credential_ref": args.credential_ref, "guild_id": args.guild_id,
            "channel_id": args.channel_id, "after": args.after, "before": args.before, "media": args.media}


def export_command(config, raw, fmt):
    guild = config["guild_id"]
    command = [config["exporter"], "exportguild" if guild else "export",
               "-g" if guild else "-c", guild or config["channel_id"],
               "-f", "HtmlDark" if fmt == "html" else "Json",
               "-o", str(raw / fmt / "%t" / f"%C [%c].{fmt}"), "--parallel", "4"]
    if guild:
        command.extend(["--include-threads", "All"])
    for option in ("after", "before"):
        if config[option]:
            command.extend(["--" + option, config[option]])
    if config["media"]:
        command.append("--media")
    return command


def exporter_call(command, environment):
    try:
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=environment, timeout=3600)
    except (OSError, subprocess.SubprocessError):
        raise ExportError("Exporter could not finish. Check its executable, access, and timeout; resume the same run after fixing it.") from None


def probe(config):
    # Do not transmit a pre-existing token to version/help probes.
    kind, name = credential_reference(config["credential_ref"])
    excluded = {"DISCORD_TOKEN"}
    if kind == "env":
        excluded.add(name)
    normalize = str.casefold if os.name == "nt" else str
    excluded = {normalize(key) for key in excluded}
    environment = {key: value for key, value in os.environ.items() if normalize(key) not in excluded}
    version = exporter_call([config["exporter"], "--version"], environment)
    selected = "exportguild" if config["guild_id"] else "export"
    help_result = exporter_call([config["exporter"], selected, "--help"], environment)
    if version.returncode or help_result.returncode:
        raise ExportError("Exporter version/help probe failed. Install a supported DiscordChatExporter CLI release.")
    match = re.search(r"(?<![0-9A-Za-z.])v?(\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?)(?![0-9A-Za-z.+-])", version.stdout)
    release = match.group(1) if match else None
    explicit_env_support = "DISCORD_TOKEN" in help_result.stdout
    if release not in SUPPORTED_ENV_RELEASES and not explicit_env_support:
        raise ExportError("Exporter credential transport is unproven. Use the documented supported release or help that declares DISCORD_TOKEN.")
    return {"release": release, "credential_transport": "DISCORD_TOKEN",
            "evidence": "official-tagged-source" if release in SUPPORTED_ENV_RELEASES else "export-command-help"}


def file_receipts(run):
    return [{"path": path.relative_to(run).as_posix(), "size_bytes": path.stat().st_size,
             "sha256": digest(path.read_bytes())}
            for path in files_under(run) if path != run / "manifest.json"]


def verify_existing(run, config, resume):
    if not run.exists():
        return None
    try:
        stored = json.loads((run / "run.json").read_text(encoding="utf-8"))
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ExportError("Existing run lacks valid immutable configuration/receipts. Choose a new run ID.") from None
    if stored != config:
        raise ExportError("Run ID is already bound to a different scope, dates, media option, exporter, or credential reference.")
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or manifest.get("run_id") != config["run_id"]
            or manifest.get("status") not in ("complete", "partial", "failed")
            or type(manifest.get("attempt")) is not int or manifest["attempt"] < 1
            or not isinstance(manifest.get("files"), list)):
        raise ExportError("Existing run metadata is malformed. Preserve it and choose a new run ID.")
    current = {item["path"]: item for item in file_receipts(run)}
    recorded = {}
    for item in manifest["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or item["path"] in recorded:
            raise ExportError("Existing run file receipts are malformed.")
        recorded[item["path"]] = item
    if any(current.get(path) != item for path, item in recorded.items()):
        raise ExportError("Existing run files changed. Preserve the run and choose a new run ID.")
    extras = set(current) - set(recorded)
    if extras:
        # An interrupted exporter can create new files after the last receipt. They are preserved
        # as incomplete evidence only within its reserved attempt, never used to declare success.
        active = f"attempts/{manifest['attempt']:04d}/"
        allowed = manifest.get("in_progress") is True and manifest["status"] == "partial"
        if not allowed or any(path != active + "channels.txt" and not path.startswith(active + "raw/") for path in extras):
            raise ExportError("Unrelated files appeared in the run. Preserve it and choose a new run ID.")
    if manifest.get("status") == "complete":
        validate_receipt_artifacts(run, manifest, config)
        return manifest
    if not resume:
        raise ExportError("This run is incomplete. Use --resume with the same configuration, or choose a new run ID.")
    return manifest


def validate_receipt_artifacts(run, manifest, config):
    entries = manifest.get("artifacts")
    if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
        raise ExportError("Completed run has malformed artifact receipts.")
    try:
        attempt = run / "attempts" / f"{manifest['attempt']:04d}"
        raw, organized = attempt / "raw", attempt / "organized"
        expected = {}
        for entry in inspect_archive(raw):
            entry["path"] = (organized.relative_to(run) / entry["path"]).as_posix()
            entry["source"] = (raw.relative_to(run) / entry["source"]).as_posix()
            expected[entry["path"]] = entry
        recorded = {entry["path"]: entry for entry in entries}
        if len(recorded) != len(entries) or recorded != expected:
            raise ExportError("Completed receipts must cover every archive artifact exactly once and match its source.")
        # Re-inspect physical organized files so a self-consistent receipt cannot omit artifacts.
        physical = {}
        for entry in inspect_archive(organized / "archive"):
            path = (organized.relative_to(run) / entry["path"]).as_posix()
            physical[path] = {key: value for key, value in entry.items() if key not in ("path", "source")}
        metadata = {path: {key: value for key, value in entry.items() if key not in ("path", "source")}
                    for path, entry in expected.items()}
        if physical != metadata:
            raise ExportError("Completed organized archive differs from its source artifacts.")
        validate_formats(entries, config)
        if manifest.get("summary") != summarize(entries):
            raise ExportError("Completed run summary differs from its artifact receipts.")
    except (KeyError, TypeError, ValueError):
        raise ExportError("Completed run has malformed artifact receipts.") from None


def save_manifest(run, manifest):
    manifest["files"] = file_receipts(run)
    temporary = run / "manifest.json.tmp"
    with temporary.open("xb") as stream:
        stream.write(json_bytes(manifest))
    temporary.replace(run / "manifest.json")


def validate_formats(entries, config):
    json_ids = validate_channel_sets(entries, require_both=True)
    if config["channel_id"] and json_ids != {config["channel_id"]}:
        raise ExportError("Exporter produced a different channel than requested.")
    if config["guild_id"] and any(a.get("guild_id", config["guild_id"]) != config["guild_id"] for a in entries):
        raise ExportError("Exporter JSON guild identity differs from the requested scope.")


def partial_entries(raw, run):
    entries = []
    for fmt in ("html", "json"):
        folder = raw / fmt
        if not folder.exists():
            continue
        try:
            verified = inspect_archive(folder, allow_empty=True)
        except (ExportError, OSError, UnicodeError):
            continue  # Invalid files remain in the file receipts and keep the run incomplete.
        for entry in verified:
            entry = dict(entry)
            entry["source"] = entry["path"] = (folder.relative_to(run) / entry["source"]).as_posix()
            entries.append(entry)
    return entries


def execute(args):
    config = configuration(args)
    data, companion = resolve_data_dir()
    run = (data / "runs" / args.run_id).resolve()
    if not contains(data, run):
        raise ExportError("Run directory escapes the private DATA root.")
    previous = verify_existing(run, config, args.resume)
    if args.action == "plan":
        return {"schema_version": 1, "status": "planned", "configuration": config,
                "companion": companion, "run_directory": str(run),
                "commands": [export_command(config, run / "attempts" / "0001" / "raw", fmt) for fmt in ("html", "json")]}
    if previous and previous["status"] == "complete":
        return previous
    provenance = probe(config)
    secret = credential_value(config["credential_ref"])
    environment = dict(os.environ)
    environment["DISCORD_TOKEN"] = secret
    attempt_number = previous.get("attempt", 0) + 1 if previous else 1
    attempt = run / "attempts" / f"{attempt_number:04d}"
    if attempt.exists():
        raise ExportError("Next attempt directory already exists. Preserve the run and choose a new run ID.")
    run.mkdir(parents=True, exist_ok=True)
    if previous is None:
        with (run / "run.json").open("xb") as stream:
            stream.write(json_bytes(config))
    manifest = {"schema_version": 1, "run_id": args.run_id, "status": "partial", "attempt": attempt_number, "in_progress": True,
                "companion": companion, "exporter": provenance, "artifacts": [], "summary": summarize([]),
                "issues": ["Export attempt has not completed. Resume with the same configuration."]}
    save_manifest(run, manifest)
    raw = attempt / "raw"
    attempt.mkdir(parents=True)
    channels = attempt / "channels.txt"
    try:
        channel_text = ""
        if config["guild_id"]:
            result = exporter_call([config["exporter"], "channels", "-g", config["guild_id"]], environment)
            if result.returncode:
                raise ExportError("Exporter could not list guild channels. Check bot permissions and resume.")
            rows = []
            for line in result.stdout.replace(secret, "[REDACTED]").splitlines():
                channel_id, separator, display = line.partition("|")
                if separator and NUMERIC_ID.fullmatch(channel_id.strip()):
                    rows.append(channel_id.strip() + " | " + display.strip())
            channel_text = "\n".join(rows) + "\n"
        channels.write_text(channel_text, encoding="utf-8")
        for fmt in ("html", "json"):
            (raw / fmt).mkdir(parents=True)
            result = exporter_call(export_command(config, raw, fmt), environment)
            if result.returncode:
                raise ExportError(f"Exporter failed during {fmt.upper()} export (exit {result.returncode}). Check bot permissions, connectivity, and date scope; then resume.")
        entries = inspect_archive(raw)
        validate_formats(entries, config)
        organized = attempt / "organized"
        organized_manifest = organize(raw, organized, channels)
        rebased = []
        for entry in organized_manifest["artifacts"]:
            entry = dict(entry)
            entry["path"] = (organized.relative_to(run) / entry["path"]).as_posix()
            entry["source"] = (raw.relative_to(run) / entry["source"]).as_posix()
            rebased.append(entry)
        manifest.update(status="complete", artifacts=rebased, summary=summarize(rebased), issues=[])
    except (ExportError, OSError, UnicodeError) as error:
        available = partial_entries(raw, run) if raw.exists() else []
        status = "partial" if raw.exists() and any(path.is_file() for path in raw.rglob("*")) else "failed"
        issue = str(error) if isinstance(error, ExportError) else "Archive I/O failed. Check available disk space and file permissions; then resume."
        manifest.update(status=status, artifacts=available, summary=summarize(available), issues=[issue.replace(secret, "[REDACTED]")])
    finally:
        # Captured child output is never printed or persisted, including failure output.
        environment.pop("DISCORD_TOKEN", None)
        secret = None
    manifest["in_progress"] = False
    save_manifest(run, manifest)
    return manifest


def main(argv=None):
    try:
        result = execute(parse_args(argv))
        print(json.dumps(result if result["status"] == "planned" else {
            key: result[key] for key in ("status", "run_id", "summary", "issues", "companion")}, ensure_ascii=False))
        return 0 if result["status"] in ("complete", "planned") else 1
    except ExportError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError):
        print("Local preflight or archive I/O failed. Check configuration, paths, and permissions.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
