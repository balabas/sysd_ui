(function () {
  "use strict";

  const services = [
    {
      name: "nginx.service",
      description: "High-performance web server and reverse proxy",
      status: "active",
      enabled: true,
      load: "loaded",
      uptime: "6d 13h",
      since: "2026-05-06 08:14",
      pid: 1421,
      memory: "46.2 MB",
      cpu: "1.3%",
      restarts: 0,
      path: "/usr/lib/systemd/system/nginx.service",
      target: "multi-user.target",
      tags: ["web", "proxy", "public"],
      deps: [
        ["network-online.target", "ok"],
        ["syslog.target", "ok"],
        ["sshd.service", "ok"],
      ],
      journal: [
        ["08:14", "Started nginx worker pool"],
        ["08:13", "Reloaded config from /etc/nginx/nginx.conf"],
        ["08:11", "Accepted 42 connections in the last minute"],
      ],
      favorite: true,
    },
    {
      name: "postgresql.service",
      description: "PostgreSQL RDBMS instance",
      status: "active",
      enabled: true,
      load: "loaded",
      uptime: "12d 04h",
      since: "2026-05-01 10:02",
      pid: 891,
      memory: "324 MB",
      cpu: "4.8%",
      restarts: 1,
      path: "/lib/systemd/system/postgresql.service",
      target: "multi-user.target",
      tags: ["database", "storage"],
      deps: [
        ["local-fs.target", "ok"],
        ["network.target", "ok"],
        ["postgresql@14-main.service", "warn"],
      ],
      journal: [
        ["08:24", "Checkpoint complete: wrote 134 buffers"],
        ["07:58", "Autovacuum launched on app_user table"],
        ["07:12", "Recovered from clean shutdown"],
      ],
      favorite: true,
    },
    {
      name: "redis-server.service",
      description: "In-memory data store and cache layer",
      status: "active",
      enabled: true,
      load: "loaded",
      uptime: "4d 01h",
      since: "2026-05-09 05:21",
      pid: 1174,
      memory: "28.7 MB",
      cpu: "0.7%",
      restarts: 0,
      path: "/lib/systemd/system/redis-server.service",
      target: "multi-user.target",
      tags: ["cache", "queue"],
      deps: [
        ["network.target", "ok"],
        ["syslog.target", "ok"],
      ],
      journal: [
        ["08:01", "PONG health probe returned in 3ms"],
        ["07:34", "Evicted 12 expired keys"],
        ["06:59", "Persistence snapshot completed"],
      ],
      favorite: false,
    },
    {
      name: "docker.service",
      description: "Docker Application Container Engine",
      status: "active",
      enabled: true,
      load: "loaded",
      uptime: "9d 18h",
      since: "2026-05-03 20:48",
      pid: 1582,
      memory: "192 MB",
      cpu: "2.1%",
      restarts: 0,
      path: "/lib/systemd/system/docker.service",
      target: "multi-user.target",
      tags: ["containers", "build"],
      deps: [
        ["network-online.target", "ok"],
        ["containerd.service", "ok"],
      ],
      journal: [
        ["08:09", "Started 2 new containers"],
        ["07:46", "Network bridge initialized"],
        ["07:20", "Image layer cache reused"],
      ],
      favorite: true,
    },
    {
      name: "ssh.service",
      description: "OpenSSH server daemon",
      status: "active",
      enabled: true,
      load: "loaded",
      uptime: "31d 02h",
      since: "2026-04-12 09:10",
      pid: 611,
      memory: "12.8 MB",
      cpu: "0.2%",
      restarts: 0,
      path: "/lib/systemd/system/ssh.service",
      target: "multi-user.target",
      tags: ["remote", "admin"],
      deps: [
        ["network.target", "ok"],
        ["sshd-keygen.service", "ok"],
      ],
      journal: [
        ["08:21", "Accepted publickey for ubn from 192.168.1.20"],
        ["07:50", "Session closed cleanly"],
        ["06:28", "Listening on port 22"],
      ],
      favorite: false,
    },
    {
      name: "systemd-journald.service",
      description: "Journal service for collecting logs",
      status: "active",
      enabled: true,
      load: "loaded",
      uptime: "31d 02h",
      since: "2026-04-12 09:01",
      pid: 317,
      memory: "52.4 MB",
      cpu: "0.8%",
      restarts: 0,
      path: "/usr/lib/systemd/system/systemd-journald.service",
      target: "sysinit.target",
      tags: ["logs", "core"],
      deps: [
        ["system.slice", "ok"],
        ["local-fs.target", "ok"],
      ],
      journal: [
        ["08:27", "Rotated journal after reaching size limit"],
        ["08:12", "Indexed 4,218 new entries"],
        ["07:41", "Vacuumed archived logs"],
      ],
      favorite: false,
    },
    {
      name: "bluetooth.service",
      description: "Bluetooth daemon",
      status: "inactive",
      enabled: false,
      load: "loaded",
      uptime: "stopped",
      since: "2026-05-10 14:06",
      pid: "-",
      memory: "0 MB",
      cpu: "0%",
      restarts: 0,
      path: "/lib/systemd/system/bluetooth.service",
      target: "multi-user.target",
      tags: ["hardware", "radio"],
      deps: [
        ["dbus.service", "ok"],
        ["bluetooth.target", "warn"],
      ],
      journal: [
        ["yesterday", "Stopped by user request"],
        ["yesterday", "Adapter power saved"],
        ["yesterday", "No controller present"],
      ],
      favorite: false,
    },
    {
      name: "fail2ban.service",
      description: "Bans hosts that trigger repeated authentication failures",
      status: "failed",
      enabled: true,
      load: "loaded",
      uptime: "failed 14m ago",
      since: "2026-05-13 07:59",
      pid: "-",
      memory: "0 MB",
      cpu: "0%",
      restarts: 3,
      path: "/lib/systemd/system/fail2ban.service",
      target: "multi-user.target",
      tags: ["security", "ssh"],
      deps: [
        ["ssh.service", "ok"],
        ["iptables.service", "warn"],
      ],
      journal: [
        ["08:33", "Exited with status 1"],
        ["08:32", "Failed to parse backend log path"],
        ["08:31", "Restart count exceeded backoff threshold"],
      ],
      favorite: true,
    },
  ];

  const targets = [
    ["multi-user.target", "Standard server boot target"],
    ["graphical.target", "Desktop/session services"],
    ["sysinit.target", "Core boot dependencies"],
    ["timers.target", "Scheduled jobs and timers"],
  ];

  const state = {
    query: "",
    filter: "all",
    sort: "name",
    selected: services[0].name,
    logCounter: 0,
  };

  const els = {};

  function init() {
    cacheDom();
    renderTargets();
    renderFilters();
    wireEvents();
    renderAll();
    bumpSync("Loaded preview dataset");
  }

  function cacheDom() {
    [
      "target-list",
      "stats-grid",
      "status-filters",
      "service-list",
      "list-title",
      "list-meta",
      "detail-name",
      "detail-description",
      "detail-status",
      "detail-grid",
      "action-row",
      "dependency-stack",
      "journal",
      "active-unit",
      "last-sync",
      "connection-state",
      "search",
      "host-name",
      "host-meta",
      "metric-uptime",
      "metric-jobs",
      "metric-failed",
      "refresh-btn",
      "reload-daemon-btn",
    ].forEach((id) => {
      els[id] = document.getElementById(id);
    });
  }

  function renderTargets() {
    els["target-list"].innerHTML = targets.map(([name, desc], index) => {
      const active = index === 0 ? "active" : "";
      return `
        <button class="target-pill ${active}" type="button" data-target="${name}">
          <span class="target-name">${name}</span>
          <span class="target-desc">${desc}</span>
        </button>
      `;
    }).join("");
  }

  function renderFilters() {
    const statuses = [
      ["all", "All"],
      ["active", "Active"],
      ["inactive", "Inactive"],
      ["failed", "Failed"],
      ["enabled", "Enabled"],
    ];

    els["status-filters"].innerHTML = statuses.map(([key, label]) => (
      `<button class="chip ${key === state.filter ? "active" : ""}" type="button" data-filter="${key}">${label}</button>`
    )).join("");
  }

  function wireEvents() {
    els.search.addEventListener("input", (event) => {
      state.query = event.target.value.trim().toLowerCase();
      renderAll();
    });

    els["status-filters"].addEventListener("click", (event) => {
      const button = event.target.closest("[data-filter]");
      if (!button) return;
      state.filter = button.dataset.filter;
      renderFilters();
      renderAll();
    });

    document.querySelector(".chip-group:last-child").addEventListener("click", (event) => {
      const button = event.target.closest("[data-sort]");
      if (!button) return;
      state.sort = button.dataset.sort;
      [...document.querySelectorAll("[data-sort]")].forEach((chip) => chip.classList.toggle("active", chip === button));
      renderAll();
      bumpSync(`Sorted by ${state.sort}`);
    });

    els["service-list"].addEventListener("click", (event) => {
      const card = event.target.closest("[data-service]");
      if (!card) return;
      state.selected = card.dataset.service;
      renderAll();
    });

    els["action-row"].addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      applyAction(button.dataset.action);
    });

    els["target-list"].addEventListener("click", (event) => {
      const pill = event.target.closest("[data-target]");
      if (!pill) return;
      [...document.querySelectorAll("[data-target]")].forEach((node) => node.classList.toggle("active", node === pill));
      bumpSync(`Viewing ${pill.dataset.target}`);
    });

    els["refresh-btn"].addEventListener("click", () => {
      tickPreview();
      bumpSync("Refreshed unit snapshots");
    });

    els["reload-daemon-btn"].addEventListener("click", () => {
      const selected = getSelectedService();
      if (selected) {
        addJournal(selected.name, "Requested daemon-reload and reloaded unit metadata");
      }
      bumpSync("Daemon reloaded");
    });
  }

  function renderAll() {
    const filtered = getFilteredServices();
    const sorted = sortServices(filtered);

    renderStats(sorted);
    renderList(sorted);
    renderDetails(getSelectedService());

    els["list-title"].textContent = state.filter === "all" ? "All services" : `${capitalize(state.filter)} services`;
    els["list-meta"].textContent = `${sorted.length} unit${sorted.length === 1 ? "" : "s"}`;
    els["active-unit"].textContent = getSelectedService()?.name || "none";
    els["connection-state"].textContent = "Local preview mode";
  }

  function renderStats(list) {
    const total = services.length;
    const active = services.filter((svc) => svc.status === "active").length;
    const failed = services.filter((svc) => svc.status === "failed").length;
    const enabled = services.filter((svc) => svc.enabled).length;

    const cards = [
      ["Loaded units", total, "Units in the preview dataset"],
      ["Active", active, "Currently running services"],
      ["Failed", failed, "Units needing attention"],
      ["Enabled", enabled, "Autostart-enabled units"],
    ];

    els["stats-grid"].innerHTML = cards.map(([label, value, note]) => `
      <article class="stat-card">
        <div class="stat-label">${label}</div>
        <div class="stat-value">${value}</div>
        <div class="stat-note">${note}</div>
      </article>
    `).join("");

    els["metric-jobs"].textContent = Math.max(0, failed + (active > 5 ? 1 : 0));
    els["metric-failed"].textContent = failed;
    els["metric-uptime"].textContent = "12d 04h";
  }

  function renderList(list) {
    if (!list.length) {
      els["service-list"].innerHTML = `
        <div class="tip-card" style="grid-column:1/-1">
          <p>No units match the current search or filter.</p>
          <p class="tip-note">Try clearing the query or switching to All services.</p>
        </div>
      `;
      return;
    }

    const template = document.getElementById("service-card-template");
    const fragment = document.createDocumentFragment();

    list.forEach((svc) => {
      const node = template.content.firstElementChild.cloneNode(true);
      node.dataset.service = svc.name;
      node.classList.toggle("selected", svc.name === state.selected);
      node.classList.toggle("favorite", svc.favorite);

      node.querySelector(".service-icon").textContent = serviceGlyph(svc);
      node.querySelector(".service-name").textContent = svc.name;
      node.querySelector(".service-desc").textContent = svc.description;

      const flags = node.querySelector(".service-flags");
      flags.innerHTML = [
        badge(svc.status, svc.status),
        badge(svc.enabled ? "enabled" : "disabled", svc.enabled ? "enabled" : "disabled"),
        badge(svc.load, svc.load),
      ].join("");

      node.querySelector(".service-state").textContent = `${svc.pid === "-" ? "no pid" : `pid ${svc.pid}`} · ${svc.memory}`;
      node.querySelector(".service-time").textContent = svc.uptime;

      fragment.appendChild(node);
    });

    els["service-list"].innerHTML = "";
    els["service-list"].appendChild(fragment);
  }

  function renderDetails(service) {
    if (!service) {
      els["detail-name"].textContent = "Pick a service";
      els["detail-description"].textContent = "Select a unit from the list to inspect its state and perform actions.";
      els["detail-status"].textContent = "idle";
      els["detail-status"].className = "detail-status";
      els["detail-grid"].innerHTML = "";
      els["action-row"].innerHTML = "";
      els["dependency-stack"].innerHTML = "";
      els["journal"].innerHTML = "";
      return;
    }

    els["detail-name"].textContent = service.name;
    els["detail-description"].textContent = service.description;
    els["detail-status"].textContent = service.status;
    els["detail-status"].className = `detail-status ${service.status}`;

    els["detail-grid"].innerHTML = [
      ["Load state", service.load],
      ["Enabled", service.enabled ? "yes" : "no"],
      ["PID", service.pid],
      ["Uptime", service.uptime],
      ["Since", service.since],
      ["Target", service.target],
      ["Memory", service.memory],
      ["CPU", service.cpu],
      ["Path", service.path],
      ["Restarts", String(service.restarts)],
    ].map(([label, value]) => `
      <div class="kv">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `).join("");

    els["action-row"].innerHTML = buildActions(service).join("");

    els["dependency-stack"].innerHTML = service.deps.map(([name, state]) => `
      <div class="dependency-item">
        <div>
          <strong>${name}</strong>
          <span>${dependencyHint(state)}</span>
        </div>
        <div class="dependency-state ${state === "ok" ? "ok" : "warn"}">${state}</div>
      </div>
    `).join("");

    els["journal"].innerHTML = service.journal.map(([time, text]) => `
      <div class="journal-item">
        <div>
          <strong>${text}</strong>
          <span>systemd journal</span>
        </div>
        <div class="journal-time">${time}</div>
      </div>
    `).join("");

    els["host-name"].textContent = "devbox-01";
    els["host-meta"].textContent = `${service.name} selected · focus unit details and actions`;
  }

  function buildActions(service) {
    const actions = [];
    if (service.status === "active") {
      actions.push(actionButton("stop", "Stop"));
      actions.push(actionButton("restart", "Restart", true));
      actions.push(actionButton(service.enabled ? "disable" : "enable", service.enabled ? "Disable" : "Enable"));
    } else if (service.status === "failed") {
      actions.push(actionButton("restart", "Restart", true));
      actions.push(actionButton("start", "Start", true));
      actions.push(actionButton(service.enabled ? "disable" : "enable", service.enabled ? "Disable" : "Enable"));
    } else {
      actions.push(actionButton("start", "Start", true));
      actions.push(actionButton(service.enabled ? "disable" : "enable", service.enabled ? "Disable" : "Enable"));
    }

    actions.push(actionButton(service.favorite ? "unfavorite" : "favorite", service.favorite ? "Unpin" : "Pin"));
    actions.push(actionButton(service.enabled ? "mask" : "unmask", service.enabled ? "Mask" : "Unmask", false, "danger"));
    return actions;
  }

  function actionButton(action, label, primary = false, variant = "") {
    return `
      <button class="action-btn ${primary ? "primary" : ""} ${variant}" type="button" data-action="${action}">
        ${label}
      </button>
    `;
  }

  function applyAction(action) {
    const service = getSelectedService();
    if (!service) return;

    switch (action) {
      case "start":
        service.status = "active";
        service.enabled = true;
        service.pid = randomPid();
        service.uptime = "0m";
        service.restarts += 1;
        service.memory = "16.8 MB";
        service.cpu = "0.4%";
        addJournal(service.name, "Started unit successfully");
        break;
      case "stop":
        service.status = "inactive";
        service.pid = "-";
        service.uptime = "stopped";
        service.cpu = "0%";
        service.memory = "0 MB";
        addJournal(service.name, "Stopped unit cleanly");
        break;
      case "restart":
        service.status = "active";
        service.pid = randomPid();
        service.uptime = "0m";
        service.restarts += 1;
        service.cpu = "0.9%";
        addJournal(service.name, "Restarted unit and reloaded sockets");
        break;
      case "enable":
        service.enabled = true;
        addJournal(service.name, "Enabled unit for future boots");
        break;
      case "disable":
        service.enabled = false;
        addJournal(service.name, "Disabled unit from autostart");
        break;
      case "mask":
        service.enabled = false;
        service.status = "inactive";
        service.pid = "-";
        addJournal(service.name, "Masked unit to prevent accidental starts");
        break;
      case "unmask":
        service.enabled = true;
        addJournal(service.name, "Unmasked unit");
        break;
      case "favorite":
        service.favorite = true;
        addJournal(service.name, "Pinned to favorites");
        break;
      case "unfavorite":
        service.favorite = false;
        addJournal(service.name, "Removed from favorites");
        break;
      default:
        break;
    }

    state.selected = service.name;
    renderAll();
    bumpSync(`${service.name}: ${action}`);
  }

  function getFilteredServices() {
    return services.filter((service) => {
      const haystack = [
        service.name,
        service.description,
        service.path,
        service.target,
        service.tags.join(" "),
      ].join(" ").toLowerCase();

      const matchesQuery = !state.query || haystack.includes(state.query);
      const matchesFilter = state.filter === "all"
        || (state.filter === "enabled" && service.enabled)
        || service.status === state.filter;

      return matchesQuery && matchesFilter;
    });
  }

  function sortServices(list) {
    const copy = [...list];
    switch (state.sort) {
      case "status":
        return copy.sort((a, b) => a.status.localeCompare(b.status) || a.name.localeCompare(b.name));
      case "uptime":
        return copy.sort((a, b) => uptimeScore(b.uptime) - uptimeScore(a.uptime));
      case "name":
      default:
        return copy.sort((a, b) => a.name.localeCompare(b.name));
    }
  }

  function getSelectedService() {
    return services.find((service) => service.name === state.selected) || services[0];
  }

  function badge(value, label) {
    return `<span class="flag ${value}">${label}</span>`;
  }

  function serviceGlyph(service) {
    if (service.status === "failed") return "!";
    if (service.status === "inactive") return "∅";
    if (service.name.includes("ssh")) return "SSH";
    if (service.name.includes("post")) return "DB";
    if (service.name.includes("docker")) return "D";
    return service.name.charAt(0).toUpperCase();
  }

  function dependencyHint(state) {
    return state === "ok" ? "Dependency satisfied" : "Watch this unit for ordering issues";
  }

  function uptimeScore(value) {
    const raw = String(value).toLowerCase();
    if (raw.includes("stopped") || raw.includes("failed")) return 0;
    const days = (raw.match(/(\d+)d/) || [0, 0])[1];
    const hours = (raw.match(/(\d+)h/) || [0, 0])[1];
    const mins = (raw.match(/(\d+)m/) || [0, 0])[1];
    return (Number(days) * 24 * 60) + (Number(hours) * 60) + Number(mins);
  }

  function randomPid() {
    return Math.floor(300 + Math.random() * 8000);
  }

  function addJournal(unit, message) {
    const service = services.find((item) => item.name === unit);
    if (!service) return;
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    service.journal.unshift([time, message]);
    service.journal = service.journal.slice(0, 4);
  }

  function bumpSync(message) {
    state.logCounter += 1;
    els["last-sync"].textContent = `Just now · ${message}`;
  }

  function tickPreview() {
    services.forEach((service) => {
      if (service.status !== "active") return;
      const cpu = (0.2 + Math.random() * 4.0).toFixed(1);
      const mem = Math.max(8, Math.round((Math.random() * 340) + 8));
      service.cpu = `${cpu}%`;
      service.memory = `${mem} MB`;
    });
    const active = services.find((service) => service.name === state.selected);
    if (active) {
      addJournal(active.name, "Polled new runtime metrics");
    }
    renderAll();
  }

  function capitalize(value) {
    return value.charAt(0).toUpperCase() + value.slice(1);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
