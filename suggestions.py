from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


SYSTEMD_DIRECTIVES = [
    "Description",
    "Documentation",
    "Wants",
    "Requires",
    "Requisite",
    "BindsTo",
    "PartOf",
    "Upholds",
    "Conflicts",
    "Before",
    "After",
    "OnFailure",
    "OnSuccess",
    "AssertPathExists",
    "AssertPathIsDirectory",
    "AssertPathIsSymbolicLink",
    "AssertFileIsExecutable",
    "ConditionPathExists",
    "ConditionPathIsDirectory",
    "ConditionPathIsSymbolicLink",
    "ConditionFileIsExecutable",
    "StartLimitIntervalSec",
    "StartLimitBurst",
    "StartLimitAction",
    "StopWhenUnneeded",
    "RefuseManualStart",
    "RefuseManualStop",
    "SourcePath",
    "RequiresMountsFor",
    "WantsMountsFor",
    "Slice",
    "Type",
    "ExecStart",
    "ExecStartPre",
    "ExecStartPost",
    "ExecReload",
    "ExecStop",
    "ExecStopPost",
    "Restart",
    "RestartSec",
    "RestartSteps",
    "RestartMaxDelaySec",
    "TimeoutStartSec",
    "TimeoutStopSec",
    "TimeoutAbortSec",
    "WorkingDirectory",
    "RootDirectory",
    "RootImage",
    "User",
    "Group",
    "SupplementaryGroups",
    "Environment",
    "EnvironmentFile",
    "PassEnvironment",
    "UnsetEnvironment",
    "UMask",
    "ExecSearchPath",
    "Nice",
    "IOSchedulingClass",
    "IOSchedulingPriority",
    "CPUWeight",
    "CPUQuota",
    "MemoryMax",
    "MemoryHigh",
    "TasksMax",
    "WantedBy",
    "Also",
    "Alias",
    "DefaultInstance",
]


DIRECTIVE_SECTIONS = {
    "Description": "Unit",
    "Documentation": "Unit",
    "Wants": "Unit",
    "Requires": "Unit",
    "Requisite": "Unit",
    "BindsTo": "Unit",
    "PartOf": "Unit",
    "Upholds": "Unit",
    "Conflicts": "Unit",
    "Before": "Unit",
    "After": "Unit",
    "OnFailure": "Unit",
    "OnSuccess": "Unit",
    "AssertPathExists": "Unit",
    "AssertPathIsDirectory": "Unit",
    "AssertPathIsSymbolicLink": "Unit",
    "AssertFileIsExecutable": "Unit",
    "ConditionPathExists": "Unit",
    "ConditionPathIsDirectory": "Unit",
    "ConditionPathIsSymbolicLink": "Unit",
    "ConditionFileIsExecutable": "Unit",
    "StartLimitIntervalSec": "Unit",
    "StartLimitBurst": "Unit",
    "StartLimitAction": "Unit",
    "StopWhenUnneeded": "Unit",
    "RefuseManualStart": "Unit",
    "RefuseManualStop": "Unit",
    "SourcePath": "Unit",
    "RequiresMountsFor": "Unit",
    "WantsMountsFor": "Unit",
    "Slice": "Service",
    "Type": "Service",
    "ExecStart": "Service",
    "ExecStartPre": "Service",
    "ExecStartPost": "Service",
    "ExecReload": "Service",
    "ExecStop": "Service",
    "ExecStopPost": "Service",
    "Restart": "Service",
    "RestartSec": "Service",
    "RestartSteps": "Service",
    "RestartMaxDelaySec": "Service",
    "TimeoutStartSec": "Service",
    "TimeoutStopSec": "Service",
    "TimeoutAbortSec": "Service",
    "WorkingDirectory": "Service",
    "RootDirectory": "Service",
    "RootImage": "Service",
    "User": "Service",
    "Group": "Service",
    "SupplementaryGroups": "Service",
    "Environment": "Service",
    "EnvironmentFile": "Service",
    "PassEnvironment": "Service",
    "UnsetEnvironment": "Service",
    "UMask": "Service",
    "ExecSearchPath": "Service",
    "Nice": "Service",
    "IOSchedulingClass": "Service",
    "IOSchedulingPriority": "Service",
    "CPUWeight": "Service",
    "CPUQuota": "Service",
    "MemoryMax": "Service",
    "MemoryHigh": "Service",
    "TasksMax": "Service",
    "WantedBy": "Install",
    "Also": "Install",
    "Alias": "Install",
    "DefaultInstance": "Install",
}

