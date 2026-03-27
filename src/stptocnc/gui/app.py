"""Tkinter desktop GUI for operator-focused nesting workflow."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from stptocnc.config import NestingDefaults, ProfileFamily
from stptocnc.importers import parse_nc1_file
from stptocnc.models import expand_part_instances
from stptocnc.nesting import pack_instances_first_fit
from stptocnc.workflows import finalize_nest_run


@dataclass(slots=True)
class PreviewSegment:
    kind: str
    start_in: float
    length_in: float
    label: str


def _parse_quantity_override_text(raw: str) -> dict[str, int]:
    overrides: dict[str, int] = {}
    if not raw.strip():
        return overrides
    for chunk in raw.split(","):
        token = chunk.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Invalid override token '{token}'. Use PART=QTY.")
        part_mark, qty_text = token.split("=", 1)
        qty = max(1, int(qty_text.strip()))
        overrides[part_mark.strip()] = qty
    return overrides


def _build_preview_segments(nest: object) -> list[PreviewSegment]:
    segments: list[PreviewSegment] = []
    cursor = 0.0
    for placement in nest.placements:
        if placement.transition_trim_before_in > 0:
            segments.append(
                PreviewSegment(
                    kind="trim",
                    start_in=cursor,
                    length_in=placement.transition_trim_before_in,
                    label="Trim",
                )
            )
            cursor += placement.transition_trim_before_in
        segments.append(
            PreviewSegment(
                kind="part",
                start_in=cursor,
                length_in=placement.length_in,
                label=placement.part_mark,
            )
        )
        cursor += placement.length_in
    if nest.stock_length_in > cursor:
        segments.append(
            PreviewSegment(
                kind="drop",
                start_in=cursor,
                length_in=nest.stock_length_in - cursor,
                label="Drop",
            )
        )
    return segments


class OperatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("STPtoCNC Operator")
        self.geometry("1100x760")

        self.file_paths: list[Path] = []
        self.preview_nests: list[object] = []

        self.pipe_len = tk.StringVar(value="252")
        self.hss_len = tk.StringVar(value="240")
        self.angle_len = tk.StringVar(value="240")
        self.qty_overrides = tk.StringVar(value="")
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "out" / "operator-run"))

        self._build_layout()

    def _build_layout(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(top)
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = ttk.Frame(top)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Selected NC1 Files").pack(anchor="w")
        self.file_list = tk.Listbox(left, width=55, height=18)
        self.file_list.pack(fill=tk.X, pady=4)
        ttk.Button(left, text="Add NC1 Files", command=self._add_files).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Remove Selected", command=self._remove_file).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Clear", command=self._clear_files).pack(fill=tk.X, pady=2)

        settings = ttk.LabelFrame(left, text="Nest Settings", padding=6)
        settings.pack(fill=tk.X, pady=10)
        ttk.Label(settings, text="Pipe stock length (in)").pack(anchor="w")
        ttk.Entry(settings, textvariable=self.pipe_len).pack(fill=tk.X)
        ttk.Label(settings, text="HSS stock length (in)").pack(anchor="w")
        ttk.Entry(settings, textvariable=self.hss_len).pack(fill=tk.X)
        ttk.Label(settings, text="Angle stock length (in)").pack(anchor="w")
        ttk.Entry(settings, textvariable=self.angle_len).pack(fill=tk.X)
        ttk.Label(settings, text="Qty overrides (PART=QTY,...)").pack(anchor="w")
        ttk.Entry(settings, textvariable=self.qty_overrides).pack(fill=tk.X)
        ttk.Label(settings, text="Output directory").pack(anchor="w")
        ttk.Entry(settings, textvariable=self.output_dir).pack(fill=tk.X)
        ttk.Button(settings, text="Browse Output Dir", command=self._choose_output_dir).pack(fill=tk.X, pady=2)

        ttk.Button(left, text="Preview Nests", command=self._preview).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="Finalize + Export", command=self._finalize).pack(fill=tk.X, pady=2)

        self.preview_text = tk.Text(right, width=70, height=10)
        self.preview_text.pack(fill=tk.X, padx=8, pady=6)
        self.canvas = tk.Canvas(right, background="white")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    def _add_files(self) -> None:
        picks = filedialog.askopenfilenames(filetypes=[("NC1 files", "*.nc1 *.NC1"), ("All files", "*.*")])
        for pick in picks:
            path = Path(pick)
            if path not in self.file_paths:
                self.file_paths.append(path)
                self.file_list.insert(tk.END, str(path))

    def _remove_file(self) -> None:
        selected = list(self.file_list.curselection())
        for idx in reversed(selected):
            self.file_list.delete(idx)
            del self.file_paths[idx]

    def _clear_files(self) -> None:
        self.file_list.delete(0, tk.END)
        self.file_paths.clear()

    def _choose_output_dir(self) -> None:
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)

    def _build_defaults(self) -> NestingDefaults:
        return NestingDefaults(
            stock_lengths_in={
                ProfileFamily.PIPE: float(self.pipe_len.get()),
                ProfileFamily.HSS: float(self.hss_len.get()),
                ProfileFamily.ANGLE: float(self.angle_len.get()),
                ProfileFamily.UNKNOWN: float(self.pipe_len.get()),
            }
        )

    def _run_pack_preview(self) -> tuple[list[object], NestingDefaults, dict[str, int]]:
        if not self.file_paths:
            raise ValueError("Please add at least one NC1 file.")
        defaults = self._build_defaults()
        qty_overrides = _parse_quantity_override_text(self.qty_overrides.get())
        parts = [parse_nc1_file(path) for path in self.file_paths]
        instances = expand_part_instances(parts, quantity_overrides=qty_overrides)
        nests = pack_instances_first_fit(instances, defaults=defaults).nests
        return nests, defaults, qty_overrides

    def _preview(self) -> None:
        try:
            nests, _, _ = self._run_pack_preview()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Preview error", str(exc))
            return
        self.preview_nests = nests
        self._render_preview(nests)

    def _render_preview(self, nests: list[object]) -> None:
        self.preview_text.delete("1.0", tk.END)
        self.canvas.delete("all")
        y = 20
        scale = 3.0
        for nest in nests:
            self.preview_text.insert(
                tk.END,
                f"{nest.nest_id}: stock={nest.stock_length_in:.2f} used={nest.used_length_in:.2f} drop={nest.remaining_length_in:.2f}\n",
            )
            x0 = 20
            width = max(1, int(nest.stock_length_in * scale))
            self.canvas.create_rectangle(x0, y, x0 + width, y + 28, outline="#333", fill="#f0f0f0")
            for seg in _build_preview_segments(nest):
                sx = x0 + int(seg.start_in * scale)
                ex = sx + max(1, int(seg.length_in * scale))
                color = "#2d7dd2" if seg.kind == "part" else ("#d28a2d" if seg.kind == "trim" else "#9e9e9e")
                self.canvas.create_rectangle(sx, y, ex, y + 28, fill=color, outline="")
                if seg.kind == "part":
                    self.canvas.create_text((sx + ex) / 2, y + 14, text=seg.label, fill="white", font=("Segoe UI", 8))
            self.canvas.create_text(x0 + width + 80, y + 14, text=f"Drop {nest.remaining_length_in:.2f} in", anchor="w")
            y += 44

    def _finalize(self) -> None:
        try:
            nests, defaults, qty_overrides = self._run_pack_preview()
            out_dir = Path(self.output_dir.get())
            out_dir.mkdir(parents=True, exist_ok=True)
            result = finalize_nest_run(
                nc1_files=[str(path) for path in self.file_paths],
                cutlist_output=out_dir / "cutlist.xlsx",
                cnc_output_dir=out_dir / "cnc",
                defaults=defaults,
                quantity_overrides=qty_overrides,
            )
            self._render_preview(nests)
            messagebox.showinfo(
                "Finalize complete",
                f"Generated {result['nests']} nests\nCut list: {result['cutlist']}\nCNC dir: {out_dir / 'cnc'}",
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Finalize error", str(exc))


def launch_gui() -> None:
    app = OperatorApp()
    app.mainloop()


def main() -> None:
    """GUI process entry point for scripts and packaged runtime."""
    launch_gui()
