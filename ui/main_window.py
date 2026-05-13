from __future__ import annotations

import logging
import json
import os
import shlex
from shutil import which
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import GLib, Gdk, Gtk, Pango

from backend import BackendError, SystemdBackend
from properties import COMMON_FIELDS, ordered_rows
from services import ServiceUnit
from suggestions import (
    ENVIRONMENT_KEYS,
    SYSTEMD_DIRECTIVES,
    command_suggestions,
    group_suggestions,
    path_suggestions,
    target_suggestions,
    user_suggestions,
)


LOGGER = logging.getLogger("sysd_ui.ui")
URI_LIST_TARGET = [Gtk.TargetEntry.new("text/uri-list", 0, 0)]


CSS = b"""
window, .shell {
  background: #091017;
  color: #eef4f8;
  font-family: "Segoe UI Variable", "Inter", "SF Pro Display", system-ui, sans-serif;
}

.shell {
  background:
    radial-gradient(circle at top left, rgba(76, 201, 240, 0.14), transparent 30%),
    radial-gradient(circle at 85% 18%, rgba(45, 220, 139, 0.10), transparent 22%),
    linear-gradient(180deg, #060b12 0%, #091017 100%);
}

.brand {
  padding: 14px 18px;
}

.brand-title {
  font-size: 18px;
  font-weight: 800;
}

.brand-subtitle, .muted, .meta {
  color: #93a7b8;
}

.panel, .card {
  background: rgba(12, 18, 28, 0.92);
  border: 1px solid rgba(120, 145, 171, 0.18);
  border-radius: 18px;
}

.panel {
  padding: 14px;
}

.sidebar-title {
  color: #6e8091;
  letter-spacing: 0.16em;
  font-size: 11px;
  margin-bottom: 8px;
}

.service-row {
  padding: 12px;
  margin-bottom: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
}

.service-row:selected {
  background: rgba(76, 201, 240, 0.11);
  border-color: rgba(76, 201, 240, 0.38);
}

.service-name {
  font-size: 14px;
  font-weight: 800;
}

.service-desc {
  color: #93a7b8;
  font-size: 12px;
  margin-top: 4px;
}

.pill {
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 10px;
  letter-spacing: 0.08em;
  border: 1px solid transparent;
}

.pill.active { background: rgba(45, 220, 139, 0.12); color: #cdfbe0; border-color: rgba(45, 220, 139, 0.24); }
.pill.inactive { background: rgba(255, 255, 255, 0.04); color: #93a7b8; border-color: rgba(255, 255, 255, 0.08); }
.pill.failed { background: rgba(255, 100, 112, 0.12); color: #ffd5d8; border-color: rgba(255, 100, 112, 0.24); }
.pill.enabled { background: rgba(76, 201, 240, 0.12); color: #d7f8ff; border-color: rgba(76, 201, 240, 0.24); }
.pill.core { background: rgba(255, 194, 102, 0.14); color: #ffe6ba; border-color: rgba(255, 194, 102, 0.28); }
.pill.system { background: rgba(76, 201, 240, 0.12); color: #d7f8ff; border-color: rgba(76, 201, 240, 0.24); }
.pill.custom { background: rgba(173, 122, 255, 0.14); color: #eadcff; border-color: rgba(173, 122, 255, 0.28); }
.pill.app { background: rgba(45, 220, 139, 0.12); color: #cdfbe0; border-color: rgba(45, 220, 139, 0.24); }

.action-btn {
  background: rgba(255, 255, 255, 0.03);
  color: #eef4f8;
  border: 1px solid rgba(120, 145, 171, 0.18);
  border-radius: 999px;
  padding: 10px 14px;
  margin-right: 8px;
}

.action-btn.primary {
  background: linear-gradient(145deg, rgba(76, 201, 240, 0.95), rgba(31, 156, 197, 0.92));
  color: #08111a;
  border-color: transparent;
  font-weight: 800;
}

.action-btn:checked {
  background: rgba(76, 201, 240, 0.16);
  border-color: rgba(76, 201, 240, 0.42);
  color: #d7f8ff;
}

.danger {
  border-color: rgba(255, 100, 112, 0.24);
  color: #ffd5d8;
  background: rgba(255, 100, 112, 0.10);
}

.detail-title {
  font-size: 20px;
  font-weight: 900;
}

.detail-status {
  padding: 7px 11px;
  border-radius: 999px;
  letter-spacing: 0.08em;
  font-size: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #93a7b8;
}

.detail-status.active { background: rgba(45, 220, 139, 0.12); color: #cdfbe0; border-color: rgba(45, 220, 139, 0.24); }
.detail-status.failed { background: rgba(255, 100, 112, 0.12); color: #ffd5d8; border-color: rgba(255, 100, 112, 0.24); }

.warning-note {
  color: #ffb3ba;
  font-size: 12px;
  margin-top: 4px;
}

.entry-error {
  border: 1px solid rgba(255, 100, 112, 0.75);
  box-shadow: 0 0 0 1px rgba(255, 100, 112, 0.25);
}

.nested-list {
  padding: 8px 0 8px 14px;
  border-left: 2px solid rgba(76, 201, 240, 0.28);
  border-radius: 6px;
}

.nested-list.child {
  margin-left: 18px;
  border-left-color: rgba(45, 220, 139, 0.32);
}

.nested-header {
  margin-bottom: 6px;
}

.nested-row {
  padding: 8px;
  margin: 4px 0 4px 10px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(120, 145, 171, 0.14);
  border-radius: 6px;
}

"""


