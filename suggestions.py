from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


# Primary data structure: section → directives.
# A directive may appear in multiple sections (e.g. What in Mount and Swap).
SECTION_DIRECTIVES: dict[str, list[str]] = {
    "Unit": [
        "Description", "Documentation",
        "Wants", "Requires", "Requisite", "BindsTo", "PartOf", "Upholds",
        "Conflicts", "Before", "After", "OnFailure", "OnSuccess",
        "AssertPathExists", "AssertPathIsDirectory", "AssertPathIsSymbolicLink", "AssertFileIsExecutable",
        "ConditionPathExists", "ConditionPathIsDirectory", "ConditionPathIsSymbolicLink",
        "ConditionFileIsExecutable", "ConditionPathExistsGlob", "ConditionPathIsMountPoint",
        "ConditionPathIsReadWrite", "ConditionDirectoryNotEmpty", "ConditionFileNotEmpty",
        "ConditionUser", "ConditionGroup", "ConditionHost", "ConditionKernelCommandLine",
        "ConditionVirtualization", "ConditionArchitecture", "ConditionACPower",
        "ConditionNeedsUpdate", "ConditionFirstBoot",
        "StartLimitIntervalSec", "StartLimitBurst", "StartLimitAction",
        "StopWhenUnneeded", "RefuseManualStart", "RefuseManualStop",
        "SourcePath", "RequiresMountsFor", "WantsMountsFor",
        "DefaultDependencies", "CollectMode", "FailureAction", "SuccessAction",
        "JobTimeoutSec", "JobRunningTimeoutSec", "JobTimeoutAction",
    ],
    "Service": [
        "Type", "ExecStart", "ExecStartPre", "ExecStartPost",
        "ExecReload", "ExecStop", "ExecStopPre", "ExecStopPost", "ExecCondition",
        "Restart", "RestartSec", "RestartSteps", "RestartMaxDelaySec", "RestartMode",
        "RestartPreventExitStatus", "RestartForceExitStatus", "SuccessExitStatus",
        "TimeoutStartSec", "TimeoutStopSec", "TimeoutAbortSec", "TimeoutSec",
        "RuntimeMaxSec", "WatchdogSec", "WatchdogSignal",
        "RemainAfterExit", "GuessMainPID", "PIDFile", "BusName", "NotifyAccess",
        "ExitType", "OOMPolicy",
        "WorkingDirectory", "RootDirectory", "RootImage",
        "User", "Group", "SupplementaryGroups", "DynamicUser",
        "Environment", "EnvironmentFile", "PassEnvironment", "UnsetEnvironment",
        "UMask", "ExecSearchPath", "Nice",
        "IOSchedulingClass", "IOSchedulingPriority",
        "CPUWeight", "CPUQuota", "CPUQuotaPeriodSec", "CPUSchedulingPolicy",
        "CPUSchedulingPriority", "CPUAffinity", "CPUAccounting",
        "MemoryMax", "MemoryHigh", "MemoryLow", "MemoryMin", "MemorySwapMax",
        "MemoryAccounting", "MemoryZSwapMax",
        "TasksMax", "TasksAccounting",
        "IOAccounting",
        "OOMScoreAdjust", "Slice",
        "StandardInput", "StandardOutput", "StandardError", "TTYPath",
        "SyslogIdentifier", "LogLevelMax", "LogExtraFields",
        "RuntimeDirectory", "RuntimeDirectoryMode", "RuntimeDirectoryPreserve",
        "StateDirectory", "StateDirectoryMode",
        "CacheDirectory", "CacheDirectoryMode",
        "LogsDirectory", "LogsDirectoryMode",
        "ConfigurationDirectory", "ConfigurationDirectoryMode",
        "KillMode", "KillSignal", "RestartKillSignal", "FinalKillSignal",
        "SendSIGKILL", "SendSIGHUP",
        "LimitCPU", "LimitFSIZE", "LimitDATA", "LimitSTACK", "LimitCORE",
        "LimitRSS", "LimitNOFILE", "LimitAS", "LimitNPROC", "LimitMEMLOCK",
        "LimitLOCKS", "LimitSIGPENDING", "LimitMSGQUEUE", "LimitNICE",
        "LimitRTPRIO", "LimitRTTIME",
        "CapabilityBoundingSet", "AmbientCapabilities", "NoNewPrivileges",
        "PrivateTmp", "PrivateDevices", "PrivateNetwork", "PrivateUsers",
        "ProtectSystem", "ProtectHome", "ProtectHostname", "ProtectClock",
        "ProtectKernelTunables", "ProtectKernelModules", "ProtectKernelLogs",
        "ProtectControlGroups",
        "RestrictAddressFamilies", "RestrictNamespaces", "RestrictRealtime",
        "RestrictSUIDSGID", "SystemCallFilter", "SystemCallArchitectures",
        "ReadWritePaths", "ReadOnlyPaths", "InaccessiblePaths",
        "TemporaryFileSystem", "BindPaths", "BindReadOnlyPaths",
    ],
    "Socket": [
        "ListenStream", "ListenDatagram", "ListenSequentialPacket", "ListenFIFO",
        "ListenSpecial", "ListenNetlink", "ListenMessageQueue", "ListenUSBFunction",
        "SocketMode", "DirectoryMode", "Accept", "Writable",
        "MaxConnections", "MaxConnectionsPerSource",
        "KeepAlive", "KeepAliveTimeSec", "KeepAliveIntervalSec", "KeepAliveProbes",
        "NoDelay", "Priority", "ReceiveBuffer", "SendBuffer",
        "IPTOS", "IPTTL", "Mark", "ReusePort",
        "SmackLabel", "SmackLabelIPIn", "SmackLabelIPOut", "SELinuxContextFromNet",
        "PipeSize", "MessageQueueMaxMessages", "MessageQueueMessageSize",
        "FreeBind", "Transparent", "Broadcast",
        "PassCredentials", "PassSecurity", "PassPacketInfo", "Timestamping",
        "TCPCongestion", "ExecStartPre", "ExecStartPost", "ExecStopPre", "ExecStopPost",
        "Service", "RemoveOnStop", "Symlinks", "FileDescriptorName",
        "TriggerLimitIntervalSec", "TriggerLimitBurst",
        "SocketUser", "SocketGroup", "BindIPv6Only", "Backlog",
        "BindToDevice", "SocketProtocol", "FlushPending",
    ],
    "Mount": [
        "What", "Where", "Type", "Options", "SloppyOptions",
        "LazyUnmount", "ReadWriteOnly", "ForceUnmount", "DirectoryMode", "TimeoutSec",
    ],
    "Automount": [
        "Where", "ExpiryDurationSec", "TimeoutIdleSec", "DirectoryMode",
    ],
    "Swap": [
        "What", "Priority", "Options", "TimeoutSec",
    ],
    "Path": [
        "PathExists", "PathExistsGlob", "PathChanged", "PathModified",
        "DirectoryNotEmpty", "Unit", "MakeDirectory", "DirectoryMode",
        "TriggerLimitIntervalSec", "TriggerLimitBurst",
    ],
    "Timer": [
        "OnActiveSec", "OnBootSec", "OnStartupSec", "OnUnitActiveSec",
        "OnUnitInactiveSec", "OnCalendar", "AccuracySec", "RandomizedDelaySec",
        "FixedRandomDelay", "OnClockChange", "OnTimezoneChange",
        "Unit", "Persistent", "WakeSystem", "RemainAfterElapse",
        "TriggerLimitIntervalSec", "TriggerLimitBurst",
    ],
    "Slice": [
        "CPUAccounting", "CPUWeight", "StartupCPUWeight", "CPUQuota", "CPUQuotaPeriodSec",
        "AllowedCPUs", "AllowedMemoryNodes",
        "MemoryAccounting", "MemoryMin", "MemoryLow", "MemoryHigh",
        "MemoryMax", "MemorySwapMax", "MemoryZSwapMax",
        "IOAccounting", "IOWeight", "StartupIOWeight",
        "IODeviceWeight", "IOReadBandwidthMax", "IOWriteBandwidthMax",
        "IOReadIOPSMax", "IOWriteIOPSMax", "IODeviceLatencyTargetSec",
        "TasksAccounting", "TasksMax",
        "ManagedOOMSwap", "ManagedOOMMemoryPressure",
        "ManagedOOMMemoryPressureLimit", "ManagedOOMPreference",
    ],
    "Install": [
        "WantedBy", "RequiredBy", "UpheldBy", "Also", "Alias", "DefaultInstance",
    ],
}

