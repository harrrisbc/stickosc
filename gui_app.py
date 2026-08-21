#!/usr/bin/env python3
"""Simple tkinter control window for StickOSC."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from stickosc import (
    EngineSettings,
    StickEngine,
    default_config_path,
    load_config,
    save_config_settings,
)


class MeterBar(ttk.Frame):
    """Simple horizontal meter; bipolar if center=True.

    Uses composition (not Canvas subclass) — Canvas subclass + delete()
    during __init__ crashes on some Windows/PyInstaller tk builds
    with: TclError: invalid command name \"180\".
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
        self._w = int(width)
        self._h = int(height)
        self._center = bool(center)
        self._value = 0.0
        self._canvas = tk.Canvas(
            self,
            width=self._w,
            height=self._h,
            highlightthickness=0,
            bg="#1e1e1e",
            borderwidth=0,
        )
        self._canvas.pack()
        # Defer first paint until widget exists in Tcl (Windows-safe)
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
        c.create_rectangle(0, 0, self._w, self._h, fill="#2a2a2a", outline="")
        if self._center:
            mid = self._w // 2
            c.create_line(mid, 0, mid, self._h, fill="#666666")
            fill_w = int(abs(self._value) * (self._w / 2))
            if self._value >= 0:
                c.create_rectangle(mid, 1, mid + fill_w, self._h - 1, fill="#3db8a8", outline="")
            else:
                c.create_rectangle(mid - fill_w, 1, mid, self._h - 1, fill="#3db8a8", outline="")
        else:
            v = max(0.0, self._value)
            fill_w = int(v * self._w)
            c.create_rectangle(0, 1, fill_w, self._h - 1, fill="#3db8a8", outline="")


class StickOscApp(ttk.Frame):
    def __init__(self, master: tk.Tk, config_path: Path | None = None) -> None:
        super().__init__(master, padding=12)
        self.master = master
        self.config_path = config_path or default_config_path()
        self.engine: StickEngine | None = None
        self._demo_var = tk.BooleanVar(value=False)

        self.cfg = load_config(self.config_path)
        self._build()
        self._load_fields_from_config()
        self.after(50, self._tick)

    def _build(self) -> None:
        self.master.title("StickOSC")
        self.master.minsize(520, 420)
        self.pack(fill="both", expand=True)

        title = ttk.Label(self, text="StickOSC", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(self, text="Xbox / PS5 → OSC / MIDI").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        left = ttk.Frame(self)
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 12))
        right = ttk.Frame(self)
        right.grid(row=2, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # --- controls ---
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

        self.midi_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="MIDI", variable=self.midi_enabled).grid(row=row, column=0, sticky="w", pady=(8, 0))
        row += 1
        ttk.Label(left, text="MIDI port").grid(row=row, column=0, sticky="w")
        self.midi_port_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.midi_port_var, width=18).grid(row=row, column=1, sticky="we", pady=2)
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
        ttk.Label(left, textvariable=self.status_var, wraplength=240).grid(
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

        self.master.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_fields_from_config(self) -> None:
        c = self.cfg
        self.osc_enabled.set(bool(c["osc"].get("enabled", True)))
        self.host_var.set(str(c["osc"].get("host", "127.0.0.1")))
        self.port_var.set(str(c["osc"].get("port", 9000)))
        self.midi_enabled.set(bool(c["midi"].get("enabled", False)))
        self.midi_port_var.set(str(c["midi"].get("port", "StickOSC")))
        self.midi_ch_var.set(str(c["midi"].get("channel", 1)))
        self.layout_var.set(str(c["controller"].get("layout", "auto")))
        self.index_var.set(str(c["controller"].get("index", 0)))

    def _settings_from_fields(self) -> EngineSettings:
        try:
            port = int(self.port_var.get().strip())
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
            midi_enabled=bool(self.midi_enabled.get()),
            midi_port=self.midi_port_var.get().strip() or "StickOSC",
            midi_channel=channel,
            demo=bool(self._demo_var.get()),
            verbose=False,
        )

    def _on_start(self) -> None:
        if self.engine and self.engine.get_snapshot().running:
            return
        try:
            settings = self._settings_from_fields()
        except ValueError as exc:
            messagebox.showerror("StickOSC", str(exc))
            return
        if not settings.osc_enabled and not settings.midi_enabled:
            messagebox.showerror("StickOSC", "Enable OSC and/or MIDI first.")
            return
        # persist current control fields
        try:
            save_config_settings(self.config_path, settings, base=load_config(self.config_path))
            self.cfg = load_config(self.config_path)
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
            settings = self._settings_from_fields()
            save_config_settings(self.config_path, settings, base=load_config(self.config_path))
            self.cfg = load_config(self.config_path)
            self.status_var.set(f"Saved {self.config_path}")
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