ADDITIONAL_DIRECTIVE_SECTIONS = {
    # [Unit]
    "ConditionPathExistsGlob": "Unit",
    "ConditionPathIsMountPoint": "Unit",
    "ConditionPathIsReadWrite": "Unit",
    "ConditionDirectoryNotEmpty": "Unit",
    "ConditionFileNotEmpty": "Unit",
    "ConditionUser": "Unit",
    "ConditionGroup": "Unit",
    "ConditionHost": "Unit",
    "ConditionKernelCommandLine": "Unit",
    "ConditionVirtualization": "Unit",
    "ConditionArchitecture": "Unit",
    "ConditionACPower": "Unit",
    "ConditionNeedsUpdate": "Unit",
    "ConditionFirstBoot": "Unit",
    # [Service]
    "ExitType": "Service",
    "RemainAfterExit": "Service",
    "GuessMainPID": "Service",
    "PIDFile": "Service",
    "BusName": "Service",
    "NotifyAccess": "Service",
    "ExecCondition": "Service",
    "RestartMode": "Service",
    "RestartPreventExitStatus": "Service",
    "RestartForceExitStatus": "Service",
    "SuccessExitStatus": "Service",
    "TimeoutSec": "Service",
    "RuntimeMaxSec": "Service",
    "WatchdogSec": "Service",
    "WatchdogSignal": "Service",
    "StandardInput": "Service",
    "StandardOutput": "Service",
    "StandardError": "Service",
    "TTYPath": "Service",
    "SyslogIdentifier": "Service",
    "LogLevelMax": "Service",
    "LogExtraFields": "Service",
    "RuntimeDirectory": "Service",
    "RuntimeDirectoryMode": "Service",
    "RuntimeDirectoryPreserve": "Service",
    "StateDirectory": "Service",
    "StateDirectoryMode": "Service",
    "CacheDirectory": "Service",
    "CacheDirectoryMode": "Service",
    "LogsDirectory": "Service",
    "LogsDirectoryMode": "Service",
    "ConfigurationDirectory": "Service",
    "ConfigurationDirectoryMode": "Service",
    "CPUSchedulingPolicy": "Service",
    "CPUSchedulingPriority": "Service",
    "CPUAffinity": "Service",
    "CPUQuotaPeriodSec": "Service",
    "MemoryLow": "Service",
    "MemoryMin": "Service",
    "MemorySwapMax": "Service",
    "MemoryAccounting": "Service",
    "CPUAccounting": "Service",
    "IOAccounting": "Service",
    "TasksAccounting": "Service",
    "LimitCPU": "Service",
    "LimitFSIZE": "Service",
    "LimitDATA": "Service",
    "LimitSTACK": "Service",
    "LimitCORE": "Service",
    "LimitRSS": "Service",
    "LimitNOFILE": "Service",
    "LimitAS": "Service",
    "LimitNPROC": "Service",
    "LimitMEMLOCK": "Service",
    "LimitLOCKS": "Service",
    "LimitSIGPENDING": "Service",
    "LimitMSGQUEUE": "Service",
    "LimitNICE": "Service",
    "LimitRTPRIO": "Service",
    "LimitRTTIME": "Service",
    "KillMode": "Service",
    "KillSignal": "Service",
    "RestartKillSignal": "Service",
    "FinalKillSignal": "Service",
    "SendSIGKILL": "Service",
    "SendSIGHUP": "Service",
    "OOMPolicy": "Service",
    "OOMScoreAdjust": "Service",
    "CapabilityBoundingSet": "Service",
    "AmbientCapabilities": "Service",
    "NoNewPrivileges": "Service",
    "PrivateTmp": "Service",
    "PrivateDevices": "Service",
    "PrivateNetwork": "Service",
    "PrivateUsers": "Service",
    "ProtectSystem": "Service",
    "ProtectHome": "Service",
    "ProtectHostname": "Service",
    "ProtectClock": "Service",
    "ProtectKernelTunables": "Service",
    "ProtectKernelModules": "Service",
    "ProtectKernelLogs": "Service",
    "ProtectControlGroups": "Service",
    "RestrictAddressFamilies": "Service",
    "RestrictNamespaces": "Service",
    "RestrictRealtime": "Service",
    "RestrictSUIDSGID": "Service",
    "SystemCallFilter": "Service",
    "SystemCallArchitectures": "Service",
    "ReadWritePaths": "Service",
    "ReadOnlyPaths": "Service",
    "InaccessiblePaths": "Service",
    "TemporaryFileSystem": "Service",
    "BindPaths": "Service",
    "BindReadOnlyPaths": "Service",
    # [Install]
    "RequiredBy": "Install",
    "UpheldBy": "Install",
}