# Flat directive → primary section (first section that defines it).
DIRECTIVE_SECTIONS: dict[str, str] = {}
for _sec, _dirs in SECTION_DIRECTIVES.items():
    for _d in _dirs:
        DIRECTIVE_SECTIONS.setdefault(_d, _sec)

# All unique directives sorted for autocomplete.
SYSTEMD_DIRECTIVES = sorted(
    dict.fromkeys(d for dirs in SECTION_DIRECTIVES.values() for d in dirs),
    key=str.lower,
)



def section_for_directive(key: str, type_section: str = "") -> str:
    """Return the correct section for a directive, preferring the unit's type_section."""
    if type_section and key in SECTION_DIRECTIVES.get(type_section, []):
        return type_section
    return DIRECTIVE_SECTIONS.get(key, "Service")

_BOOL = ["yes", "no", "true", "false"]
_SIGNALS = [
    "SIGABRT", "SIGALRM", "SIGBUS", "SIGCHLD", "SIGCONT", "SIGFPE",
    "SIGHUP", "SIGILL", "SIGINT", "SIGKILL", "SIGPIPE", "SIGQUIT",
    "SIGSEGV", "SIGSYS", "SIGTERM", "SIGTRAP", "SIGTSTP", "SIGTTIN",
    "SIGTTOU", "SIGURG", "SIGUSR1", "SIGUSR2", "SIGVTALRM", "SIGWINCH",
    "SIGXCPU", "SIGXFSZ",
]
_STDIO_OUT = [
    "inherit", "null", "tty", "journal", "kmsg",
    "journal+console", "kmsg+console",
    "file:", "append:", "truncate:", "socket", "fd:",
]

