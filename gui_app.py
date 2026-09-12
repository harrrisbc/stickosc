#!/usr/bin/env python3
"""Simple tkinter control window for StickOSC."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Any

from presets import apply_preset, list_presets
from stickosc import (
    MAP_KEYS,
    EngineSettings,
    MidiBridge,
    StickEngine,
    default_config_path,
    load_config,
    save_config_settings,
    save_mapping_table,
    write_config,
)


class MeterBar(ttk.Frame):
    """Simple horizontal meter; bipolar if center=True.

    IMPORTANT: do not store size as ``self._w`` / ``self._h`` — those names
    are reserved by tkinter for the Tcl widget path. Overwriting them makes
    Windows crash with: TclError: invalid command name \"180\".
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        width: int = 180,
        height: int = 14,
        center: bool = False,
    ) -> None:
        super().__init__(master)
        self._bar_w = int(width)
        self._bar_h = int(height)
        self._center = bool(center)
        self._value = 0.0
        self._canvas = tk.Canvas(
            self,
            width=self._bar_w,
            height=self._bar_h,
            highlightthickness=0,
            bg="#1e1e1e",
            borderwidth=0,
        )
        self._canvas.pack()
        # Defer first paint until widget exists in Tcl
        self.after_idle(self.redraw)

    def set_value(self, value: float) -> None:
        self._value = max(-1.0, min(1.0, float(value)))
        self.redraw()

    def redraw(self) -> None:
        c = self._canvas
        try:
            if not c.winfo_exists():
                return
            c.delete("all")
        except tk.TclError:
            return
        c.create_rectangle(0, 0, self._bar_w, self._bar_h, fill="#2a2a2a", outline="")
        if self._center:
            mid = self._bar_w // 2
            c.create_line(mid, 0, mid, self._bar_h, fill="#666666")
            fill_w = int(abs(self._value) * (self._bar_w / 2))
            if self._value >= 0:
                c.create_rectangle(mid, 1, mid + fill_w, self._bar_h - 1, fill="#3db8a8", outline="")
            else:
                c.create_rectangle(mid - fill_w, 1, mid, self._bar_h - 1, fill="#3db8a8", outline="")
        else:
            v = max(0.0, self._value)
            fill_w = int(v * self._bar_w)
            c.create_rectangle(0, 1, fill_w, self._bar_h - 1, fill="#3db8a8", outline="")


