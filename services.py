from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ServiceUnit:
    name: str
    description: str
    status: str
    enabled: bool
    load_state: str
    uptime: str
    since: str
    pid: str
    memory: str
    cpu: str
    restarts: int
    path: str
    target: str
    tags: list[str] = field(default_factory=list)
    deps: list[tuple[str, str]] = field(default_factory=list)
    journal: list[tuple[str, str]] = field(default_factory=list)
    favorite: bool = False
    service_class: str = "system"


def sample_services() -> list[ServiceUnit]:
    return [
        ServiceUnit(
            name="nginx.service",
            description="High-performance web server and reverse proxy",
            status="active",
            enabled=True,
            load_state="loaded",
            uptime="6d 13h",
            since="2026-05-06 08:14",
            pid="1421",
            memory="46.2 MB",
            cpu="1.3%",
            restarts=0,
            path="/usr/lib/systemd/system/nginx.service",
            target="multi-user.target",
            tags=["web", "proxy", "public"],
            deps=[
                ("network-online.target", "ok"),
                ("syslog.target", "ok"),
                ("sshd.service", "ok"),
            ],
            journal=[
                ("08:14", "Started nginx worker pool"),
                ("08:13", "Reloaded config from /etc/nginx/nginx.conf"),
                ("08:11", "Accepted 42 connections in the last minute"),
            ],
            favorite=True,
        ),
        ServiceUnit(
            name="postgresql.service",
            description="PostgreSQL RDBMS instance",
            status="active",
            enabled=True,
            load_state="loaded",
            uptime="12d 04h",
            since="2026-05-01 10:02",
            pid="891",
            memory="324 MB",
            cpu="4.8%",
            restarts=1,
            path="/lib/systemd/system/postgresql.service",
            target="multi-user.target",
            tags=["database", "storage"],
            deps=[
                ("local-fs.target", "ok"),
                ("network.target", "ok"),
                ("postgresql@14-main.service", "warn"),
            ],
            journal=[
                ("08:24", "Checkpoint complete: wrote 134 buffers"),
                ("07:58", "Autovacuum launched on app_user table"),
                ("07:12", "Recovered from clean shutdown"),
            ],
            favorite=True,
        ),
        ServiceUnit(
            name="redis-server.service",
            description="In-memory data store and cache layer",
            status="active",
            enabled=True,
            load_state="loaded",
            uptime="4d 01h",
            since="2026-05-09 05:21",
            pid="1174",
            memory="28.7 MB",
            cpu="0.7%",
            restarts=0,
            path="/lib/systemd/system/redis-server.service",
            target="multi-user.target",
            tags=["cache", "queue"],
            deps=[
                ("network.target", "ok"),
                ("syslog.target", "ok"),
            ],
            journal=[
                ("08:01", "PONG health probe returned in 3ms"),
                ("07:34", "Evicted 12 expired keys"),
                ("06:59", "Persistence snapshot completed"),
            ],
        ),
        ServiceUnit(
            name="docker.service",
            description="Docker Application Container Engine",
            status="active",
            enabled=True,
            load_state="loaded",
            uptime="9d 18h",
            since="2026-05-03 20:48",
            pid="1582",
            memory="192 MB",
            cpu="2.1%",
            restarts=0,
            path="/lib/systemd/system/docker.service",
            target="multi-user.target",
            tags=["containers", "build"],
            deps=[
                ("network-online.target", "ok"),
                ("containerd.service", "ok"),
            ],
            journal=[
                ("08:09", "Started 2 new containers"),
                ("07:46", "Network bridge initialized"),
                ("07:20", "Image layer cache reused"),
            ],
            favorite=True,
        ),
        ServiceUnit(
            name="ssh.service",
            description="OpenSSH server daemon",
            status="active",
            enabled=True,
            load_state="loaded",
            uptime="31d 02h",
            since="2026-04-12 09:10",
            pid="611",
            memory="12.8 MB",
            cpu="0.2%",
            restarts=0,
            path="/lib/systemd/system/ssh.service",
            target="multi-user.target",
            tags=["remote", "admin"],
            deps=[
                ("network.target", "ok"),
                ("sshd-keygen.service", "ok"),
            ],
            journal=[
                ("08:21", "Accepted publickey for ubn from 192.168.1.20"),
                ("07:50", "Session closed cleanly"),
                ("06:28", "Listening on port 22"),
            ],
        ),
        ServiceUnit(
            name="systemd-journald.service",
            description="Journal service for collecting logs",
            status="active",
            enabled=True,
            load_state="loaded",
            uptime="31d 02h",
            since="2026-04-12 09:01",
            pid="317",
            memory="52.4 MB",
            cpu="0.8%",
            restarts=0,
            path="/usr/lib/systemd/system/systemd-journald.service",
            target="sysinit.target",
            tags=["logs", "core"],
            deps=[
                ("system.slice", "ok"),
                ("local-fs.target", "ok"),
            ],
            journal=[
                ("08:27", "Rotated journal after reaching size limit"),
                ("08:12", "Indexed 4,218 new entries"),
                ("07:41", "Vacuumed archived logs"),
            ],
        ),
        ServiceUnit(
            name="bluetooth.service",
            description="Bluetooth daemon",
            status="inactive",
            enabled=False,
            load_state="loaded",
            uptime="stopped",
            since="2026-05-10 14:06",
            pid="-",
            memory="0 MB",
            cpu="0%",
            restarts=0,
            path="/lib/systemd/system/bluetooth.service",
            target="multi-user.target",
            tags=["hardware", "radio"],
            deps=[
                ("dbus.service", "ok"),
                ("bluetooth.target", "warn"),
            ],
            journal=[
                ("yesterday", "Stopped by user request"),
                ("yesterday", "Adapter power saved"),
                ("yesterday", "No controller present"),
            ],
        ),
        ServiceUnit(
            name="fail2ban.service",
            description="Bans hosts that trigger repeated authentication failures",
            status="failed",
            enabled=True,
            load_state="loaded",
            uptime="failed 14m ago",
            since="2026-05-13 07:59",
            pid="-",
            memory="0 MB",
            cpu="0%",
            restarts=3,
            path="/lib/systemd/system/fail2ban.service",
            target="multi-user.target",
            tags=["security", "ssh"],
            deps=[
                ("ssh.service", "ok"),
                ("iptables.service", "warn"),
            ],
            journal=[
                ("08:33", "Exited with status 1"),
                ("08:32", "Failed to parse backend log path"),
                ("08:31", "Restart count exceeded backoff threshold"),
            ],
            favorite=True,
        ),
    ]