SECTION_DIRECTIVE_VALUE_SUGGESTIONS: dict[str, dict[str, list[str]]] = {
    "Mount": {
        "Type": [
            "ext4", "ext3", "ext2", "xfs", "btrfs", "vfat", "fat", "ntfs",
            "nfs", "nfs4", "cifs", "tmpfs", "overlay", "iso9660", "udf",
            "squashfs", "erofs", "exfat", "f2fs", "jfs", "reiserfs",
        ],
        "Options": ["defaults", "ro", "rw", "noatime", "relatime", "nodiratime",
                    "noexec", "nosuid", "nodev", "sync", "async", "auto", "noauto",
                    "user", "users", "owner", "nofail", "x-systemd.automount"],
    },
    "Swap": {
        "Options": ["defaults", "pri=", "discard", "nofail"],
    },
}

DIRECTIVE_VALUE_SUGGESTIONS: dict[str, list[str]] = {
    # ── [Service] ──────────────────────────────────────────────────────
    "Type": ["simple", "exec", "forking", "oneshot", "dbus",
             "notify", "notify-reload", "idle"],
    "Restart": ["no", "on-success", "on-failure", "on-abnormal",
                "on-watchdog", "on-abort", "always"],
    "RestartMode": ["normal", "direct"],
    "ExitType": ["main", "cgroup"],
    "NotifyAccess": ["none", "main", "exec", "all"],
    "OOMPolicy": ["continue", "stop", "kill"],
    "KillMode": ["control-group", "process", "mixed", "none"],
    "KillSignal": _SIGNALS,
    "RestartKillSignal": _SIGNALS,
    "FinalKillSignal": _SIGNALS,
    "WatchdogSignal": _SIGNALS,
    "StandardInput": ["null", "tty", "tty-force", "tty-fail",
                      "data", "file:", "socket", "fd:"],
    "StandardOutput": _STDIO_OUT,
    "StandardError": _STDIO_OUT,
    "IOSchedulingClass": ["none", "realtime", "best-effort", "idle"],
    "CPUSchedulingPolicy": ["other", "batch", "idle", "fifo", "rr"],
    "ProtectSystem": ["true", "false", "full", "strict"],
    "ProtectHome": ["true", "false", "read-only", "tmpfs"],
    "RuntimeDirectoryPreserve": ["no", "yes", "restart"],
    "MountAPIVFS": _BOOL,
    "RemainAfterExit": _BOOL,
    "GuessMainPID": _BOOL,
    "SendSIGKILL": _BOOL,
    "SendSIGHUP": _BOOL,
    "PrivateTmp": _BOOL,
    "PrivateDevices": _BOOL,
    "PrivateNetwork": _BOOL,
    "PrivateUsers": _BOOL,
    "PrivateMounts": _BOOL,
    "PrivateIPC": _BOOL,
    "ProtectHostname": _BOOL,
    "ProtectClock": _BOOL,
    "ProtectKernelTunables": _BOOL,
    "ProtectKernelModules": _BOOL,
    "ProtectKernelLogs": _BOOL,
    "ProtectControlGroups": _BOOL,
    "ProtectProc": ["noaccess", "invisible", "ptraceable", "default"],
    "ProcSubset": ["all", "pid"],
    "LockPersonality": _BOOL,
    "MemoryDenyWriteExecute": _BOOL,
    "NoNewPrivileges": _BOOL,
    "RestrictRealtime": _BOOL,
    "RestrictSUIDSGID": _BOOL,
    "DynamicUser": _BOOL,
    # ── [Unit] ─────────────────────────────────────────────────────────
    "StartLimitAction": [
        "none", "reboot", "reboot-force", "reboot-immediate",
        "poweroff", "poweroff-force", "poweroff-immediate",
        "exit", "exit-force", "halt", "halt-force", "halt-immediate",
    ],
    "StopWhenUnneeded": _BOOL,
    "RefuseManualStart": _BOOL,
    "RefuseManualStop": _BOOL,
    "ConditionVirtualization": [
        "private", "container", "vm", "host",
        "kvm", "qemu", "bochs", "xen", "uml",
        "openvz", "lxc", "lxc-libvirt", "systemd-nspawn",
        "docker", "podman", "rkt", "wsl", "proot", "acrn",
    ],
    "ConditionArchitecture": [
        "x86", "x86-64", "ppc", "ppc-le", "ppc64", "ppc64-le",
        "ia64", "parisc", "parisc64", "s390", "s390x",
        "sparc", "sparc64", "mips", "mips-le", "mips64", "mips64-le",
        "alpha", "arm", "arm-be", "arm64", "arm64-be",
        "sh", "sh64", "m68k", "tilegx", "cris", "arc", "arc-be", "native",
    ],
    "ConditionACPower": _BOOL,
    "ConditionFirstBoot": _BOOL,
    # ── [Timer] ────────────────────────────────────────────────────────
    "WakeSystem": _BOOL,
    "Persistent": _BOOL,
    "RemainAfterElapse": _BOOL,
    "FixedRandomDelay": _BOOL,
    "OnClockChange": _BOOL,
    "OnTimezoneChange": _BOOL,
    # ── [Socket] ───────────────────────────────────────────────────────
    "Accept": _BOOL,
    "Writable": _BOOL,
    "KeepAlive": _BOOL,
    "NoDelay": _BOOL,
    "FreeBind": _BOOL,
    "Transparent": _BOOL,
    "Broadcast": _BOOL,
    "PassCredentials": _BOOL,
    "PassSecurity": _BOOL,
    "PassPacketInfo": _BOOL,
    "ReusePort": _BOOL,
    "RemoveOnStop": _BOOL,
    "FlushPending": _BOOL,
    "SELinuxContextFromNet": _BOOL,
    "BindIPv6Only": ["default", "both", "ipv6-only"],
    "Timestamping": ["off", "us", "usec", "ns", "nsec"],
    "SocketProtocol": ["udplite", "sctp"],
    # ── [Mount] ────────────────────────────────────────────────────────
    "SloppyOptions": _BOOL,
    "LazyUnmount": _BOOL,
    "ReadWriteOnly": _BOOL,
    "ForceUnmount": _BOOL,
    # ── [Automount] ────────────────────────────────────────────────────
    # (no closed-value directives beyond booleans already listed)
    # ── [Path] ─────────────────────────────────────────────────────────
    "MakeDirectory": _BOOL,
    # ── [Slice] ────────────────────────────────────────────────────────
    "ManagedOOMSwap": ["auto", "kill"],
    "ManagedOOMMemoryPressure": ["auto", "kill"],
    "ManagedOOMPreference": ["none", "avoid", "omit"],
}

