"""Tkinter desktop GUI for operator-focused nesting workflow."""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from stptocnc.config import NestingDefaults, ProfileFamily
from stptocnc.importers import parse_nc1_file
from stptocnc.models import expand_part_instances
from stptocnc.nesting import move_instance_between_nests, pack_instances_first_fit
from stptocnc.workflows import finalize_nest_run
from stptocnc.workflows.operator_run import parse_quantity_overrides


@dataclass(slots=True)
class PreviewSegment:
    kind: str
    start_in: float
    length_in: float
    label: str


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
        self._qty_vars: dict[str, tk.StringVar] = {}
        self._loaded_part_qty: "OrderedDict[str, int]" = OrderedDict()

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
        ttk.Label(settings, text="Per-part qty (editable)").pack(anchor="w", pady=(6, 0))
        self.qty_grid = ttk.Frame(settings)
        self.qty_grid.pack(fill=tk.X)
        ttk.Label(settings, text="Output directory").pack(anchor="w")
        ttk.Entry(settings, textvariable=self.output_dir).pack(fill=tk.X)
        ttk.Button(settings, text="Browse Output Dir", command=self._choose_output_dir).pack(fill=tk.X, pady=2)

        ttk.Button(left, text="Preview Nests", command=self._preview).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="Finalize + Export", command=self._finalize).pack(fill=tk.X, pady=2)

        self.preview_text = tk.Text(right, width=70, height=10)
        self.preview_text.pack(fill=tk.X, padx=8, pady=6)

        move_panel = ttk.LabelFrame(right, text="Manual Reassignment", padding=6)
        move_panel.pack(fill=tk.X, padx=8, pady=4)
        self.piece_list = tk.Listbox(move_panel, width=38, height=6, exportselection=False)
        self.piece_list.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.target_nest_list = tk.Listbox(move_panel, width=28, height=6, exportselection=False)
        self.target_nest_list.grid(row=0, column=1, sticky="nsew")
        ttk.Button(move_panel, text="Move Selected Piece", command=self._move_selected_piece).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )

        self.canvas = tk.Canvas(right, background="white")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    def _add_files(self) -> None:
        picks = filedialog.askopenfilenames(filetypes=[("NC1 files", "*.nc1 *.NC1"), ("All files", "*.*")])
        for pick in picks:
            path = Path(pick)
            if path not in self.file_paths:
                self.file_paths.append(path)
                self.file_list.insert(tk.END, str(path))
        self._refresh_qty_grid()

    def _remove_file(self) -> None:
        selected = list(self.file_list.curselection())
        for idx in reversed(selected):
            self.file_list.delete(idx)
            del self.file_paths[idx]
        self._refresh_qty_grid()

    def _clear_files(self) -> None:
        self.file_list.delete(0, tk.END)
        self.file_paths.clear()
        self._refresh_qty_grid()

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
        qty_overrides = self._collect_qty_overrides()
        parts = [parse_nc1_file(path) for path in self.file_paths]
        instances = expand_part_instances(parts, quantity_overrides=qty_overrides)
        nests = pack_instances_first_fit(instances, defaults=defaults).nests
        return nests, defaults, qty_overrides

    def _refresh_qty_grid(self) -> None:
        for child in self.qty_grid.winfo_children():
            child.destroy()
        self._qty_vars.clear()
        self._loaded_part_qty.clear()
        if not self.file_paths:
            return

        for path in self.file_paths:
            part = parse_nc1_file(path)
            self._loaded_part_qty[part.part_mark] = part.quantity

        ttk.Label(self.qty_grid, text="Part").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Label(self.qty_grid, text="Qty").grid(row=0, column=1, sticky="w")
        for row, (mark, qty) in enumerate(self._loaded_part_qty.items(), start=1):
            ttk.Label(self.qty_grid, text=mark).grid(row=row, column=0, sticky="w", padx=(0, 4))
            var = tk.StringVar(value=str(qty))
            self._qty_vars[mark] = var
            ttk.Entry(self.qty_grid, textvariable=var, width=8).grid(row=row, column=1, sticky="w")

    def _collect_qty_overrides(self) -> dict[str, int]:
        entry_overrides = parse_quantity_overrides([token for token in self.qty_overrides.get().split(",") if token.strip()])
        grid_overrides: dict[str, int] = {}
        for mark, var in self._qty_vars.items():
            qty = int(var.get().strip())
            if qty < 1:
                raise ValueError(f"Quantity for part '{mark}' must be >= 1.")
            grid_overrides[mark] = qty
        return {**grid_overrides, **entry_overrides}

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
        self.piece_list.delete(0, tk.END)
        self.target_nest_list.delete(0, tk.END)
        self.canvas.delete("all")
        y = 20
        scale = 3.0
        for nest in nests:
            self.target_nest_list.insert(tk.END, nest.nest_id)
            self.preview_text.insert(
                tk.END,
                f"{nest.nest_id}: stock={nest.stock_length_in:.2f} used={nest.used_length_in:.2f} drop={nest.remaining_length_in:.2f}\n",
            )
            for placement in nest.placements:
                self.piece_list.insert(tk.END, f"{placement.instance_id} ({placement.part_mark}) in {nest.nest_id}")
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

    def _move_selected_piece(self) -> None:
        if not self.preview_nests:
            messagebox.showerror("Move error", "Preview nests before moving pieces.")
            return
        piece_sel = self.piece_list.curselection()
        nest_sel = self.target_nest_list.curselection()
        if not piece_sel or not nest_sel:
            messagebox.showerror("Move error", "Select a piece and a target nest.")
            return
        piece_text = self.piece_list.get(piece_sel[0])
        instance_id = piece_text.split(" ", 1)[0]
        target_nest_id = self.target_nest_list.get(nest_sel[0])
        try:
            self.move_piece_between_nests(instance_id, target_nest_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Move error", str(exc))

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

    def move_piece_between_nests(self, instance_id: str, target_nest_id: str) -> None:
        """Backend hook for future drag/drop reassignment UI.

        TODO: wire this into list/canvas interactions for point-and-click reassignment.
        """
        self.preview_nests = move_instance_between_nests(self.preview_nests, instance_id, target_nest_id)
        self._render_preview(self.preview_nests)


def launch_gui() -> None:
    app = OperatorApp()
    app.mainloop()


def main() -> None:
    """GUI process entry point for scripts and packaged runtime."""
    launch_gui()