class StickOscApp(ttk.Frame):
    def __init__(self, master: tk.Tk, config_path: Path | None = None) -> None:
        super().__init__(master, padding=12)
        self.master = master
        self.config_path = config_path or default_config_path()
        self.engine: StickEngine | None = None
        self._demo_var = tk.BooleanVar(value=False)
        self._map_rows: dict[str, dict[str, tk.Variable]] = {}

        self.cfg = load_config(self.config_path)
        self._build()
        self._load_fields_from_config()
        self._refresh_midi_ports()
        self._load_map_table_from_config()
        self.after(50, self._tick)

    def _build(self) -> None:
        self.master.title("StickOSC")
        self.master.minsize(640, 520)
        self.pack(fill="both", expand=True)

        title = ttk.Label(self, text="StickOSC", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="Xbox / PS5 → OSC / MIDI").grid(row=1, column=0, sticky="w", pady=(0, 8))

        notebook = ttk.Notebook(self)
        notebook.grid(row=2, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        control = ttk.Frame(notebook, padding=8)
        mapping = ttk.Frame(notebook, padding=8)
        notebook.add(control, text="Control")
        notebook.add(mapping, text="Mapping")

        self._build_control_tab(control)
        self._build_mapping_tab(mapping)

        self.master.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_control_tab(self, parent: ttk.Frame) -> None:
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        row = 0
        self.osc_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="OSC", variable=self.osc_enabled).grid(row=row, column=0, sticky="w")
        row += 1
        ttk.Label(left, text="Host").grid(row=row, column=0, sticky="w")
        self.host_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.host_var, width=18).grid(row=row, column=1, sticky="we", pady=2)
        row += 1
        ttk.Label(left, text="Port").grid(row=row, column=0, sticky="w")
        self.port_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.port_var, width=8).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        self.osc2_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="OSC extra", variable=self.osc2_enabled).grid(
            row=row, column=0, sticky="w", pady=(6, 0)
        )
        row += 1
        ttk.Label(left, text="Extra host").grid(row=row, column=0, sticky="w")
        self.osc2_host_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.osc2_host_var, width=18).grid(row=row, column=1, sticky="we", pady=2)
        row += 1
        ttk.Label(left, text="Extra port").grid(row=row, column=0, sticky="w")
        self.osc2_port_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.osc2_port_var, width=8).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        self.midi_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="MIDI", variable=self.midi_enabled).grid(
            row=row, column=0, sticky="w", pady=(8, 0)
        )
        row += 1
        ttk.Label(left, text="MIDI port").grid(row=row, column=0, sticky="w")
        midi_row = ttk.Frame(left)
        midi_row.grid(row=row, column=1, sticky="we", pady=2)
        self.midi_port_var = tk.StringVar()
        self.midi_port_combo = ttk.Combobox(midi_row, textvariable=self.midi_port_var, width=16)
        self.midi_port_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(midi_row, text="Refresh", width=8, command=self._refresh_midi_ports).pack(
            side="left", padx=(4, 0)
        )
        row += 1
        ttk.Label(left, text="Channel").grid(row=row, column=0, sticky="w")
        self.midi_ch_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.midi_ch_var, width=6).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        ttk.Label(left, text="Layout").grid(row=row, column=0, sticky="w", pady=(8, 0))
        self.layout_var = tk.StringVar(value="auto")
        ttk.Combobox(
            left,
            textvariable=self.layout_var,
            values=["auto", "xbox", "ps5"],
            state="readonly",
            width=10,
        ).grid(row=row, column=1, sticky="w", pady=(8, 2))
        row += 1

        ttk.Label(left, text="Pad index").grid(row=row, column=0, sticky="w")
        self.index_var = tk.StringVar(value="0")
        ttk.Entry(left, textvariable=self.index_var, width=6).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        ttk.Checkbutton(left, text="Demo mode (no pad)", variable=self._demo_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 4)
        )
        row += 1

        btns = ttk.Frame(left)
        btns.grid(row=row, column=0, columnspan=2, sticky="we", pady=(8, 0))
        self.start_btn = ttk.Button(btns, text="Start", command=self._on_start)
        self.start_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = ttk.Button(btns, text="Stop", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Save", command=self._on_save).pack(side="left")
        row += 1

        self.status_var = tk.StringVar(value="Stopped")
        ttk.Label(left, textvariable=self.status_var, wraplength=260).grid(
            row=row, column=0, columnspan=2, sticky="we", pady=(10, 0)
        )

        # --- live meters ---
        self.ctrl_var = tk.StringVar(value="controller: —")
        self.layout_status = tk.StringVar(value="layout: —")
        ttk.Label(right, textvariable=self.ctrl_var).pack(anchor="w")
        ttk.Label(right, textvariable=self.layout_status).pack(anchor="w", pady=(0, 6))

        self.meters: dict[str, MeterBar] = {}
        for key, label, center in (
            ("left_x", "LX", True),
            ("left_y", "LY", True),
            ("right_x", "RX", True),
            ("right_y", "RY", True),
            ("lt", "LT", False),
            ("rt", "RT", False),
        ):
            rowf = ttk.Frame(right)
            rowf.pack(fill="x", pady=2)
            ttk.Label(rowf, text=label, width=3).pack(side="left")
            bar = MeterBar(rowf, center=center)
            bar.pack(side="left", padx=6)
            self.meters[key] = bar

        self.btn_vars = {
            name: tk.StringVar(value=label)
            for name, label in (
                ("a", "A"),
                ("b", "B"),
                ("x", "X"),
                ("y", "Y"),
                ("lb", "LB"),
                ("rb", "RB"),
                ("back", "Back"),
                ("start", "Start"),
                ("l3", "L3"),
                ("r3", "R3"),
            )
        }
        btn_frame = ttk.Frame(right)
        btn_frame.pack(anchor="w", pady=(10, 0))
        self.btn_labels: dict[str, ttk.Label] = {}
        for i, name in enumerate(self.btn_vars):
            lab = ttk.Label(btn_frame, textvariable=self.btn_vars[name], width=6)
            lab.grid(row=i // 5, column=i % 5, padx=2, pady=2)
            self.btn_labels[name] = lab

        self.pulse_var = tk.StringVar(value="○")
        ttk.Label(right, textvariable=self.pulse_var).pack(anchor="w", pady=(8, 0))

    def _build_mapping_tab(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Preset").pack(side="left")
        self.preset_var = tk.StringVar(value="StickOSC")
        self.preset_combo = ttk.Combobox(
            top,
            textvariable=self.preset_var,
            values=list_presets(),
            state="readonly",
            width=14,
        )
        self.preset_combo.pack(side="left", padx=6)
        ttk.Button(top, text="Apply preset", command=self._on_apply_preset).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Save mapping", command=self._on_save_mapping).pack(side="left")

        hint = ttk.Label(
            parent,
            text="Edit OSC address / MIDI per control. Apply preset overwrites addresses "
            "(Stop first if running). Windows MIDI needs loopMIDI or an existing port.",
            wraplength=580,
        )
        hint.pack(anchor="w", pady=(0, 6))

        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        table = ttk.Frame(canvas)
        table.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=table, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        headers = ("Control", "Label", "OSC address", "MIDI", "Note/CC")
        for col, text in enumerate(headers):
            ttk.Label(table, text=text, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=col, sticky="w", padx=4, pady=2
            )

        self._map_rows = {}
        for i, key in enumerate(MAP_KEYS, start=1):
            ttk.Label(table, text=key, width=10).grid(row=i, column=0, sticky="w", padx=4, pady=1)
            label_var = tk.StringVar()
            addr_var = tk.StringVar()
            kind_var = tk.StringVar()
            num_var = tk.StringVar()
            ttk.Entry(table, textvariable=label_var, width=14).grid(row=i, column=1, padx=2, pady=1)
            ttk.Entry(table, textvariable=addr_var, width=28).grid(row=i, column=2, padx=2, pady=1)
            kind_box = ttk.Combobox(
                table,
                textvariable=kind_var,
                values=["", "note", "cc"],
                width=7,
                state="readonly",
            )
            kind_box.grid(row=i, column=3, padx=2, pady=1)
            ttk.Entry(table, textvariable=num_var, width=6).grid(row=i, column=4, padx=2, pady=1)
            self._map_rows[key] = {
                "label": label_var,
                "address": addr_var,
                "kind": kind_var,
                "num": num_var,
            }

    def _refresh_midi_ports(self) -> None:
        current = self.midi_port_var.get().strip()
        ports: list[str] = []
        try:
            ports = MidiBridge.list_ports()
        except Exception as exc:
            self.status_var.set(f"MIDI ports: {exc}")
        values = list(ports)
        # Keep configured / typed name even if not currently listed
        if current and current not in values:
            values = [current, *values]
        if "StickOSC" not in values and not any("StickOSC" in p for p in values):
            # Placeholder name for Mac virtual create; harmless on Windows until Start
            values.append("StickOSC")
        self.midi_port_combo["values"] = values
        if current:
            self.midi_port_var.set(current)
        elif ports:
            self.midi_port_var.set(ports[0])
        else:
            self.midi_port_var.set("StickOSC")

    def _load_fields_from_config(self) -> None:
        c = self.cfg
        self.osc_enabled.set(bool(c["osc"].get("enabled", True)))
        self.host_var.set(str(c["osc"].get("host", "127.0.0.1")))
        self.port_var.set(str(c["osc"].get("port", 9000)))
        extra = c["osc"].get("extra") or {}
        self.osc2_enabled.set(bool(extra.get("enabled", False)))
        self.osc2_host_var.set(str(extra.get("host", "127.0.0.1")))
        self.osc2_port_var.set(str(extra.get("port", 9001)))
        self.midi_enabled.set(bool(c["midi"].get("enabled", False)))
        self.midi_port_var.set(str(c["midi"].get("port", "StickOSC")))
        self.midi_ch_var.set(str(c["midi"].get("channel", 1)))
        self.layout_var.set(str(c["controller"].get("layout", "auto")))
        self.index_var.set(str(c["controller"].get("index", 0)))

    def _load_map_table_from_config(self) -> None:
        mapping = self.cfg.get("map") or {}
        for key, vars_ in self._map_rows.items():
            meta = mapping.get(key) or {}
            vars_["label"].set(str(meta.get("label", "")))
            vars_["address"].set(str(meta.get("address", "")))
            midi = meta.get("midi") or {}
            kind = str(midi.get("kind", "")).lower() if midi else ""
            vars_["kind"].set(kind if kind in ("note", "cc") else "")
            if kind == "note":
                vars_["num"].set(str(midi.get("note", "")))
            elif kind == "cc":
                vars_["num"].set(str(midi.get("cc", midi.get("controller", ""))))
            else:
                vars_["num"].set("")

    def _mapping_from_table(self) -> dict[str, Any]:
        base = (self.cfg.get("map") or {}).copy()
        out: dict[str, Any] = {}
        for key in MAP_KEYS:
            vars_ = self._map_rows[key]
            existing = dict(base.get(key) or {})
            address = vars_["address"].get().strip()
            label = vars_["label"].get().strip()
            kind = vars_["kind"].get().strip().lower()
            num_raw = vars_["num"].get().strip()
            entry: dict[str, Any] = {
                "address": address,
                "type": existing.get("type") or "button",
            }
            if label:
                entry["label"] = label
            if kind in ("note", "cc"):
                midi: dict[str, Any] = {"kind": kind}
                if num_raw:
                    try:
                        num = int(num_raw)
                    except ValueError as exc:
                        raise ValueError(f"{key}: Note/CC must be an integer") from exc
                    if kind == "note":
                        midi["note"] = num
                    else:
                        midi["cc"] = num
                entry["midi"] = midi
            out[key] = entry
        return out

    def _settings_from_fields(self) -> EngineSettings:
        try:
            port = int(self.port_var.get().strip())
            osc2_port = int(self.osc2_port_var.get().strip() or "9001")
            index = int(self.index_var.get().strip())
            channel = int(self.midi_ch_var.get().strip())
        except ValueError as exc:
            raise ValueError("Port / index / MIDI channel must be integers") from exc
        return EngineSettings(
            config_path=self.config_path,
            host=self.host_var.get().strip() or "127.0.0.1",
            port=port,
            index=index,
            deadzone=float(self.cfg["controller"].get("deadzone", 0.12)),
            layout_pref=self.layout_var.get() or "auto",
            osc_enabled=bool(self.osc_enabled.get()),
            osc2_enabled=bool(self.osc2_enabled.get()),
            osc2_host=self.osc2_host_var.get().strip() or "127.0.0.1",
            osc2_port=osc2_port,
            midi_enabled=bool(self.midi_enabled.get()),
            midi_port=self.midi_port_var.get().strip() or "StickOSC",
            midi_channel=channel,
            demo=bool(self._demo_var.get()),
            verbose=False,
        )

    def _persist_all(self) -> None:
        settings = self._settings_from_fields()
        mapping = self._mapping_from_table()
        base = load_config(self.config_path)
        base["map"] = mapping
        save_config_settings(self.config_path, settings, base=base)
        self.cfg = load_config(self.config_path)

    def _on_start(self) -> None:
        if self.engine and self.engine.get_snapshot().running:
            return
        try:
            settings = self._settings_from_fields()
        except ValueError as exc:
            messagebox.showerror("StickOSC", str(exc))
            return
        if not settings.any_output:
            messagebox.showerror("StickOSC", "Enable OSC and/or MIDI first.")
            return
        try:
            self._persist_all()
        except Exception as exc:
            messagebox.showwarning("StickOSC", f"Could not save config: {exc}")

        try:
            self.engine = StickEngine(settings)
            # Main-thread coop mode — required on macOS (threaded pygame freezes the app)
            self.engine.begin()
            snap = self.engine.get_snapshot()
            if snap.error and not snap.running:
                messagebox.showerror("StickOSC", snap.error)
                self.engine.end()
                self.engine = None
                return
        except Exception as exc:
            messagebox.showerror("StickOSC", f"Failed to start: {exc}")
            self.engine = None
            return

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_var.set("Running…")

    def _on_stop(self) -> None:
        if self.engine:
            self.engine.end()
            self.engine = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set("Stopped")
        self.pulse_var.set("○")

    def _on_save(self) -> None:
        try:
            self._persist_all()
            self.status_var.set(f"Saved {self.config_path}")
        except Exception as exc:
            messagebox.showerror("StickOSC", str(exc))

    def _on_save_mapping(self) -> None:
        try:
            mapping = self._mapping_from_table()
            save_mapping_table(self.config_path, mapping, base=load_config(self.config_path))
            self.cfg = load_config(self.config_path)
            self.status_var.set(f"Saved mapping → {self.config_path}")
        except Exception as exc:
            messagebox.showerror("StickOSC", str(exc))

    def _on_apply_preset(self) -> None:
        name = self.preset_var.get().strip()
        if not name:
            return
        if self.engine and self.engine.get_snapshot().running:
            if not messagebox.askyesno(
                "StickOSC",
                "Engine is running. Stop it and apply this preset?",
            ):
                return
            self._on_stop()
        if not messagebox.askyesno(
            "StickOSC",
            f"Apply preset “{name}”? This overwrites OSC addresses (and sets a suggested OSC port).",
        ):
            return
        try:
            base = load_config(self.config_path)
            # Merge any unsaved table edits into base before applying
            try:
                base["map"] = self._mapping_from_table()
            except ValueError:
                pass
            updated = apply_preset(base, name)
            write_config(self.config_path, updated)
            self.cfg = load_config(self.config_path)
            self._load_fields_from_config()
            self._load_map_table_from_config()
            self._refresh_midi_ports()
            self.status_var.set(f"Applied preset {name}")
        except Exception as exc:
            messagebox.showerror("StickOSC", str(exc))

    def _tick(self) -> None:
        if self.engine:
            # Drive engine on the UI thread (macOS-safe)
            if self.engine.active:
                try:
                    snap = self.engine.poll()
                except Exception as exc:
                    self.status_var.set(f"Error: {exc}")
                    self._on_stop()
                    self.after(16, self._tick)
                    return
            else:
                snap = self.engine.get_snapshot()

            name = snap.joy_name or "(none)"
            self.ctrl_var.set(f"controller: {name}")
            src = snap.layout_pref
            note = snap.layout if src == snap.layout else f"{snap.layout} ({src})"
            self.layout_status.set(f"layout: {note}")
            for key, bar in self.meters.items():
                bar.set_value(snap.values.get(key, 0.0))
            ps5 = snap.layout == "ps5"
            labels = {
                "a": "✕" if ps5 else "A",
                "b": "○" if ps5 else "B",
                "x": "□" if ps5 else "X",
                "y": "△" if ps5 else "Y",
                "lb": "L1" if ps5 else "LB",
                "rb": "R1" if ps5 else "RB",
                "back": "Cre" if ps5 else "Back",
                "start": "Opt" if ps5 else "Start",
                "l3": "L3",
                "r3": "R3",
            }
            for name, var in self.btn_vars.items():
                on = snap.values.get(name, 0.0) >= 0.5
                prefix = "●" if on else "○"
                var.set(f"{prefix}{labels[name]}")
            self.pulse_var.set("● sending" if snap.sent_pulse else "○ idle")
            if snap.error:
                self.status_var.set(snap.error)
            elif snap.running:
                self.status_var.set(f"Running · OSC {snap.osc_line} · MIDI {snap.midi_line}")
            else:
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
                if snap.error:
                    self.status_var.set(snap.error)
                else:
                    self.status_var.set("Stopped")
        self.after(16, self._tick)

    def _on_close(self) -> None:
        self._on_stop()
        self.master.destroy()


def run(config_path: Path | None = None) -> int:
    # Set SDL dummies before pygame gets imported via stickosc side effects on Start
    import os

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    root = tk.Tk()
    root.title("StickOSC")
    # Prefer a readable default theme
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except tk.TclError:
        pass
    StickOscApp(root, config_path=config_path)
    root.mainloop()
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