DIRECTIVE_SECTIONS.update(ADDITIONAL_DIRECTIVE_SECTIONS)
SYSTEMD_DIRECTIVES = sorted(dict.fromkeys([*SYSTEMD_DIRECTIVES, *ADDITIONAL_DIRECTIVE_SECTIONS]), key=str.lower)

ENVIRONMENT_KEYS = [
    "PATH",
    "HOME",
    "USER",
    "SHELL",
    "LANG",
    "LC_ALL",
    "LD_LIBRARY_PATH",
    "PYTHONPATH",
    "NODE_ENV",
    "JAVA_HOME",
    "XDG_RUNTIME_DIR",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "TMPDIR",
]


@lru_cache(maxsize=1)
def command_suggestions() -> list[str]:
    paths = os.environ.get("PATH", "").split(os.pathsep)
    seen: set[str] = set()
    results: list[str] = []
    for dirname in paths:
        if not dirname:
            continue
        path = Path(dirname)
        if not path.is_dir():
            continue
        try:
            for entry in path.iterdir():
                if not entry.is_file():
                    continue
                if not os.access(entry, os.X_OK):
                    continue
                name = entry.name
                if name in seen:
                    continue
                seen.add(name)
                results.append(name)
        except OSError:
            continue
    results.sort()
    return results


@lru_cache(maxsize=1)
def user_suggestions() -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for line in Path("/etc/passwd").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 1)
        if not parts:
            continue
        name = parts[0].strip()
        if not name or name in seen:
            continue
        seen.add(name)
        results.append(name)
    results.sort()
    return results


@lru_cache(maxsize=1)
def group_suggestions() -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for line in Path("/etc/group").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 1)
        if not parts:
            continue
        name = parts[0].strip()
        if not name or name in seen:
            continue
        seen.add(name)
        results.append(name)
    results.sort()
    return results


@lru_cache(maxsize=512)
def path_suggestions(prefix: str = "") -> list[str]:
    raw = os.path.expanduser(prefix.strip())
    if not raw:
        roots = [
            "/etc/systemd/system/",
            "/opt/",
            "/srv/",
            "/usr/local/bin/",
            "/usr/bin/",
            "/bin/",
            str(Path.home()) + "/",
        ]
        return roots

    path = Path(raw)
    if raw.endswith(os.sep) or path.is_dir():
        directory = path
        needle = ""
    else:
        directory = path.parent
        needle = path.name

    if not directory.exists() or not directory.is_dir():
        return []

    results: list[str] = []
    seen: set[str] = set()
    try:
        for child in directory.iterdir():
            name = child.name
            if needle and not name.startswith(needle):
                continue
            candidate = str(child)
            if child.is_dir():
                candidate += os.sep
            if candidate in seen:
                continue
            seen.add(candidate)
            results.append(candidate)
    except OSError:
        return []
    results.sort()
    return results


@lru_cache(maxsize=1)
def target_suggestions() -> list[str]:
    static_targets = [
        "default.target",
        "basic.target",
        "sysinit.target",
        "multi-user.target",
        "graphical.target",
        "rescue.target",
        "emergency.target",
        "timers.target",
        "sockets.target",
        "paths.target",
        "local-fs.target",
        "remote-fs.target",
        "network.target",
        "network-online.target",
    ]
    targets: list[str] = []
    seen: set[str] = set()
    try:
        output = os.popen(
            "systemctl list-unit-files --type=target --no-legend --no-pager --plain"
        ).read()
        for line in output.splitlines():
            parts = line.split(None, 1)
            if not parts:
                continue
            name = parts[0].strip()
            if name.endswith(".target") and name not in seen:
                seen.add(name)
                targets.append(name)
    except Exception:
        pass
    for name in static_targets:
        if name not in seen:
            seen.add(name)
            targets.append(name)
    targets.sort()
    return targets
