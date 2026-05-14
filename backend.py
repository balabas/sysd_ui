from __future__ import annotations

import os
from shutil import which
import subprocess
from dataclasses import replace
from pathlib import Path

from services import ServiceUnit, sample_services
from properties import COMMON_FIELDS, section_for_key
from suggestions import SUFFIX_TO_SECTION

_SECTION_ORDER = ["Unit", "Service", "Socket", "Mount", "Automount", "Swap", "Path", "Timer", "Slice", "Install"]


SERVICE_COLUMNS = [
    "Id",
    "Description",
    "LoadState",
    "ActiveState",
    "SubState",
    "FragmentPath",
    "DropInPaths",
    "UnitFileState",
    "MainPID",
    "MemoryCurrent",
    "CPUUsageNSec",
    "NRestarts",
    "ActiveEnterTimestamp",
    "UnitFilePreset",
    "ControlGroup",
]


class BackendError(RuntimeError):
    pass


class SystemdBackend:
    def __init__(self) -> None:
        self._fallback = sample_services()
        self._pkexec_env = self._build_pkexec_env()

    def list_services(self) -> list[ServiceUnit]:
        try:
            enabled_states = self._list_unit_files()
            runtime_states = self._list_units()
            units: dict[str, ServiceUnit] = {}

            for name, enabled_state in enabled_states.items():
                base = self._blank_service(name, enabled_state)
                runtime = runtime_states.get(name)
                if runtime is not None:
                    base = self._merge_runtime(base, runtime)
                units[name] = base

            if not units:
                for service in self._fallback:
                    units[service.name] = self._decorate_service(replace(service), {})

            result = sorted(units.values(), key=lambda svc: svc.name)
            if result:
                return result
        except Exception:
            pass
        return self._fallback_copy()

    def refresh_service(self, name: str) -> ServiceUnit:
        base = next((svc for svc in self.list_services() if svc.name == name), None)
        if base is None:
            raise BackendError(f"unknown service: {name}")
        try:
            record = self._show_unit(name)
            return self._merge(base, record)
        except Exception:
            return base

    def journal(self, name: str, lines: int = 4) -> list[tuple[str, str]]:
        try:
            output = self._run(
                [
                    "journalctl",
                    "-u",
                    name,
                    "-n",
                    str(lines),
                    "--no-pager",
                    "--output=short-iso",
                ]
            )
            entries: list[tuple[str, str]] = []
            for line in output.splitlines():
                if not line.strip():
                    continue
                if " " not in line:
                    entries.append(("now", line.strip()))
                    continue
                stamp, message = line.split(" ", 1)
                entries.append((stamp, message))
            return entries or [("now", "No journal output available")]
        except Exception:
            service = next((svc for svc in self._fallback if svc.name == name), None)
            return list(service.journal) if service else [("now", "No journal output available")]

    def required_by(self, name: str) -> list[str]:
        try:
            output = self._run(
                [
                    "systemctl",
                    "show",
                    "--no-pager",
                    "--property=RequiredBy,BoundBy",
                    name,
                ]
            )
            units: list[str] = []
            for line in output.splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in {"RequiredBy", "BoundBy"}:
                    for unit in value.split():
                        unit = unit.strip()
                        if unit:
                            units.append(unit)
            return sorted(set(units))
        except Exception:
            return []

    def start(self, name: str) -> None:
        self._run_systemctl(["start", name], privileged=True)

    def stop(self, name: str) -> None:
        self._run_systemctl(["stop", name], privileged=True)

    def restart(self, name: str) -> None:
        self._run_systemctl(["restart", name], privileged=True)

    def enable(self, name: str) -> None:
        self._run_systemctl(["enable", name], privileged=True)

    def disable(self, name: str) -> None:
        self._run_systemctl(["disable", name], privileged=True)

    def mask(self, name: str) -> None:
        self._run_systemctl(["mask", name], privileged=True)

    def unmask(self, name: str) -> None:
        self._run_systemctl(["unmask", name], privileged=True)

    def daemon_reload(self) -> None:
        self._run_systemctl(["daemon-reload"], privileged=True)

    def delete_service(self, name: str) -> None:
        unit_name = self._normalize_unit_name(name)
        for args in (["stop", unit_name], ["disable", unit_name]):
            try:
                self._run_systemctl(args, privileged=True)
            except BackendError:
                pass
        self._remove_system_paths(
            [
                self._service_path(unit_name),
                self._override_path(unit_name),
            ]
        )
        self.daemon_reload()

    def read_properties(self, name: str) -> dict[str, str]:
        props = list(COMMON_FIELDS)
        try:
            output = self._run(["systemctl", "cat", name])
            data = self._parse_unit_text(output, props)
        except Exception:
            data = {prop: "" for prop in props}

        try:
            unit = self.refresh_service(name)
        except BackendError:
            unit = next((svc for svc in self.list_services() if svc.name == name), None)
            if unit is None:
                unit = next((svc for svc in self._fallback if svc.name == name), None)
        data["FragmentPath"] = unit.path if unit is not None else ""
        data["OverridePath"] = self._override_path(name)
        return data

    def read_unit_sections(self, name: str) -> dict[str, list[tuple[str, str]]]:
        try:
            output = self._run(["systemctl", "cat", name])
        except Exception:
            return {}
        return self._parse_unit_sections(output)

    def save_override(self, name: str, fields: dict[str, str], extra: list[tuple[str, str]]) -> None:
        content = self._render_override(fields, extra)
        self._write_text_system(self._override_path(name), content)
        self.daemon_reload()

    def save_unit(self, name: str, fields: dict[str, str], extra: list[tuple[str, str]]) -> None:
        unit_name = self._normalize_unit_name(name)
        content = self._render_service_unit(fields, extra)
        service_path = self._service_path(unit_name)
        self._write_text_system(service_path, content)
        if not Path(service_path).exists():
            raise BackendError(f"service file was not written: {service_path}")
        self.daemon_reload()
        try:
            self._run(["systemctl", "cat", unit_name])
        except BackendError as exc:
            raise BackendError(f"systemd could not read saved unit {unit_name}: {exc}") from exc

    def save_vendor_unit(self, name: str, path: str, fields: dict[str, str], extra: list[tuple[str, str]]) -> None:
        unit_name = self._normalize_unit_name(name)
        service_path = path.strip()
        if not service_path:
            raise BackendError(f"vendor unit path is unknown for {unit_name}")
        if service_path.startswith("/etc/systemd/system/"):
            self.save_unit(unit_name, fields, extra)
            return
        self.backup_unit_file(unit_name, service_path)
        content = self._render_service_unit(fields, extra)
        self._write_text_system(service_path, content)
        if not Path(service_path).exists():
            raise BackendError(f"vendor service file was not written: {service_path}")
        self.daemon_reload()
        try:
            self._run(["systemctl", "cat", unit_name])
        except BackendError as exc:
            raise BackendError(f"systemd could not read saved unit {unit_name}: {exc}") from exc

    def backup_unit_file(self, name: str, path: str) -> str:
        unit_name = self._normalize_unit_name(name)
        source = path.strip()
        if not source:
            raise BackendError(f"unit path is unknown for {unit_name}")
        backup = self._backup_path(unit_name)
        self._copy_system_path(source, backup)
        return backup

    def restore_unit_backup(self, name: str, path: str) -> str:
        unit_name = self._normalize_unit_name(name)
        target = path.strip()
        if not target:
            raise BackendError(f"unit path is unknown for {unit_name}")
        backup = self._backup_path(unit_name)
        if not Path(backup).exists():
            raise BackendError(f"backup does not exist: {backup}")
        self._copy_system_path(backup, target)
        self.daemon_reload()
        return backup

    def create_service(self, name: str, fields: dict[str, str], extra: list[tuple[str, str]]) -> str:
        unit_name = self._normalize_unit_name(name)
        content = self._render_service_unit(fields, extra)
        service_path = self._service_path(unit_name)
        self._write_text_system(service_path, content)
        if not Path(service_path).exists():
            raise BackendError(f"service file was not created: {service_path}")
        self.daemon_reload()
        try:
            self._run(["systemctl", "cat", unit_name])
        except BackendError as exc:
            raise BackendError(f"systemd could not read created unit {unit_name}: {exc}") from exc
        if not any(svc.name == unit_name for svc in self.list_services()):
            raise BackendError(f"created unit is not visible in systemd: {unit_name}")
        return unit_name

    def _run(self, cmd: list[str]) -> str:
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return proc.stdout
        except FileNotFoundError as exc:
            raise BackendError(f"command not found: {cmd[0]}") from exc
        except subprocess.CalledProcessError as exc:
            msg = exc.stderr.strip() or exc.stdout.strip() or f"command failed: {' '.join(cmd)}"
            raise BackendError(msg) from exc

    def _run_with_input(self, cmd: list[str], stdin_text: str) -> str:
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                text=True,
                input=stdin_text,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return proc.stdout
        except FileNotFoundError as exc:
            raise BackendError(f"command not found: {cmd[0]}") from exc
        except subprocess.CalledProcessError as exc:
            msg = exc.stderr.strip() or exc.stdout.strip() or f"command failed: {' '.join(cmd)}"
            raise BackendError(msg) from exc

    def _run_systemctl(self, args: list[str], *, privileged: bool = False) -> str:
        cmd = ["systemctl", *args]
        try:
            return self._run(cmd)
        except BackendError as exc:
            if not privileged or not self._should_escalate(str(exc)):
                raise
            if not self._pkexec_available():
                raise BackendError(
                    f"{exc} (pkexec not available; install polkit agent support or run the app with elevated permissions)"
                ) from exc
            return self._run_pkexec(cmd)

    def _run_pkexec(self, cmd: list[str]) -> str:
        pkcmd = ["pkexec", "/usr/bin/env"]
        for key, value in self._pkexec_env.items():
            pkcmd.append(f"{key}={value}")
        pkcmd.extend(cmd)
        return self._run(pkcmd)

    def _should_escalate(self, message: str) -> bool:
        lowered = message.lower()
        return any(
            token in lowered
            for token in [
                "access denied",
                "authentication is required",
                "interactive authentication required",
                "polkit",
                "not permitted",
                "permission denied",
            ]
        )

    def _pkexec_available(self) -> bool:
        return which("pkexec") is not None

    def _build_pkexec_env(self) -> dict[str, str]:
        env = {}
        for key in [
            "DISPLAY",
            "WAYLAND_DISPLAY",
            "XAUTHORITY",
            "XDG_RUNTIME_DIR",
            "DBUS_SESSION_BUS_ADDRESS",
        ]:
            value = os.environ.get(key)
            if value:
                env[key] = value
        return env

    def _write_text_system(self, path: str, content: str) -> None:
        script = (
            "import pathlib,sys\n"
            "target=pathlib.Path(sys.argv[1])\n"
            "target.parent.mkdir(parents=True, exist_ok=True)\n"
            "target.write_text(sys.stdin.read(), encoding='utf-8')\n"
        )
        self._run_with_input(["pkexec", "/usr/bin/python3", "-c", script, path], content)

    def _copy_system_path(self, source: str, target: str) -> None:
        script = (
            "import pathlib,shutil,sys\n"
            "source=pathlib.Path(sys.argv[1])\n"
            "target=pathlib.Path(sys.argv[2])\n"
            "if not source.exists():\n"
            "    raise SystemExit(f'source does not exist: {source}')\n"
            "target.parent.mkdir(parents=True, exist_ok=True)\n"
            "shutil.copy2(source, target)\n"
        )
        self._run(["pkexec", "/usr/bin/python3", "-c", script, source, target])

    def _remove_system_paths(self, paths: list[str]) -> None:
        script = (
            "import pathlib,shutil,sys\n"
            "for item in sys.argv[1:]:\n"
            "    path=pathlib.Path(item)\n"
            "    if path.is_dir():\n"
            "        shutil.rmtree(path, ignore_errors=True)\n"
            "    else:\n"
            "        try:\n"
            "            path.unlink()\n"
            "        except FileNotFoundError:\n"
            "            pass\n"
        )
        self._run(["pkexec", "/usr/bin/python3", "-c", script, *paths])

    def _override_path(self, name: str) -> str:
        return str(Path("/etc/systemd/system") / f"{name}.d" / "override.conf")

    def _service_path(self, name: str) -> str:
        return str(Path("/etc/systemd/system") / self._normalize_unit_name(name))

    def _backup_path(self, name: str) -> str:
        safe_name = self._normalize_unit_name(name).replace("/", "_")
        return str(Path("/var/lib/sysd_ui/backups") / f"{safe_name}.bak")

    def _normalize_unit_name(self, name: str) -> str:
        known_suffixes = (".service", ".socket", ".timer", ".target", ".path", ".mount", ".scope", ".slice")
        return name if name.endswith(known_suffixes) else f"{name}.service"

    @staticmethod
    def _grouped_sections() -> dict[str, list[str]]:
        return {"Unit": [], "Install": []}

    def _render_grouped(self, grouped: dict[str, list[str]]) -> str:
        in_order = set(_SECTION_ORDER)
        ordered = [s for s in _SECTION_ORDER if s in grouped]
        ordered += [s for s in grouped if s not in in_order]
        parts: list[str] = []
        for section in ordered:
            if grouped.get(section):
                parts.append(f"[{section}]")
                parts.extend(grouped[section])
                parts.append("")
        return "\n".join(parts).rstrip() + "\n"

    def _add_to_grouped(self, grouped: dict[str, list[str]], key: str, value: str, *, override_reset: bool = False) -> None:
        text = value.strip()
        section = section_for_key(key)
        grouped.setdefault(section, [])
        if key == "ExecStart" and override_reset:
            if text:
                grouped[section].append("ExecStart=")
                grouped[section].append(f"ExecStart={text}")
            return
        if key == "Environment":
            for entry in self._split_environment_values(text):
                grouped[section].append(f"Environment={entry}")
            return
        if not text:
            return
        grouped[section].append(f"{key}={text}")

    def _render_service_unit(self, fields: dict[str, str], extra: list[tuple[str, str]]) -> str:
        grouped = self._grouped_sections()

        description = fields.get("Description", "").strip()
        if description:
            grouped["Unit"].append(f"Description={description}")

        if fields.get("ExecStart", "").strip():
            grouped.setdefault("Service", [])

        for key in ["ExecStart", "ExecReload", "ExecStop", "WorkingDirectory", "User", "Group", "Environment", "Restart"]:
            self._add_to_grouped(grouped, key, fields.get(key, ""))

        for key, value in extra:
            self._add_to_grouped(grouped, key, value)

        wanted_by = fields.get("WantedBy", "").strip()
        if wanted_by:
            grouped["Install"].append(f"WantedBy={wanted_by}")

        return self._render_grouped(grouped)

    def _render_override(self, fields: dict[str, str], extra: list[tuple[str, str]]) -> str:
        grouped = self._grouped_sections()

        for key in COMMON_FIELDS:
            self._add_to_grouped(grouped, key, fields.get(key, ""), override_reset=(key == "ExecStart"))
        for key, value in extra:
            self._add_to_grouped(grouped, key, value)

        return self._render_grouped(grouped)

    def _split_environment_values(self, text: str) -> list[str]:
        values: list[str] = []
        for line in text.splitlines():
            entry = line.strip()
            if not entry:
                continue
            values.append(entry)
        return values

    def _fallback_copy(self) -> list[ServiceUnit]:
        return [self._decorate_service(replace(service), {}) for service in self._fallback]

    _UNIT_SUFFIXES = (
        ".service", ".socket", ".timer", ".target", ".path",
        ".mount", ".automount", ".swap", ".slice", ".scope", ".device",
    )

    def _strip_unit_suffix(self, name: str) -> str:
        for suffix in self._UNIT_SUFFIXES:
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return name

    def _blank_service(self, name: str, enabled_state: str) -> ServiceUnit:
        base = next((svc for svc in self._fallback if svc.name == name), None)
        if base is not None:
            return self._decorate_service(replace(base), {})
        description = self._strip_unit_suffix(name).replace("-", " ").replace("_", " ").title()
        return self._decorate_service(
            ServiceUnit(
                name=name,
                description=description,
                status="inactive",
                enabled=enabled_state in {"enabled", "enabled-runtime", "static", "indirect"},
                load_state="loaded" if enabled_state != "masked" else "masked",
                uptime="stopped",
                since="unknown",
                pid="-",
                memory="0 MB",
                cpu="0%",
                restarts=0,
                path="",
                target="multi-user.target",
                tags=[],
                deps=[],
                journal=[("now", "No journal entries loaded")],
                favorite=False,
            ),
            {},
        )

    def _list_unit_files(self) -> dict[str, str]:
        output = self._run(
            [
                "systemctl",
                "list-unit-files",
                "--all",
                "--no-legend",
                "--no-pager",
                "--plain",
            ]
        )
        states: dict[str, str] = {}
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0].strip()
            enabled_state = parts[1].strip()
            if name:
                states[name] = enabled_state
        return states

    def _list_units(self) -> dict[str, dict[str, str]]:
        output = self._run(
            [
                "systemctl",
                "list-units",
                "--all",
                "--no-legend",
                "--no-pager",
                "--plain",
            ]
        )
        states: dict[str, dict[str, str]] = {}
        for line in output.splitlines():
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            name, load_state, active_state, sub_state, description = parts
            if not name:
                continue
            states[name] = {
                "Id": name,
                "Description": description,
                "LoadState": load_state,
                "ActiveState": active_state,
                "SubState": sub_state,
            }
        return states

    def _show_unit(self, name: str) -> dict[str, str]:
        output = self._run(
            [
                "systemctl",
                "show",
                "--all",
                "--no-pager",
                "--no-ask-password",
                "--property=" + ",".join(SERVICE_COLUMNS),
                name,
            ]
        )
        return self._parse_show_output(output).get(name, {})

    def _merge(self, base: ServiceUnit, record: dict[str, str]) -> ServiceUnit:
        active_state = record.get("ActiveState", "").strip()
        sub_state = record.get("SubState", "").strip()
        load_state = record.get("LoadState", base.load_state).strip() or base.load_state
        enabled_state = record.get("UnitFileState", "")
        main_pid = record.get("MainPID", base.pid).strip() or base.pid
        path = record.get("FragmentPath", base.path).strip() or base.path
        since = record.get("ActiveEnterTimestamp", base.since).strip() or base.since
        target = self._guess_target(record.get("ControlGroup", ""), base.target)

        status = "inactive"
        if active_state == "active":
            status = "active"
        elif active_state == "failed":
            status = "failed"
        elif sub_state == "running":
            status = "active"
        elif sub_state == "dead":
            status = "inactive"

        enabled = base.enabled
        if enabled_state:
            enabled = enabled_state in {"enabled", "enabled-runtime", "static", "indirect"}

        return self._decorate_service(
            replace(
                base,
                status=status,
                enabled=enabled,
                load_state=load_state or base.load_state,
                pid=main_pid if main_pid and main_pid != "0" else "-",
                since=since,
                path=path,
                target=target,
                restarts=self._safe_int(record.get("NRestarts", str(base.restarts))),
            ),
            record,
        )

    def _merge_runtime(self, base: ServiceUnit, runtime: dict[str, str]) -> ServiceUnit:
        active_state = runtime.get("ActiveState", "").strip()
        sub_state = runtime.get("SubState", "").strip()
        status = base.status
        if active_state == "active" or sub_state == "running":
            status = "active"
        elif active_state == "failed":
            status = "failed"
        elif active_state:
            status = "inactive"
        return self._decorate_service(
            replace(
                base,
                description=runtime.get("Description", base.description).strip() or base.description,
                load_state=runtime.get("LoadState", base.load_state).strip() or base.load_state,
                status=status,
            ),
            runtime,
        )

    def _decorate_service(self, service: ServiceUnit, record: dict[str, str]) -> ServiceUnit:
        local_path = service.path or self._local_unit_path(service.name)
        if local_path and not service.path:
            service = replace(service, path=local_path)
        blob = service.search_blob
        if not blob and service.path:
            try:
                blob = Path(service.path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                blob = ""
        return replace(service, service_class=self._classify_service(service, record), search_blob=blob)

    def _local_unit_path(self, name: str) -> str:
        unit_name = self._normalize_unit_name(name)
        unit_path = Path("/etc/systemd/system") / unit_name
        if unit_path.exists():
            return str(unit_path)
        override_path = Path("/etc/systemd/system") / f"{unit_name}.d" / "override.conf"
        if override_path.exists():
            return str(unit_path)
        return ""

    def _classify_service(self, service: ServiceUnit, record: dict[str, str]) -> str:
        path = (record.get("FragmentPath") or service.path or "").strip()
        dropins = (record.get("DropInPaths") or "").strip()
        target = service.target.lower()
        name = service.name.lower()

        if path.startswith("/etc/systemd/system/") or "/etc/systemd/system/" in dropins:
            return "custom"
        if path.startswith(("/home/", "/opt/", "/srv/", "/usr/local/")):
            return "app"
        if target in {
            "sysinit.target",
            "basic.target",
            "local-fs.target",
            "initrd.target",
            "initrd-root-fs.target",
            "sockets.target",
        }:
            return "core"
        if name.startswith("systemd-"):
            return "core"
        if "core" in {tag.lower() for tag in service.tags}:
            return "core"
        if path.startswith(("/usr/lib/systemd/system/", "/lib/systemd/system/")):
            return "system"
        return "app" if path else "system"

    def _safe_int(self, value: str) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    def _guess_target(self, control_group: str, fallback: str) -> str:
        if "user.slice" in control_group:
            return "default.target"
        return fallback

    def _parse_show_output(self, output: str) -> dict[str, dict[str, str]]:
        records: dict[str, dict[str, str]] = {}
        current: dict[str, str] = {}
        current_name: str | None = None
        for line in output.splitlines():
            if not line.strip():
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key == "Id":
                if current_name is not None:
                    records[current_name] = current
                current = {"Id": value}
                current_name = value
            else:
                current[key] = value
        if current_name is not None:
            records[current_name] = current
        return records

    def _parse_unit_text(self, output: str, props: list[str]) -> dict[str, str]:
        data: dict[str, list[str]] = {prop: [] for prop in props}
        current_section = ""
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                current_section = stripped[1:-1]
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in data:
                continue
            if key == "WantedBy" and current_section != "Install":
                continue
            if key != "WantedBy" and key in {"Description", "Wants", "Requires", "After", "Before"} and current_section != "Unit":
                continue
            if key in {"ExecStart", "ExecReload", "ExecStop", "WorkingDirectory", "User", "Group", "Environment", "Restart"} and current_section != "Service":
                continue
            data[key].append(value.strip())
        return {key: "\n".join(values).strip() for key, values in data.items()}

    def _parse_unit_sections(self, output: str) -> dict[str, list[tuple[str, str]]]:
        sections: dict[str, list[tuple[str, str]]] = {}
        current_section = ""
        common = set(COMMON_FIELDS)
        seen: set[tuple[str, str, str]] = set()
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                current_section = stripped[1:-1]
                sections.setdefault(current_section, [])
                continue
            if "=" not in line or not current_section:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or key in common:
                continue
            item = (current_section, key, value)
            if item in seen:
                continue
            seen.add(item)
            sections[current_section].append((key, value))
        return sections