class MainWindow:
    def __init__(self) -> None:
        self.window: Gtk.ApplicationWindow | None = None
        self.backend = SystemdBackend()
        self.services = self.backend.list_services()
        self.favorite_names = self._load_favorite_names()
        if not self.favorite_names:
            self.favorite_names = {svc.name for svc in self.services if svc.favorite}
        self.filtered: list[ServiceUnit] = list(self.services)
        self.selected: ServiceUnit = self.services[0] if self.services else self._empty_service()
        self.search_text = ""
        self.show_favorites_only = False
        self.service_rows: dict[str, Gtk.ListBoxRow] = {}
        self.property_entries: dict[str, Gtk.Entry] = {}
        self.create_entries: dict[str, Gtk.Entry] = {}
        self.create_execstart_entry: Gtk.Entry | None = None
        self.extra_properties: list[tuple[str, str]] = []
        self.extra_rows: list[tuple[Gtk.Entry, Gtk.Entry]] = []
        self.environment_rows: list[tuple[Gtk.Entry, Gtk.Entry]] = []
        self.environment_path_entries: list[Gtk.Entry] = []
        self.environment_path_block: Gtk.Widget | None = None
        self.environment_path_rows_box: Gtk.Box | None = None
        self.properties: dict[str, str] = {}
        self.create_mode = False
        self.editor_execstart_entry: Gtk.Entry | None = None
        self.preferences = self._load_preferences()
        self._ui_ready = False

    def _favorites_path(self) -> Path:
        return Path.home() / ".config" / "sysd_ui" / "favorites.json"

    def _preferences_path(self) -> Path:
        return Path.home() / ".config" / "sysd_ui" / "preferences.json"

    def _load_favorite_names(self) -> set[str]:
        try:
            data = json.loads(self._favorites_path().read_text(encoding="utf-8"))
        except Exception:
            return set()
        if isinstance(data, list):
            return {str(item) for item in data if isinstance(item, str)}
        return set()

    def _save_favorite_names(self) -> None:
        path = self._favorites_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(sorted(self.favorite_names), indent=2), encoding="utf-8")
        except Exception:
            pass

    def _default_preferences(self) -> dict[str, object]:
        return {
            "show_favorites_only": False,
            "search_text": "",
            "paned_position": 460,
            "window_width": 1400,
            "window_height": 900,
            "notebook_page": 0,
        }

    def _load_preferences(self) -> dict[str, object]:
        prefs = self._default_preferences()
        try:
            data = json.loads(self._preferences_path().read_text(encoding="utf-8"))
        except Exception:
            return prefs
        if isinstance(data, dict):
            prefs["show_favorites_only"] = bool(data.get("show_favorites_only", prefs["show_favorites_only"]))
            prefs["search_text"] = str(data.get("search_text", prefs["search_text"]))
            prefs["paned_position"] = int(data.get("paned_position", prefs["paned_position"]))
            prefs["window_width"] = int(data.get("window_width", prefs["window_width"]))
            prefs["window_height"] = int(data.get("window_height", prefs["window_height"]))
            prefs["notebook_page"] = int(data.get("notebook_page", prefs["notebook_page"]))
        return prefs

    def _save_preferences(self) -> None:
        path = self._preferences_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._current_preferences(), indent=2), encoding="utf-8")
        except Exception:
            pass

    def _current_preferences(self) -> dict[str, object]:
        width = 1400
        height = 900
        if self.window is not None:
            width = max(1, int(self.window.get_allocated_width()))
            height = max(1, int(self.window.get_allocated_height()))
        paned_position = 460
        if hasattr(self, "main_paned"):
            try:
                paned_position = int(self.main_paned.get_position())
            except Exception:
                pass
        notebook_page = 0
        if hasattr(self, "notebook"):
            try:
                notebook_page = int(self.notebook.get_current_page())
            except Exception:
                pass
        return {
            "show_favorites_only": bool(self.show_favorites_only),
            "search_text": self.search_text,
            "paned_position": paned_position,
            "window_width": width,
            "window_height": height,
            "notebook_page": notebook_page,
        }

    def build(self, app: Gtk.Application) -> Gtk.ApplicationWindow:
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("sysd_ui")
        self._set_initial_window_size()

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("shell")
        self.window.add(root)

        header = Gtk.HeaderBar()
        header.set_title("sysd_ui")
        header.set_subtitle("systemd services control room")
        header.set_show_close_button(True)
        self.window.set_titlebar(header)

        header_pack = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header_pack.get_style_context().add_class("brand")
        title = Gtk.Label(label="sysd_ui")
        title.get_style_context().add_class("brand-title")
        title.set_xalign(0)
        subtitle = Gtk.Label(label="native GTK systemd service manager")
        subtitle.get_style_context().add_class("brand-subtitle")
        subtitle.set_xalign(0)
        header_pack.pack_start(title, False, False, 0)
        header_pack.pack_start(subtitle, False, False, 0)
        header.set_custom_title(header_pack)

        reload_btn = Gtk.Button.new_with_label("Daemon reload")
        reload_btn.connect("clicked", self._on_reload_clicked)
        header.pack_end(reload_btn)

        create_btn = Gtk.Button.new_with_label("New service")
        create_btn.connect("clicked", self._on_create_service_clicked)
        header.pack_end(create_btn)

        main = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        main.set_wide_handle(True)
        main.set_position(int(self.preferences.get("paned_position", 460)))
        self.main_paned = main
        main.connect("notify::position", self._on_paned_position_changed)
        root.pack_start(main, True, True, 0)

        left = self._build_left_panel()
        main.pack1(left, resize=False, shrink=False)
        right = self._build_detail_panel()
        main.pack2(right, resize=True, shrink=True)

        self._ui_ready = True
        self._apply_saved_preferences()
        self._refresh_from_backend()
        self.window.show_all()
        self.window.connect("configure-event", self._on_window_configure_event)
        self.window.connect("destroy", self._on_window_destroy)
        GLib.idle_add(self._apply_initial_geometry)
        return self.window

    def _set_initial_window_size(self) -> None:
        if self.window is None:
            return
        width, height = 1400, 900
        width = int(self.preferences.get("window_width", width))
        height = int(self.preferences.get("window_height", height))
        self._initial_window_geometry = (0, 0, width, height)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            monitor = screen.get_primary_monitor()
            if monitor >= 0:
                geometry = screen.get_monitor_workarea(monitor)
                margin = 64
                width = max(960, min(width, geometry.width - margin))
                height = max(720, min(height, geometry.height - margin))
                self._initial_window_geometry = (geometry.x + 32, geometry.y + 32, width, height)
        self.window.set_default_size(width, height)
        self.window.set_position(Gtk.WindowPosition.CENTER)

    def _apply_saved_preferences(self) -> None:
        self.show_favorites_only = bool(self.preferences.get("show_favorites_only", False))
        if hasattr(self, "favorites_only_toggle"):
            self.favorites_only_toggle.set_active(self.show_favorites_only)
        search_text = str(self.preferences.get("search_text", ""))
        if hasattr(self, "search_entry"):
            self.search_entry.set_text(search_text)
        if hasattr(self, "notebook"):
            try:
                self.notebook.set_current_page(int(self.preferences.get("notebook_page", 0)))
            except Exception:
                self.notebook.set_current_page(0)

    def _on_paned_position_changed(self, _widget: Gtk.Paned, _param: object) -> None:
        if not self._ui_ready:
            return
        self._save_preferences()

    def _on_window_configure_event(self, _widget: Gtk.Window, event: Gdk.EventConfigure) -> bool:
        if not self._ui_ready:
            return False
        try:
            self.preferences["window_width"] = int(event.width)
            self.preferences["window_height"] = int(event.height)
            self._save_preferences()
        except Exception:
            pass
        return False

    def _on_window_destroy(self, _widget: Gtk.Widget) -> None:
        self._save_preferences()

    def _apply_initial_geometry(self) -> bool:
        if self.window is None:
            return False
        x, y, width, height = getattr(self, "_initial_window_geometry", (0, 0, 1400, 900))
        self.window.unmaximize()
        self.window.resize(width, height)
        self.window.move(x, y)
        return False

    def _build_left_panel(self) -> Gtk.Widget:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        panel.set_border_width(16)
        panel.set_size_request(400, -1)

        host = Gtk.Frame()
        host.get_style_context().add_class("panel")
        host_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        host_box.set_border_width(14)
        host.add(host_box)

        host_box.pack_start(self._section_label("Host"), False, False, 0)
        host_box.pack_start(self._host_block(), False, False, 0)
        panel.pack_start(host, False, False, 0)

        favorites = Gtk.Frame()
        favorites.get_style_context().add_class("panel")
        favorites_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        favorites_box.set_border_width(14)
        favorites.add(favorites_box)
        favorites_box.pack_start(self._section_label("Browse"), False, False, 0)

        self.favorites_only_toggle = Gtk.CheckButton(label="Favorites only")
        self.favorites_only_toggle.set_active(False)
        self.favorites_only_toggle.connect("toggled", self._on_favorites_only_toggled)
        favorites_box.pack_start(self.favorites_only_toggle, False, False, 0)
        panel.pack_start(favorites, False, False, 0)

        list_frame = Gtk.Frame()
        list_frame.get_style_context().add_class("panel")
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        list_box.set_border_width(14)
        list_frame.add(list_box)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search services, descriptions, paths, tags")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        list_box.pack_start(self.search_entry, False, False, 0)
        list_box.pack_start(self._section_label("Units"), False, False, 0)
        list_frame.set_vexpand(True)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_shadow_type(Gtk.ShadowType.NONE)
        scroller.set_min_content_width(400)
        scroller.set_vexpand(True)

        self.service_list = Gtk.ListBox()
        self.service_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.service_list.connect("row-selected", self._on_service_selected)
        scroller.add(self.service_list)
        list_box.pack_start(scroller, True, True, 0)
        panel.pack_start(list_frame, True, True, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_shadow_type(Gtk.ShadowType.NONE)
        scroller.set_hexpand(False)
        scroller.set_vexpand(True)
        scroller.set_min_content_width(400)
        scroller.add(panel)
        return scroller

    def _build_detail_panel(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_border_width(16)
        outer.set_hexpand(True)
        outer.set_vexpand(True)

        summary = Gtk.Frame()
        summary.get_style_context().add_class("panel")
        self.summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.summary_box.set_border_width(16)
        summary.add(self.summary_box)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top.set_halign(Gtk.Align.FILL)
        self.detail_title = Gtk.Label(label="")
        self.detail_title.get_style_context().add_class("detail-title")
        self.detail_title.set_xalign(0)
        self.detail_title.set_selectable(True)
        self.detail_status = Gtk.Label(label="")
        self.detail_status.get_style_context().add_class("detail-status")
        top.pack_start(self.detail_title, True, True, 0)
        top.pack_start(self.detail_status, False, False, 0)
        self.summary_box.pack_start(top, False, False, 0)

        self.create_summary_warning = Gtk.Label(label="")
        self.create_summary_warning.set_xalign(0)
        self.create_summary_warning.set_line_wrap(True)
        self.create_summary_warning.get_style_context().add_class("warning-note")
        self.summary_box.pack_start(self.create_summary_warning, False, False, 0)

        self.detail_desc = Gtk.Label(label="")
        self.detail_desc.set_xalign(0)
        self.detail_desc.set_line_wrap(True)
        self.detail_desc.get_style_context().add_class("muted")
        self.summary_box.pack_start(self.detail_desc, False, False, 0)
        self.create_summary_warning.set_visible(False)

        self.summary_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.summary_actions.set_halign(Gtk.Align.START)
        self.summary_actions.set_hexpand(True)
        self.summary_box.pack_start(self.summary_actions, False, False, 0)

        outer.pack_start(summary, False, False, 0)

        notebook = Gtk.Notebook()
        notebook.set_scrollable(True)
        notebook.set_tab_pos(Gtk.PositionType.TOP)
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        self.notebook = notebook
        notebook.connect("switch-page", self._on_notebook_switch_page)

        editor = Gtk.Frame()
        editor.get_style_context().add_class("panel")
        editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        editor_box.set_border_width(16)
        editor.add(editor_box)
        editor_box.pack_start(self._section_label("Editable properties"), False, False, 0)

        self.editor_grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        editor_box.pack_start(self.editor_grid, False, False, 0)
        self.editor_execstart_warning = Gtk.Label(label="")
        self.editor_execstart_warning.set_xalign(0)
        self.editor_execstart_warning.set_line_wrap(True)
        self.editor_execstart_warning.get_style_context().add_class("warning-note")

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.save_btn = Gtk.Button(label="Save changes")
        self.save_btn.get_style_context().add_class("primary")
        self.save_btn.connect("clicked", self._on_save_unit_clicked)
        self.editor_backup_btn = Gtk.Button(label="Backup unit")
        self.editor_backup_btn.connect("clicked", self._on_backup_unit_clicked)
        self.editor_restore_btn = Gtk.Button(label="Restore backup")
        self.editor_restore_btn.get_style_context().add_class("danger")
        self.editor_restore_btn.connect("clicked", self._on_restore_backup_clicked)
        save_row.pack_start(self.save_btn, False, False, 0)
        save_row.pack_start(self.editor_backup_btn, False, False, 0)
        save_row.pack_start(self.editor_restore_btn, False, False, 0)
        editor_box.pack_start(save_row, False, False, 0)

        info = Gtk.Frame()
        info.get_style_context().add_class("panel")
        self.info_grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        self.info_grid.set_border_width(16)
        info.add(self.info_grid)

        actions = Gtk.Frame()
        actions.get_style_context().add_class("panel")
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        action_box.set_border_width(16)
        actions.add(action_box)
        action_box.pack_start(self._section_label("Actions"), False, False, 0)
        self.action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.action_row.set_hexpand(True)
        action_box.pack_start(self.action_row, False, False, 0)

        deps = Gtk.Frame()
        deps.get_style_context().add_class("panel")
        dep_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        dep_box.set_border_width(16)
        deps.add(dep_box)
        dep_box.pack_start(self._section_label("Dependencies"), False, False, 0)
        self.dep_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        dep_box.pack_start(self.dep_list, False, False, 0)

        journal = Gtk.Frame()
        journal.get_style_context().add_class("panel")
        journal_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        journal_box.set_border_width(16)
        journal.add(journal_box)
        journal_box.pack_start(self._section_label("Recent journal"), False, False, 0)
        self.journal_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        journal_box.pack_start(self.journal_list, False, False, 0)

        def wrap_page(widget: Gtk.Widget) -> Gtk.ScrolledWindow:
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_shadow_type(Gtk.ShadowType.NONE)
            scroller.set_hexpand(True)
            scroller.set_vexpand(True)
            scroller.add(widget)
            return scroller

        notebook.append_page(wrap_page(editor), Gtk.Label(label="Properties"))

        status_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        status_page.pack_start(info, False, False, 0)
        status_page.pack_start(actions, False, False, 0)
        status_page.pack_start(deps, False, False, 0)
        notebook.append_page(wrap_page(status_page), Gtk.Label(label="Status"))

        notebook.append_page(wrap_page(journal), Gtk.Label(label="Journal"))
        outer.pack_start(notebook, True, True, 0)
        return outer

    def _section_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_xalign(0)
        label.get_style_context().add_class("sidebar-title")
        return label

    def _host_block(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.host_name = Gtk.Label(label="devbox-01")
        self.host_name.set_xalign(0)
        self.host_name.set_markup("<b>devbox-01</b>")
        self.host_meta = Gtk.Label(label="Ubuntu 24.04 LTS · PID 1: systemd 255")
        self.host_meta.set_xalign(0)
        self.host_meta.get_style_context().add_class("muted")
        self.host_meta.set_ellipsize(Pango.EllipsizeMode.END)
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        self.status_label.get_style_context().add_class("meta")
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.pack_start(self.host_name, False, False, 0)
        box.pack_start(self.host_meta, False, False, 0)
        box.pack_start(self.status_label, False, False, 0)
        return box

    def _set_directive_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        for directive in sorted(dict.fromkeys(SYSTEMD_DIRECTIVES), key=str.lower):
            model.append([directive])
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(0)
        completion.set_match_func(self._completion_match_func)
        entry.set_completion(completion)
        entry.connect("focus-in-event", self._on_completion_focus)

    def _set_command_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        for command in command_suggestions():
            model.append([command])
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(False)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(1)
        completion.set_match_func(self._completion_match_func)
        entry.set_completion(completion)

    def _set_execstart_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(1)

        def refresh() -> None:
            model.clear()
            text = entry.get_text().strip()
            token = text
            if text:
                try:
                    token = shlex.split(text, posix=True)[0]
                except ValueError:
                    token = text.split()[0]
            suggestions: list[str]
            if token.startswith(("/", ".", "~")):
                suggestions = path_suggestions(token)
            else:
                commands = command_suggestions()
                if token:
                    commands = [item for item in commands if item.startswith(token)]
                suggestions = commands[:200]
            for item in suggestions:
                model.append([item])

        entry.set_completion(completion)
        self._enable_file_drop(entry, replace_first_token=True)
        entry.connect("changed", lambda *_args: refresh())
        entry.connect("focus-in-event", lambda *_args: (refresh(), False)[1])
        refresh()

    def _set_target_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        for target in target_suggestions():
            model.append([target])
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(1)
        completion.set_match_func(self._completion_match_func)
        entry.set_completion(completion)

    def _set_path_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(1)

        def refresh() -> None:
            model.clear()
            text = entry.get_text().strip()
            suggestions = path_suggestions(text)
            for item in suggestions:
                model.append([item])

        entry.set_completion(completion)
        self._enable_file_drop(entry)
        entry.connect("changed", lambda *_args: refresh())
        entry.connect("focus-in-event", lambda *_args: (refresh(), False)[1])
        refresh()

    def _enable_file_drop(self, entry: Gtk.Entry, *, replace_first_token: bool = False) -> None:
        entry._replace_first_drop_token = replace_first_token  # type: ignore[attr-defined]
        entry.drag_dest_set(Gtk.DestDefaults.ALL, URI_LIST_TARGET, Gdk.DragAction.COPY)
        entry.connect("drag-data-received", self._on_entry_file_dropped)

    def _on_entry_file_dropped(
        self,
        entry: Gtk.Entry,
        _context: Gdk.DragContext,
        _x: int,
        _y: int,
        selection: Gtk.SelectionData,
        _info: int,
        _time: int,
    ) -> None:
        uris = selection.get_uris()
        if not uris:
            return
        file_path = self._file_path_from_uri(uris[0])
        if not file_path:
            self._status_message("Dropped item is not a local file")
            return
        text = entry.get_text()
        if getattr(entry, "_replace_first_drop_token", False) and text.strip():
            try:
                first = shlex.split(text, posix=True)[0]
            except ValueError:
                first = text.split()[0]
            entry.set_text(text.replace(first, file_path, 1))
            self._status_message(f"Dropped file: {file_path}")
            return
        entry.set_text(file_path)
        self._status_message(f"Dropped file: {file_path}")

    def _file_path_from_uri(self, uri: str) -> str:
        try:
            return GLib.filename_from_uri(uri)[0] or ""
        except Exception:
            return ""

    def _set_user_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        for user in user_suggestions():
            model.append([user])
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(1)
        completion.set_match_func(self._completion_match_func)
        entry.set_completion(completion)

    def _set_group_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        for group in group_suggestions():
            model.append([group])
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(1)
        completion.set_match_func(self._completion_match_func)
        entry.set_completion(completion)

    def _set_environment_key_completion(self, entry: Gtk.Entry) -> None:
        model = Gtk.ListStore(str)
        for key in sorted(dict.fromkeys(ENVIRONMENT_KEYS), key=str.lower):
            model.append([key])
        completion = Gtk.EntryCompletion()
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_popup_completion(True)
        completion.set_popup_single_match(True)
        completion.set_popup_set_width(True)
        completion.set_minimum_key_length(1)
        completion.set_match_func(self._completion_match_func)
        entry.set_completion(completion)

    def _completion_match_func(
        self,
        completion: Gtk.EntryCompletion,
        key: str,
        iter_: Gtk.TreeIter,
        _data: object | None = None,
    ) -> bool:
        model = completion.get_model()
        if model is None:
            return False
        candidate = str(model.get_value(iter_, 0))
        key = key.lower()
        candidate = candidate.lower()
        if not key:
            return True
        return candidate.startswith(key)

    def _on_completion_focus(self, entry: Gtk.Entry, _event: Gdk.EventFocus) -> bool:
        GLib.idle_add(self._complete_entry, entry)
        return False

    def _complete_entry(self, entry: Gtk.Entry) -> bool:
        completion = entry.get_completion()
        if completion is not None:
            completion.complete()
        return False

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        if not self._ui_ready:
            return
        self.search_text = entry.get_text().strip().lower()
        self._save_preferences()
        self._refresh_list()

    def _on_target_clicked(self, _button: Gtk.Button, target: str) -> None:
        self._journal(self.selected, f"Viewing target {target}")

    def _on_favorites_only_toggled(self, button: Gtk.CheckButton) -> None:
        if not self._ui_ready:
            return
        self.show_favorites_only = button.get_active()
        self._save_preferences()
        self._refresh_list()

    def _on_notebook_switch_page(self, _notebook: Gtk.Notebook, _page: Gtk.Widget, page_num: int) -> None:
        if not self._ui_ready:
            return
        self.preferences["notebook_page"] = int(page_num)
        self._save_preferences()

    def _on_service_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if not self._ui_ready:
            return
        if row is None:
            return
        service = getattr(row, "service", None)
        if isinstance(service, ServiceUnit):
            if service.name != self.selected.name:
                self.extra_properties = []
            self.selected = service
            self._refresh_detail()

    def _refresh_list(self) -> None:
        self.filtered = self._filtered_services()
        self.filtered.sort(key=lambda svc: (0 if svc.favorite else 1, svc.name))

        if self.filtered and self.selected.name not in {svc.name for svc in self.filtered}:
            self.selected = self.filtered[0]
        elif not self.filtered:
            self.selected = self.services[0]

        if hasattr(self, "service_list"):
            for child in self.service_list.get_children():
                self.service_list.remove(child)

            self.service_rows.clear()
            for service in self.filtered:
                row = self._service_row(service)
                self.service_rows[service.name] = row
                self.service_list.add(row)
                if service.name == self.selected.name:
                    self.service_list.select_row(row)
            self.service_list.show_all()

        self._refresh_detail()

    def _refresh_from_backend(self) -> None:
        LOGGER.debug("refreshing services from backend")
        previous_name = self.selected.name if hasattr(self, "selected") else ""
        self.services = self.backend.list_services()
        for service in self.services:
            service.favorite = service.name in self.favorite_names
        if not self.services:
            self.services = [self._empty_service()]
        if self.selected.name not in {svc.name for svc in self.services}:
            self.selected = self.services[0]
        if self.selected.name != previous_name:
            self.extra_properties = []
        self._refresh_list()

    def _refresh_editor(self) -> None:
        if not hasattr(self, "editor_grid"):
            return

        for child in self.editor_grid.get_children():
            self.editor_grid.remove(child)
        self.property_entries.clear()
        self._update_editor_toolbar_state()

        if self.create_mode:
            create_placeholders = self._create_field_placeholders()
            rows = [("Name", "name.service")] + [(key, create_placeholders.get(key, "")) for key in COMMON_FIELDS]
            self.create_entries = {}
            editor = self._build_unit_properties_editor(rows, create_mode=True)
            self.editor_grid.attach(editor, 0, 0, 1, 1)
            self._update_create_execstart_warning()
            self.editor_grid.show_all()
            return

        rows = [(row.key, row.value) for row in ordered_rows(self.properties)]
        editor = self._build_unit_properties_editor(rows, create_mode=False)
        self.editor_grid.attach(editor, 0, 0, 1, 1)
        self._update_editor_execstart_warning()
        self.editor_grid.show_all()

    def _build_unit_properties_editor(self, rows: list[tuple[str, str]], *, create_mode: bool) -> Gtk.Widget:
        add_btn = Gtk.Button(label="Add property")
        add_btn.set_tooltip_text("Add a user-defined systemd directive to Unit properties")
        add_btn.connect("clicked", self._on_add_property)
        panel, body = self._foldable_list("Unit properties", [add_btn], level=0)
        self.extra_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.extra_list.set_hexpand(True)
        body.pack_start(self.extra_list, False, False, 0)
        self._refresh_extra_properties()

        for key, value in rows:
            if key == "Environment":
                body.pack_start(
                    self._property_editor_row(
                        key,
                        self._build_environment_editor("" if create_mode else value),
                        clear_callback=self._on_clear_environment_property,
                    ),
                    False,
                    False,
                    0,
                )
                continue
            placeholder = value if create_mode else ""
            entry = self._build_property_entry(key, "" if create_mode else value, placeholder, create_mode=create_mode)
            widget: Gtk.Widget = entry
            if key == "ExecStart":
                widget = self._wrap_execstart_entry(entry, create_mode=create_mode)
            body.pack_start(
                self._property_editor_row(
                    key,
                    widget,
                    clear_callback=lambda _button, item=entry: item.set_text(""),
                    removable=key != "Name",
                ),
                False,
                False,
                0,
            )

        return panel

    def _update_editor_toolbar_state(self) -> None:
        if not hasattr(self, "editor_backup_btn"):
            return
        is_create = self.create_mode
        has_path = bool(self._unit_save_path(self.selected)) and not is_create
        self.editor_backup_btn.set_sensitive(has_path)
        self.editor_restore_btn.set_sensitive(has_path)
        self.editor_backup_btn.set_tooltip_text("Copy the current unit file to /var/lib/sysd_ui/backups")
        self.editor_restore_btn.set_tooltip_text("Restore the saved backup over the current unit file")

    def _property_editor_row(self, name: str, widget: Gtk.Widget, *, clear_callback=None, removable: bool = True) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_hexpand(True)
        row.get_style_context().add_class("nested-row")
        label = Gtk.Label(label=name)
        label.set_xalign(0)
        label.set_yalign(0.5)
        label.set_width_chars(18)
        label.get_style_context().add_class("meta")
        row.pack_start(label, False, False, 0)
        row.pack_start(widget, True, True, 0)
        if removable:
            clear_btn = Gtk.Button(label="Remove property")
            clear_btn.set_tooltip_text("Clear this property. Empty properties are omitted when the unit is saved.")
            if clear_callback is not None:
                clear_btn.connect("clicked", clear_callback)
            row.pack_start(clear_btn, False, False, 0)
        return row

    def _build_property_entry(self, key: str, value: str, placeholder: str, *, create_mode: bool) -> Gtk.Entry:
        entry = Gtk.Entry()
        entry.set_text(value)
        entry.set_placeholder_text(placeholder)
        entry.set_hexpand(True)
        if key == "WantedBy":
            self._set_target_completion(entry)
        elif key in {"ExecStart", "ExecReload", "ExecStop"}:
            self._set_execstart_completion(entry)
        elif key in {"WorkingDirectory", "RootDirectory", "RootImage", "EnvironmentFile", "SourcePath", "RequiresMountsFor", "WantsMountsFor", "AssertPathExists", "AssertPathIsDirectory", "AssertPathIsSymbolicLink", "ConditionPathExists", "ConditionPathIsDirectory", "ConditionPathIsSymbolicLink"}:
            self._set_path_completion(entry)
        elif key == "User":
            self._set_user_completion(entry)
        elif key == "Group":
            self._set_group_completion(entry)

        if create_mode:
            self.create_entries[key] = entry
        else:
            self.property_entries[key] = entry
        return entry

    def _wrap_execstart_entry(self, entry: Gtk.Entry, *, create_mode: bool) -> Gtk.Widget:
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        wrap.set_hexpand(True)
        wrap.pack_start(entry, False, False, 0)
        if create_mode:
            self.create_execstart_entry = entry
            self.create_execstart_warning = Gtk.Label(label="")
            self.create_execstart_warning.set_xalign(0)
            self.create_execstart_warning.set_line_wrap(True)
            self.create_execstart_warning.get_style_context().add_class("warning-note")
            wrap.pack_start(self.create_execstart_warning, False, False, 0)
            entry.connect("changed", self._on_create_execstart_changed)
            return wrap

        self.editor_execstart_entry = entry
        parent = self.editor_execstart_warning.get_parent()
        if isinstance(parent, Gtk.Container):
            parent.remove(self.editor_execstart_warning)
        wrap.pack_start(self.editor_execstart_warning, False, False, 0)
        entry.connect("changed", self._on_editor_execstart_changed)
        return wrap

    def _build_environment_editor(self, raw: str) -> Gtk.Widget:
        add_menu = Gtk.MenuButton.new()
        add_menu.set_label("Add")
        add_menu.set_tooltip_text("Add an environment variable")
        add_popover = Gtk.Popover()
        add_menu.set_popover(add_popover)
        add_options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        add_options.set_border_width(8)
        add_popover.add(add_options)
        add_text_btn = Gtk.Button(label="Text variable")
        add_text_btn.set_tooltip_text("Add a regular KEY=value environment variable")
        add_text_btn.connect("clicked", self._on_add_environment_from_menu, add_popover)
        add_path_btn = Gtk.Button(label="PATH variable")
        add_path_btn.set_tooltip_text("Add PATH with one directory per row")
        add_path_btn.connect("clicked", self._on_add_path_environment_from_menu, add_popover)
        add_options.pack_start(add_text_btn, False, False, 0)
        add_options.pack_start(add_path_btn, False, False, 0)
        add_options.show_all()

        outer, body = self._foldable_list("Variables", [add_menu], level=1)
        self.environment_box = body
        self.environment_rows = []
        self.environment_path_entries = []
        self.environment_path_block = None
        self.environment_path_rows_box = None

        parsed_entries = self._parse_environment_text(raw)
        for key, value in parsed_entries:
            if key == "PATH":
                body.pack_start(self._ensure_path_environment_block(value), False, False, 0)
                continue
            body.pack_start(self._environment_row(key, value), False, False, 0)
        return outer

    def _foldable_list(self, title: str, actions: list[Gtk.Widget], *, level: int = 0) -> tuple[Gtk.Box, Gtk.Box]:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        container.set_hexpand(True)
        container.get_style_context().add_class("nested-list")
        if level > 0:
            container.get_style_context().add_class("child")
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_hexpand(True)
        header.get_style_context().add_class("nested-header")
        toggle = Gtk.ToggleButton(label=title)
        toggle.set_active(True)
        toggle.set_tooltip_text(f"Show or hide {title}")
        toggle.get_style_context().add_class("meta")
        header.pack_start(toggle, False, False, 0)
        header.pack_start(Gtk.Label(label=""), True, True, 0)
        for action in actions:
            header.pack_start(action, False, False, 0)
        container.pack_start(header, False, False, 0)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_hexpand(True)
        container.pack_start(body, False, False, 0)
        toggle.connect("toggled", lambda button: body.set_visible(button.get_active()))
        return container, body

    def _ensure_path_environment_block(self, raw: str) -> Gtk.Widget:
        if self.environment_path_block is not None and self.environment_path_rows_box is not None:
            for child in self.environment_path_rows_box.get_children():
                self.environment_path_rows_box.remove(child)
            parts = [part for part in raw.split(":") if part.strip()]
            for part in parts:
                self.environment_path_rows_box.pack_start(self._single_path_row(part, self.environment_path_rows_box), False, False, 0)
            self.environment_path_rows_box.show_all()
            return self.environment_path_block
        block = self._path_environment_row(raw)
        self.environment_path_block = block
        return block

    def _path_environment_row(self, raw: str) -> Gtk.Widget:
        add_btn = Gtk.Button(label="Add entry")
        add_btn.set_tooltip_text("Add a directory to PATH")
        add_btn.connect("clicked", self._on_add_path_row_for_block)
        remove_btn = Gtk.Button(label="Remove variable")
        remove_btn.set_tooltip_text("Remove the PATH environment variable")
        outer, rows_box = self._foldable_list("PATH", [add_btn, remove_btn], level=2)
        remove_btn.connect("clicked", self._on_remove_path_block, outer)

        self.environment_path_rows_box = rows_box

        parts = [part for part in raw.split(":") if part.strip()]
        for part in parts:
            rows_box.pack_start(self._single_path_row(part, rows_box), False, False, 0)

        return outer

    def _single_path_row(self, value: str, rows_box: Gtk.Box) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.get_style_context().add_class("nested-row")
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        wrap.set_hexpand(True)
        entry = Gtk.Entry()
        entry.set_text(value)
        entry.set_hexpand(True)
        self._set_path_completion(entry)
        check_label = Gtk.Label(label="")
        check_label.set_xalign(0)
        check_label.set_line_wrap(True)
        check_label.get_style_context().add_class("warning-note")

        def refresh_check(_entry: Gtk.Entry | None = None) -> None:
            text = entry.get_text().strip()
            if not text:
                check_label.set_text("")
                check_label.set_visible(False)
                entry.get_style_context().remove_class("entry-error")
                return
            expanded = Path(text).expanduser()
            if not expanded.exists():
                check_label.set_text(f"Path does not exist: {expanded}")
                check_label.set_visible(True)
                entry.get_style_context().add_class("entry-error")
                return
            if expanded.is_dir():
                check_label.set_text(f"Directory: {expanded}")
                check_label.set_visible(True)
                entry.get_style_context().remove_class("entry-error")
                return
            check_label.set_text(f"File exists: {expanded}")
            check_label.set_visible(True)
            entry.get_style_context().remove_class("entry-error")

        entry.connect("changed", refresh_check)
        refresh_check()
        remove_btn = Gtk.Button(label="Remove entry")
        remove_btn.set_tooltip_text("Remove this PATH entry")
        remove_btn.connect("clicked", self._on_remove_path_row, row, rows_box, entry)
        wrap.pack_start(entry, False, False, 0)
        wrap.pack_start(check_label, False, False, 0)
        row.pack_start(wrap, True, True, 0)
        row.pack_start(remove_btn, False, False, 0)
        self.environment_path_entries.append(entry)
        return row

    def _parse_environment_text(self, raw: str) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []
        for line in raw.splitlines():
            chunk = line.strip()
            if not chunk:
                continue
            try:
                tokens = shlex.split(chunk)
            except ValueError:
                tokens = [chunk]
            for token in tokens:
                if "=" in token:
                    key, value = token.split("=", 1)
                else:
                    key, value = token, ""
                entries.append((key, value))
        return entries

    def _environment_row(self, key: str, value: str) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.get_style_context().add_class("nested-row")
        key_entry = Gtk.Entry()
        key_entry.set_text(key)
        key_entry.set_placeholder_text("Variable name")
        key_entry.set_width_chars(16)
        self._set_environment_key_completion(key_entry)
        value_entry = Gtk.Entry()
        value_entry.set_text(value)
        value_entry.set_placeholder_text("Variable value")
        value_entry.set_hexpand(True)
        self._apply_extra_value_completion(key_entry, value_entry)
        key_entry.connect("changed", self._on_extra_key_changed, value_entry)
        key_entry.connect("changed", self._on_environment_key_changed, row, value_entry)
        remove_btn = Gtk.Button(label="Remove variable")
        remove_btn.set_tooltip_text("Remove this environment variable")
        remove_btn.connect("clicked", self._on_remove_environment_row, row)
        row.pack_start(key_entry, False, False, 0)
        row.pack_start(value_entry, True, True, 0)
        row.pack_start(remove_btn, False, False, 0)
        self.environment_rows.append((key_entry, value_entry))
        return row

    def _on_environment_key_changed(self, key_entry: Gtk.Entry, row: Gtk.Widget, value_entry: Gtk.Entry) -> None:
        if key_entry.get_text().strip() != "PATH":
            return
        value = value_entry.get_text().strip()
        try:
            self.environment_rows.remove((key_entry, value_entry))
        except ValueError:
            pass
        path_block = self._ensure_path_environment_block(value)
        parent = row.get_parent()
        row.destroy()
        if isinstance(parent, Gtk.Box):
            if path_block.get_parent() is None:
                parent.pack_start(path_block, False, False, 0)
            parent.reorder_child(path_block, max(1, len(parent.get_children()) - 1))
            parent.show_all()
        self._status_message("PATH editor enabled")

    def _on_clear_environment_property(self, _button: Gtk.Button) -> None:
        if hasattr(self, "environment_box"):
            for child in self.environment_box.get_children():
                self.environment_box.remove(child)
            self.environment_box.show_all()
        self.environment_rows.clear()
        self.environment_path_entries.clear()
        self.environment_path_block = None
        self.environment_path_rows_box = None
        self._status_message("Environment property will be removed on save")

    def _refresh_extra_properties(self) -> None:
        if not hasattr(self, "extra_list"):
            return
        for child in self.extra_list.get_children():
            self.extra_list.remove(child)

        self.extra_rows.clear()
        for key, value in getattr(self, "extra_properties", []):
            self.extra_list.pack_start(self._unit_property_row(key, value), False, False, 0)
        self.extra_list.show_all()

    def _unit_property_row(self, key: str, value: str) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.get_style_context().add_class("nested-row")
        key_entry = Gtk.Entry()
        key_entry.set_text(key)
        key_entry.set_placeholder_text("Directive name")
        key_entry.set_width_chars(18)
        self._set_directive_completion(key_entry)
        value_entry = Gtk.Entry()
        value_entry.set_text(value)
        value_entry.set_placeholder_text("Directive value")
        value_entry.set_hexpand(True)
        self._apply_extra_value_completion(key_entry, value_entry)
        key_entry.connect("changed", self._on_extra_key_changed, value_entry)
        remove_btn = Gtk.Button(label="Remove property")
        remove_btn.set_tooltip_text("Remove this user-defined unit property from the saved output")
        remove_btn.connect("clicked", self._on_remove_extra_property, row, key_entry, value_entry)
        row.pack_start(key_entry, False, False, 0)
        row.pack_start(value_entry, True, True, 0)
        row.pack_start(remove_btn, False, False, 0)
        self.extra_rows.append((key_entry, value_entry))
        return row

    def _on_add_environment(self, _button: Gtk.Button) -> None:
        row = self._environment_row("", "")
        self.environment_box.pack_start(row, False, False, 0)
        self.environment_box.show_all()

    def _on_add_environment_from_menu(self, button: Gtk.Button, popover: Gtk.Popover) -> None:
        popover.popdown()
        self._on_add_environment(button)

    def _on_add_path_environment(self, _button: Gtk.Button) -> None:
        row = self._ensure_path_environment_block("")
        if row.get_parent() is None:
            self.environment_box.pack_start(row, False, False, 0)
        if self.environment_path_rows_box is not None and not self.environment_path_rows_box.get_children():
            self._on_add_path_row(_button, self.environment_path_rows_box)
        self.environment_box.show_all()

    def _on_add_path_environment_from_menu(self, button: Gtk.Button, popover: Gtk.Popover) -> None:
        popover.popdown()
        self._on_add_path_environment(button)

    def _collect_environment_text(self) -> str:
        env_lines = []
        for key_entry, value_entry in self.environment_rows:
            key = key_entry.get_text().strip()
            if not key:
                continue
            value = value_entry.get_text().strip()
            env_lines.append(f"{key}={value}")
        if self.environment_path_entries:
            paths = [entry.get_text().strip() for entry in self.environment_path_entries if entry.get_text().strip()]
            if paths:
                env_lines.append(f"PATH={':'.join(paths)}")
        return "\n".join(env_lines)

    def _on_add_path_row(self, _button: Gtk.Button, rows_box: Gtk.Box) -> None:
        row = self._single_path_row("", rows_box)
        rows_box.pack_start(row, False, False, 0)
        rows_box.show_all()

    def _on_add_path_row_for_block(self, button: Gtk.Button) -> None:
        if self.environment_path_rows_box is None:
            return
        self._on_add_path_row(button, self.environment_path_rows_box)

    def _on_remove_path_block(self, _button: Gtk.Button, block: Gtk.Widget) -> None:
        self.environment_path_rows_box = None
        self.environment_path_block = None
        self.environment_path_entries.clear()
        block.destroy()
        if hasattr(self, "environment_box"):
            self.environment_box.show_all()

    def _on_remove_path_row(self, _button: Gtk.Button, row: Gtk.Widget, _rows_box: Gtk.Box, entry: Gtk.Entry) -> None:
        try:
            self.environment_path_entries.remove(entry)
        except ValueError:
            pass
        row.destroy()
        _rows_box.show_all()
        if hasattr(self, "environment_box"):
            self.environment_box.show_all()

    def _on_editor_execstart_changed(self, _entry: Gtk.Entry) -> None:
        self._update_editor_execstart_warning()

    def _update_editor_execstart_warning(self) -> None:
        label = getattr(self, "editor_execstart_warning", None)
        entry = self.property_entries.get("ExecStart")
        if label is None or entry is None:
            return
        message = self._create_execstart_issue(entry.get_text().strip())
        label.set_text(message or "")
        label.set_visible(bool(message))
        if self.editor_execstart_entry is not None:
            ctx = self.editor_execstart_entry.get_style_context()
            if message:
                ctx.add_class("entry-error")
            else:
                ctx.remove_class("entry-error")

    def _apply_extra_value_completion(self, key_entry: Gtk.Entry, value_entry: Gtk.Entry) -> None:
        key = key_entry.get_text().strip()
        if key == "WantedBy":
            self._set_target_completion(value_entry)
        elif key == "ExecStart":
            self._set_execstart_completion(value_entry)
        elif key == "User":
            self._set_user_completion(value_entry)
        elif key == "Group":
            self._set_group_completion(value_entry)
        elif key in {"ExecReload", "ExecStop", "WorkingDirectory", "RootDirectory", "RootImage", "EnvironmentFile", "SourcePath", "RequiresMountsFor", "WantsMountsFor", "AssertPathExists", "AssertPathIsDirectory", "AssertPathIsSymbolicLink", "ConditionPathExists", "ConditionPathIsDirectory", "ConditionPathIsSymbolicLink"}:
            self._set_path_completion(value_entry)

    def _on_extra_key_changed(self, key_entry: Gtk.Entry, value_entry: Gtk.Entry) -> None:
        self._apply_extra_value_completion(key_entry, value_entry)

    def _on_remove_environment_row(self, _button: Gtk.Button, row: Gtk.Widget) -> None:
        if hasattr(self, "environment_rows"):
            children = row.get_children()
            if len(children) >= 2:
                key_entry = children[0]
                value_entry = children[1]
                if isinstance(key_entry, Gtk.Entry) and isinstance(value_entry, Gtk.Entry):
                    try:
                        self.environment_rows.remove((key_entry, value_entry))
                    except ValueError:
                        pass
        row.destroy()
        if hasattr(self, "environment_box"):
            self.environment_box.show_all()

    def _on_add_property(self, _button: Gtk.Button) -> None:
        if not hasattr(self, "extra_list"):
            self._status_message("Unit property editor is not ready")
            return
        LOGGER.info("add-property clicked")
        row = self._unit_property_row("", "")
        self.extra_list.pack_start(row, False, False, 0)
        self.extra_list.show_all()
        first = row.get_children()[0] if row.get_children() else None
        if isinstance(first, Gtk.Entry):
            first.grab_focus()
            GLib.idle_add(self._complete_entry, first)
        self._status_message("Property row added")

    def _on_remove_extra_property(self, _button: Gtk.Button, row: Gtk.Widget, key_entry: Gtk.Entry, value_entry: Gtk.Entry) -> None:
        try:
            self.extra_rows.remove((key_entry, value_entry))
        except ValueError:
            pass
        row.destroy()
        self.extra_list.show_all()

    def _on_save_unit_clicked(self, _button: Gtk.Button) -> None:
        try:
            fields = {key: entry.get_text() for key, entry in self.property_entries.items()}
            if hasattr(self, "environment_rows"):
                fields["Environment"] = self._collect_environment_text()
            extras = [(key_entry.get_text().strip(), value_entry.get_text().strip()) for key_entry, value_entry in self.extra_rows if key_entry.get_text().strip()]
            if "ExecStart" in fields:
                warning = self._create_execstart_issue(fields["ExecStart"].strip())
                if warning and not self._confirm_action("Service warning", f"{warning}\n\nContinue saving anyway?"):
                    self._status_message("Save cancelled")
                    return
            if self._is_vendor_unit(self.selected):
                if not self._confirm_action(
                    "Save vendor unit file",
                    f"This will modify the vendor unit file directly:\n{self._unit_save_path(self.selected)}\n\nA backup will be created first. Continue?",
                ):
                    self._status_message("Save cancelled")
                    return
                self.backend.save_vendor_unit(self.selected.name, self._unit_save_path(self.selected), fields, extras)
                self._status_message(f"Saved vendor unit for {self.selected.name}")
            elif self._can_save_unit(self.selected):
                self.backend.save_unit(self.selected.name, fields, extras)
                self._status_message(f"Saved unit for {self.selected.name}")
            else:
                raise BackendError(f"unit file path is unknown for {self.selected.name}")
            self._refresh_from_backend()
        except BackendError as exc:
            self._status_message(str(exc))

    def _on_backup_unit_clicked(self, _button: Gtk.Button) -> None:
        if self.create_mode:
            self._status_message("Create the service before backing it up")
            return
        try:
            path = self._unit_save_path(self.selected)
            if not path:
                raise BackendError(f"unit file path is unknown for {self.selected.name}")
            backup = self.backend.backup_unit_file(self.selected.name, path)
            self._status_message(f"Backup created: {backup}")
        except BackendError as exc:
            self._status_message(str(exc))

    def _on_restore_backup_clicked(self, _button: Gtk.Button) -> None:
        if self.create_mode:
            self._status_message("Create the service before restoring a backup")
            return
        try:
            path = self._unit_save_path(self.selected)
            if not path:
                raise BackendError(f"unit file path is unknown for {self.selected.name}")
            if not self._confirm_action(
                "Restore unit backup",
                f"Restore backup over this unit file?\n{path}",
            ):
                self._status_message("Restore cancelled")
                return
            backup = self.backend.restore_unit_backup(self.selected.name, path)
            self._status_message(f"Restored backup: {backup}")
            self._refresh_from_backend()
            refreshed = self.backend.refresh_service(self.selected.name)
            refreshed.favorite = refreshed.name in self.favorite_names
            self.selected = refreshed
            self._refresh_detail()
        except BackendError as exc:
            self._status_message(str(exc))

    def _filtered_services(self) -> list[ServiceUnit]:
        result: list[ServiceUnit] = []
        for service in self.services:
            haystack = " ".join(
                [
                    service.name,
                    service.description,
                    service.path,
                    service.target,
                    service.service_class,
                    " ".join(service.tags),
            ]
            ).lower()
            query_ok = not self.search_text or self.search_text in haystack
            favorite_ok = not self.show_favorites_only or service.favorite
            if query_ok and favorite_ok:
                result.append(service)
        return result

    def _service_row(self, service: ServiceUnit) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("service-row")
        row.service = service  # type: ignore[attr-defined]

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(12)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        name = Gtk.Label(label=service.name)
        name.set_xalign(0)
        name.get_style_context().add_class("service-name")
        desc = Gtk.Label(label=service.description)
        desc.set_xalign(0)
        desc.set_line_wrap(True)
        desc.get_style_context().add_class("service-desc")
        name_box.pack_start(name, False, False, 0)
        name_box.pack_start(desc, False, False, 0)
        top.pack_start(name_box, True, True, 0)

        badge = Gtk.Label(label=self._status_label(service))
        badge.get_style_context().add_class("pill")
        badge.get_style_context().add_class(service.status)
        top.pack_start(badge, False, False, 0)

        favorite_toggle = Gtk.CheckButton()
        favorite_toggle.set_active(service.favorite)
        favorite_toggle.set_tooltip_text("Pin service")
        favorite_toggle.connect("toggled", self._on_service_favorite_toggled, service.name)
        top.pack_end(favorite_toggle, False, False, 0)

        flags = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        flags.pack_start(self._pill(service.status), False, False, 0)
        flags.pack_start(self._pill("enabled" if service.enabled else "inactive"), False, False, 0)
        flags.pack_start(self._pill(service.load_state), False, False, 0)
        flags.pack_start(self._pill(service.service_class), False, False, 0)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        footer.pack_start(Gtk.Label(label=f"pid {service.pid} · {service.memory}"), False, False, 0)
        footer.pack_end(Gtk.Label(label=service.uptime), False, False, 0)

        box.pack_start(top, False, False, 0)
        box.pack_start(flags, False, False, 0)
        box.pack_start(footer, False, False, 0)
        row.add(box)
        row.connect("activate", self._on_row_activated)
        return row

    def _on_row_activated(self, row: Gtk.ListBoxRow) -> None:
        service = getattr(row, "service", None)
        if isinstance(service, ServiceUnit):
            self.selected = service
            self._refresh_detail()

    def _on_service_favorite_toggled(self, button: Gtk.CheckButton, name: str) -> None:
        service = next((svc for svc in self.services if svc.name == name), None)
        if service is None:
            return
        favorite = button.get_active()
        if favorite:
            self.favorite_names.add(name)
        else:
            self.favorite_names.discard(name)
        service.favorite = favorite
        self._save_favorite_names()
        self._refresh_from_backend()

    def _on_create_service_clicked(self, _button: Gtk.Button) -> None:
        if not hasattr(self, "notebook"):
            return
        LOGGER.info("create-service clicked")
        self.create_mode = True
        self._refresh_detail()
        self.notebook.set_current_page(0)
        if "Name" in self.create_entries:
            self.create_entries["Name"].grab_focus()
        self._status_message("Create service form opened")

    def _prepare_create_form(self) -> None:
        self.extra_properties = []
        for entry in self.create_entries.values():
            entry.set_text("")
        self._update_create_execstart_warning()

    def _create_field_placeholders(self) -> dict[str, str]:
        return {
            "Description": "optional description",
            "ExecStart": "/path/to/executable",
            "ExecReload": "",
            "ExecStop": "",
            "WorkingDirectory": "",
            "User": "",
            "Group": "",
            "Environment": "",
            "Restart": "",
            "WantedBy": "",
        }

    def _set_create_summary(self) -> None:
        self.detail_title.set_text("Create service")
        self.detail_desc.set_text("Use the base app shell to define a new unit.")
        self.detail_status.set_text("new")
        for cls in ("active", "failed"):
            self.detail_status.get_style_context().remove_class(cls)
        for child in self.summary_actions.get_children():
            self.summary_actions.remove(child)
        create_btn = Gtk.Button(label="Create service")
        create_btn.get_style_context().add_class("action-btn")
        create_btn.get_style_context().add_class("primary")
        create_btn.connect("clicked", self._on_create_service_submit)
        cancel_btn = Gtk.Button(label="Back to details")
        cancel_btn.get_style_context().add_class("action-btn")
        cancel_btn.connect("clicked", self._on_create_service_cancel)
        self.summary_actions.pack_start(create_btn, False, False, 0)
        self.summary_actions.pack_start(cancel_btn, False, False, 0)
        self.summary_actions.show_all()
        self.create_summary_warning.set_text("")
        self.create_summary_warning.show()

    def _on_create_execstart_changed(self, _entry: Gtk.Entry) -> None:
        self._update_create_execstart_warning()

    def _update_create_execstart_warning(self) -> None:
        label = getattr(self, "create_execstart_warning", None)
        summary = getattr(self, "create_summary_warning", None)
        entry = self.create_entries.get("ExecStart")
        if label is None or entry is None:
            return
        message = self._create_execstart_issue(entry.get_text().strip())
        label.set_text(message or "")
        label.set_visible(bool(message))
        if summary is not None:
            summary.set_text(message or "")
            summary.set_visible(bool(message))
        if self.create_execstart_entry is not None:
            ctx = self.create_execstart_entry.get_style_context()
            if message:
                ctx.add_class("entry-error")
            else:
                ctx.remove_class("entry-error")

    def _create_execstart_issue(self, exec_start: str) -> str:
        if not exec_start:
            return "ExecStart is required."
        exec_token = exec_start
        try:
            exec_token = shlex.split(exec_start, posix=True)[0]
        except ValueError:
            pass
        if not exec_token:
            return "ExecStart is required."
        if exec_token.startswith(("/", ".", "~")) or os.sep in exec_token:
            expanded = Path(exec_token).expanduser()
            if not expanded.exists():
                return f"ExecStart path does not exist: {expanded}"
            if expanded.is_dir():
                return f"ExecStart points to a directory, not a file: {expanded}"
            if not os.access(expanded, os.X_OK):
                return f"ExecStart is not executable: {expanded}"
            return ""
        resolved = which(exec_token)
        if resolved is None:
            return f"ExecStart command is not found in PATH: {exec_token}"
        return ""

    def _on_create_service_submit(self, _button: Gtk.Button) -> None:
        if not self.create_entries:
            return
        try:
            LOGGER.info("create service submit clicked")
            name = self.create_entries["Name"].get_text().strip()
            exec_start = self.create_entries["ExecStart"].get_text().strip()
            if not name or not exec_start:
                LOGGER.warning("create validation failed name=%r exec_start=%r", name, exec_start)
                self._show_error_dialog(
                    "Service creation failed",
                    "Name and ExecStart are required.",
                )
                return
            warning = self._create_execstart_issue(exec_start)
            if warning:
                LOGGER.warning("create execstart check warning: %s", warning)
                if not self._confirm_action("Service creation warning", f"{warning}\n\nContinue creating the service anyway?"):
                    self._status_message("Service creation cancelled")
                    return
            fields = {
                key: self.create_entries[key].get_text().strip()
                for key in COMMON_FIELDS
                if key != "Environment" and key in self.create_entries
            }
            fields["ExecStart"] = exec_start
            fields["WantedBy"] = fields.get("WantedBy", "").strip()
            fields["Environment"] = self._collect_environment_text()
            extras = []
            for key_entry, value_entry in self.extra_rows:
                key = key_entry.get_text().strip()
                value = value_entry.get_text().strip()
                if key:
                    extras.append((key, value))
            self._status_message(f"Creating {name} ...")
            LOGGER.info("creating unit name=%s wanted_by=%s exec_start=%s", name, fields.get("WantedBy", ""), exec_start)
            created_name = self.backend.create_service(name, fields, extras)
            LOGGER.info("backend created %s", created_name)
            self.favorite_names.add(created_name)
            self._save_favorite_names()
            if hasattr(self, "search_entry"):
                self.search_entry.set_text("")
            self.search_text = ""
            wanted_by = fields.get("WantedBy", "").strip()
            if wanted_by:
                try:
                    self.backend.enable(created_name)
                except BackendError as exc:
                    LOGGER.warning("enable failed for %s: %s", created_name, exc)
                    self._show_error_dialog("Service creation warning", f"Created unit, but enable failed: {exc}")
                    self._status_message(f"Created unit, but enable failed: {exc}")
            refreshed = self._refresh_and_select(created_name)
            if refreshed is None:
                LOGGER.warning("created unit missing after refresh: %s", created_name)
                self._show_error_dialog(
                    "Service creation warning",
                    f"Created {created_name}, but it did not appear in the refreshed systemd list.",
                )
                self._status_message(f"Created {created_name}, but it did not appear in the refreshed systemd list")
                return
            self._reveal_service(created_name)
            self._status_message(f"Created {created_name}")
            LOGGER.info("create flow completed for %s", created_name)
            self._show_info_dialog("Service created", f"Created {created_name}")
            self.create_mode = False
            if hasattr(self, "notebook"):
                self.notebook.set_current_page(0)
            self._refresh_from_backend()
        except BackendError as exc:
            LOGGER.exception("service creation failed")
            self._show_error_dialog("Service creation failed", str(exc))
            self._status_message(str(exc))
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("unexpected service creation error")
            self._show_error_dialog("Service creation failed", message)
            self._status_message(message)

    def _on_create_service_cancel(self, _button: Gtk.Button | None) -> None:
        self.create_mode = False
        if hasattr(self, "notebook"):
            self.notebook.set_current_page(0)
        self._refresh_detail()

    def _show_error_dialog(self, title: str, message: str) -> None:
        if self.window is None:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.show_all()
        dialog.present()
        dialog.run()
        dialog.destroy()

    def _show_info_dialog(self, title: str, message: str) -> None:
        if self.window is None:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.show_all()
        dialog.present()
        dialog.run()
        dialog.destroy()

    def _reveal_service(self, name: str) -> None:
        if not hasattr(self, "service_list"):
            return
        for row in self.service_list.get_children():
            service = getattr(row, "service", None)
            if isinstance(service, ServiceUnit) and service.name == name:
                self.service_list.select_row(row)
                row.grab_focus()
                return

    def _refresh_and_select(self, name: str) -> ServiceUnit | None:
        self._refresh_from_backend()
        refreshed = next((svc for svc in self.services if svc.name == name), None)
        if refreshed is not None:
            refreshed.favorite = True
            self.favorite_names.add(refreshed.name)
            self._save_favorite_names()
            self.selected = refreshed
            self._refresh_detail()
            return refreshed
        return None

    def _refresh_detail(self) -> None:
        service = self.selected
        if self.create_mode:
            self._set_create_summary()
            self.properties = {}
            for child in self.info_grid.get_children():
                self.info_grid.remove(child)
            for child in self.action_row.get_children():
                self.action_row.remove(child)
            for child in self.dep_list.get_children():
                self.dep_list.remove(child)
            for child in self.journal_list.get_children():
                self.journal_list.remove(child)
            self._refresh_editor()
            self._prepare_create_form()
            self.info_grid.show_all()
            self.action_row.show_all()
            self.dep_list.show_all()
            self.journal_list.show_all()
            return
        self.detail_title.set_text(service.name)
        self.detail_desc.set_text(service.description)
        self.detail_status.set_text(service.status)
        self.detail_status.get_style_context().remove_class("active")
        self.detail_status.get_style_context().remove_class("failed")
        if service.status in {"active", "failed"}:
            self.detail_status.get_style_context().add_class(service.status)

        self.host_meta.set_text(f"{service.name} selected · focus unit details and actions")
        self.properties = self.backend.read_properties(service.name)
        self.extra_properties = self.backend.read_extra_properties(service.name)
        if hasattr(self, "save_btn"):
            self.save_btn.set_label("Save vendor unit" if self._is_vendor_unit(service) else "Save unit")

        for child in self.summary_actions.get_children():
            self.summary_actions.remove(child)
        if self._can_delete(service):
            delete_btn = Gtk.Button(label="Delete")
            delete_btn.get_style_context().add_class("action-btn")
            delete_btn.get_style_context().add_class("danger")
            delete_btn.connect("clicked", self._on_action_clicked, "delete")
            self.summary_actions.pack_start(delete_btn, False, False, 0)

        for child in self.info_grid.get_children():
            self.info_grid.remove(child)
        info_rows = [
            ("Load state", service.load_state),
            ("Enabled", "yes" if service.enabled else "no"),
            ("PID", service.pid),
            ("Uptime", service.uptime),
            ("Since", service.since),
            ("Target", service.target),
            ("Memory", service.memory),
            ("CPU", service.cpu),
            ("Path", service.path),
            ("Restarts", str(service.restarts)),
        ]
        for idx, (key, value) in enumerate(info_rows):
            self.info_grid.attach(self._kv(key, value), idx % 2, idx // 2, 1, 1)

        for child in self.action_row.get_children():
            self.action_row.remove(child)
        for action, label, primary, danger in self._actions_for(service):
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("action-btn")
            if primary:
                btn.get_style_context().add_class("primary")
            if danger:
                btn.get_style_context().add_class("danger")
            btn.connect("clicked", self._on_action_clicked, action)
            self.action_row.pack_start(btn, False, False, 0)

        for child in self.dep_list.get_children():
            self.dep_list.remove(child)
        for name, state in service.deps:
            self.dep_list.pack_start(self._dependency_row(name, state), False, False, 0)

        for child in self.journal_list.get_children():
            self.journal_list.remove(child)
        for time, text in service.journal[:4]:
            self.journal_list.pack_start(self._journal_row(time, text), False, False, 0)

        self.action_row.show_all()
        self.summary_actions.show_all()
        self.dep_list.show_all()
        self.journal_list.show_all()
        self.info_grid.show_all()
        self._refresh_editor()

        if hasattr(self, "service_list"):
            for row in self.service_list.get_children():
                service_row = getattr(row, "service", None)
                if isinstance(service_row, ServiceUnit):
                    row.get_style_context().remove_class("selected")
                    if service_row.name == service.name:
                        row.get_style_context().add_class("selected")
                        self.service_list.select_row(row)

    def _on_action_clicked(self, _button: Gtk.Button, action: str) -> None:
        service = self.selected
        if service.name == "__none__":
            return
        try:
            self._status_message(f"Requesting {action} for {service.name} ...")
            if action == "start":
                self.backend.start(service.name)
            elif action == "stop":
                self.backend.stop(service.name)
            elif action == "restart":
                self.backend.restart(service.name)
            elif action == "enable":
                self.backend.enable(service.name)
            elif action == "disable":
                self.backend.disable(service.name)
            elif action == "mask":
                self.backend.mask(service.name)
            elif action == "unmask":
                self.backend.unmask(service.name)
            elif action == "favorite":
                self.favorite_names.add(service.name)
                service.favorite = True
                self._save_favorite_names()
            elif action == "unfavorite":
                self.favorite_names.discard(service.name)
                service.favorite = False
                self._save_favorite_names()
            elif action == "delete":
                if not self._confirm_action(
                    "Delete service",
                    f"Delete {service.name} from /etc/systemd/system?",
                ):
                    self._status_message("Delete cancelled")
                    return
                self.backend.delete_service(service.name)
                self.favorite_names.discard(service.name)
                self._save_favorite_names()
            elif action == "backup":
                backup = self.backend.backup_unit_file(service.name, self._unit_save_path(service))
                self._status_message(f"Backup created: {backup}")
            elif action == "restore":
                if not self._confirm_action(
                    "Restore unit backup",
                    f"Restore backup over this unit file?\n{self._unit_save_path(service)}",
                ):
                    self._status_message("Restore cancelled")
                    return
                backup = self.backend.restore_unit_backup(service.name, self._unit_save_path(service))
                self._status_message(f"Restored backup: {backup}")
            self._refresh_from_backend()
            refreshed = self.backend.refresh_service(service.name)
            refreshed.favorite = refreshed.name in self.favorite_names
            self.selected = refreshed
            self._refresh_detail()
            self._status_message(f"{service.name}: {action}")
        except BackendError as exc:
            self._status_message(str(exc))

    def _actions_for(self, service: ServiceUnit) -> list[tuple[str, str, bool, bool]]:
        if service.status == "active":
            actions = [("stop", "Stop", False, False), ("restart", "Restart", True, False)]
        elif service.status == "failed":
            actions = [("restart", "Restart", True, False), ("start", "Start", True, False)]
        else:
            actions = [("start", "Start", True, False)]

        actions.append(("disable" if service.enabled else "enable", "Disable" if service.enabled else "Enable", False, False))
        actions.append(("unfavorite" if service.favorite else "favorite", "Unpin" if service.favorite else "Pin", False, False))
        if self._unit_save_path(service):
            actions.append(("backup", "Backup unit", False, False))
            actions.append(("restore", "Restore backup", False, True))
        actions.append(("mask" if service.enabled else "unmask", "Mask" if service.enabled else "Unmask", False, True))
        if self._can_delete(service):
            actions.append(("delete", "Delete", False, True))
        return actions

    def _can_delete(self, service: ServiceUnit) -> bool:
        path = (service.path or "").strip()
        return path.startswith("/etc/systemd/system/") or service.service_class in {"custom", "app"}

    def _can_save_unit(self, service: ServiceUnit) -> bool:
        path = (service.path or "").strip()
        return path.startswith("/etc/systemd/system/") or service.service_class in {"custom", "app"}

    def _is_vendor_unit(self, service: ServiceUnit) -> bool:
        path = (service.path or "").strip()
        return path.startswith(("/usr/lib/systemd/system/", "/lib/systemd/system/"))

    def _unit_save_path(self, service: ServiceUnit) -> str:
        path = (service.path or "").strip()
        if path:
            return path
        if self._can_save_unit(service):
            return str(Path("/etc/systemd/system") / service.name)
        return ""

    def _status_label(self, service: ServiceUnit) -> str:
        return service.status

    def _pill(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("pill")
        label.get_style_context().add_class(text.replace(".", "-").replace(" ", "-"))
        return label

    def _kv(self, key: str, value: str) -> Gtk.Widget:
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        title = Gtk.Label(label=key)
        title.set_xalign(0)
        title.get_style_context().add_class("meta")
        val = Gtk.Label(label=value)
        val.set_xalign(0)
        val.set_line_wrap(True)
        frame.pack_start(title, False, False, 0)
        frame.pack_start(val, False, False, 0)
        return frame

    def _dependency_row(self, name: str, state: str) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label=name)
        title.set_xalign(0)
        hint = Gtk.Label(label="Dependency satisfied" if state == "ok" else "Watch this unit for ordering issues")
        hint.set_xalign(0)
        hint.get_style_context().add_class("muted")
        left.pack_start(title, False, False, 0)
        left.pack_start(hint, False, False, 0)
        badge = Gtk.Label(label=state)
        badge.get_style_context().add_class("pill")
        badge.get_style_context().add_class("active" if state == "ok" else "failed")
        row.pack_start(left, True, True, 0)
        row.pack_end(badge, False, False, 0)
        return row

    def _journal_row(self, time: str, text: str) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label=text)
        title.set_xalign(0)
        title.set_line_wrap(True)
        clock = Gtk.Label(label="systemd journal")
        clock.set_xalign(0)
        clock.get_style_context().add_class("muted")
        left.pack_start(title, False, False, 0)
        left.pack_start(clock, False, False, 0)
        time_label = Gtk.Label(label=time)
        time_label.get_style_context().add_class("meta")
        row.pack_start(left, True, True, 0)
        row.pack_end(time_label, False, False, 0)
        return row

    def _journal(self, service: ServiceUnit, message: str) -> None:
        service.journal.insert(0, ("now", message))
        service.journal = service.journal[:4]
        self._refresh_detail()

    def _uptime_rank(self, uptime: str) -> int:
        raw = uptime.lower()
        if "stopped" in raw or "failed" in raw:
            return 0
        days = self._extract_number(raw, "d")
        hours = self._extract_number(raw, "h")
        mins = self._extract_number(raw, "m")
        return days * 24 * 60 + hours * 60 + mins

    @staticmethod
    def _extract_number(raw: str, suffix: str) -> int:
        idx = raw.find(suffix)
        if idx <= 0:
            return 0
        start = idx - 1
        while start >= 0 and raw[start].isdigit():
            start -= 1
        chunk = raw[start + 1 : idx]
        return int(chunk) if chunk.isdigit() else 0

    def _on_reload_clicked(self, _button: Gtk.Button) -> None:
        try:
            LOGGER.info("daemon-reload clicked")
            self._status_message("Requesting daemon-reload ...")
            self.backend.daemon_reload()
            self._refresh_from_backend()
            self._status_message("daemon-reload completed")
        except BackendError as exc:
            LOGGER.exception("daemon-reload failed")
            self._status_message(str(exc))

    def _status_message(self, message: str) -> None:
        self.status_label.set_text(message)

    def _show_error_dialog(self, title: str, message: str) -> None:
        if self.window is None:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.show_all()
        dialog.present()
        dialog.run()
        dialog.destroy()

    def _confirm_action(self, title: str, message: str) -> bool:
        if self.window is None:
            return False
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=title,
        )
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _empty_service(self) -> ServiceUnit:
        return ServiceUnit(
            name="__none__",
            description="No systemd services available",
            status="inactive",
            enabled=False,
            load_state="loaded",
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
            journal=[("now", "No units found")],
            favorite=False,
        )