# Maps unit file suffix to the name of its type-specific section
SUFFIX_TO_SECTION: dict[str, str] = {
    "service": "Service",
    "socket": "Socket",
    "mount": "Mount",
    "automount": "Automount",
    "swap": "Swap",
    "path": "Path",
    "timer": "Timer",
    "slice": "Slice",
    "target": "",   # targets have only [Unit] and [Install]
    "scope": "Service",  # scopes share Service directives
    "device": "",   # device units have only [Unit]
}

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


def path_suggestions(prefix: str = "") -> list[str]:
    raw = os.path.expanduser(prefix.strip())
    if not raw:
        return [
            "/etc/systemd/system/",
            "/opt/",
            "/srv/",
            "/usr/local/bin/",
            "/usr/bin/",
            "/bin/",
            str(Path.home()) + "/",
        ]
    path = Path(raw)
    if raw.endswith(os.sep) or path.is_dir():
        directory, needle = path, ""
    else:
        directory, needle = path.parent, path.name
    if not directory.exists() or not directory.is_dir():
        return []
    results: list[str] = []
    seen: set[str] = set()
    try:
        for child in directory.iterdir():
            if needle and not child.name.startswith(needle):
                continue
            candidate = str(child) + (os.sep if child.is_dir() else "")
            if candidate not in seen:
                seen.add(candidate)
                results.append(candidate)
    except OSError:
        return []
    results.sort()
    return results


@lru_cache(maxsize=1)
def disk_suggestions() -> list[str]:
    """Block devices and partitions suitable for What= in mount/swap units."""
    devices: list[str] = []
    seen: set[str] = set()
    try:
        output = os.popen("lsblk -rno PATH,TYPE 2>/dev/null").read()
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            path, kind = parts[0], parts[1]
            if kind in {"disk", "part", "lvm", "raid1", "crypt"} and path not in seen:
                seen.add(path)
                devices.append(path)
    except Exception:
        pass
    try:
        output = os.popen("blkid -o export 2>/dev/null").read()
        uuid = label = ""
        for line in output.splitlines():
            if line.startswith("UUID="):
                uuid = line.strip()
            elif line.startswith("LABEL="):
                label = line.strip()
            elif line == "" and uuid:
                if uuid and uuid not in seen:
                    seen.add(uuid); devices.append(uuid)
                if label and label not in seen:
                    seen.add(label); devices.append(label)
                uuid = label = ""
    except Exception:
        pass
    devices.sort()
    return devices


@lru_cache(maxsize=1)
def unit_suggestions() -> list[str]:
    units: list[str] = []
    seen: set[str] = set()
    try:
        output = os.popen(
            "systemctl list-unit-files --no-legend --no-pager --plain"
        ).read()
        for line in output.splitlines():
            parts = line.split()
            if not parts:
                continue
            name = parts[0].strip()
            if name and name not in seen:
                seen.add(name)
                units.append(name)
    except Exception:
        pass
    units.sort()
    return units


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


