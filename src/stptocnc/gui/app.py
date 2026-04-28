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
    part_type: str = "unknown"


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
                part_type=(placement.profile_designation or nest.profile_family.value if hasattr(nest.profile_family, "value") else "unknown"),
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
        self.geometry("1320x860")
        self.minsize(1180, 760)
        self.option_add("*Font", "Segoe UI 10")

        self.file_paths: list[Path] = []
        self.preview_nests: list[object] = []

        self.pipe_len = tk.StringVar(value="252")
        self.hss_len = tk.StringVar(value="240")
        self.angle_len = tk.StringVar(value="240")
        self.qty_overrides = tk.StringVar(value="")
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "out" / "operator-run"))
        self._qty_vars: dict[str, tk.StringVar] = {}
        self._loaded_part_qty: "OrderedDict[str, int]" = OrderedDict()
        self.theme_mode = tk.StringVar(value="Light")
        self._drag_piece_index: int | None = None

        self._set_theme("Light")

        self._build_layout()

    def _set_theme(self, mode: str) -> None:
        if mode == "Dark":
            self.palette = {
                "app_bg": "#242628",
                "panel_bg": "#2f3236",
                "main_bg": "#2a2d30",
                "card_bg": "#34383d",
                "text": "#e8eaed",
                "muted": "#b7bcc3",
                "border": "#4b5158",
                "button_primary": "#3b82f6",
                "button_primary_hover": "#2563eb",
            }
        else:
            self.palette = {
                "app_bg": "#f5f6f7",
                "panel_bg": "#eceff2",
                "main_bg": "#f7f8f9",
                "card_bg": "#ffffff",
                "text": "#1f2933",
                "muted": "#425466",
                "border": "#d7dde4",
                "button_primary": "#2563eb",
                "button_primary_hover": "#1d4ed8",
            }
        self.configure(bg=self.palette["app_bg"])

    def _mk_button(
        self,
        parent: tk.Misc,
        text: str,
        command: object,
        *,
        kind: str = "minimal",
    ) -> tk.Button:
        if kind == "primary":
            bg = self.palette["button_primary"]
            fg = "#ffffff"
            bd = 0
            active_bg = self.palette["button_primary_hover"]
        elif kind == "outlined":
            bg = self.palette["card_bg"]
            fg = self.palette["text"]
            bd = 1
            active_bg = "#edf3ff"
        else:
            bg = self.palette["card_bg"]
            fg = self.palette["muted"]
            bd = 0
            active_bg = "#f0f3f6"
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief=tk.FLAT if kind != "outlined" else tk.SOLID,
            bd=bd,
            highlightthickness=0,
            padx=10,
            pady=7,
            cursor="hand2",
        )
        default_bg = bg
        btn.bind("<Enter>", lambda _e: btn.configure(bg=active_bg))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=default_bg))
        return btn

    def _add_scrollbar_to_listbox(self, parent: tk.Misc, listbox: tk.Listbox) -> None:
        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_collapsible(self, parent: tk.Misc, title: str, *, expanded: bool = True) -> tuple[tk.Frame, tk.Frame]:
        wrapper = tk.Frame(parent, bg=self.palette["card_bg"], bd=1, relief=tk.SOLID, highlightbackground=self.palette["border"])
        head = tk.Frame(wrapper, bg=self.palette["card_bg"])
        head.pack(fill=tk.X, padx=10, pady=(8, 4))
        body = tk.Frame(wrapper, bg=self.palette["card_bg"])
        state = tk.BooleanVar(value=expanded)

        def _toggle() -> None:
            state.set(not state.get())
            if state.get():
                body.pack(fill=tk.X, padx=10, pady=(0, 10))
                btn.configure(text="▾")
            else:
                body.pack_forget()
                btn.configure(text="▸")

        btn = tk.Button(head, text="▾" if expanded else "▸", command=_toggle, bg=self.palette["card_bg"], fg=self.palette["muted"], relief=tk.FLAT, bd=0)
        btn.pack(side=tk.LEFT)
        tk.Label(head, text=title, bg=self.palette["card_bg"], fg=self.palette["text"], font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=4)
        if expanded:
            body.pack(fill=tk.X, padx=10, pady=(0, 10))
        return wrapper, body

    def _build_layout(self) -> None:
        top = tk.Frame(self, bg=self.palette["app_bg"], padx=12, pady=12)
        top.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(top, bg=self.palette["panel_bg"], width=400, padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right = tk.Frame(top, bg=self.palette["main_bg"], padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        files_card, files_body = self._create_collapsible(left, "Files", expanded=True)
        files_card.pack(fill=tk.X, pady=(0, 10))
        file_list_frame = tk.Frame(files_body, bg=self.palette["card_bg"])
        file_list_frame.pack(fill=tk.X, pady=(2, 8))
        self.file_list = tk.Listbox(file_list_frame, width=50, height=12, bg="#ffffff", fg=self.palette["text"], bd=1, relief=tk.SOLID, exportselection=False)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._add_scrollbar_to_listbox(file_list_frame, self.file_list)
        self._mk_button(files_body, "Add NC1 Files", self._add_files, kind="minimal").pack(fill=tk.X, pady=2)
        self._mk_button(files_body, "Remove", self._remove_file, kind="minimal").pack(fill=tk.X, pady=2)
        self._mk_button(files_body, "Clear", self._clear_files, kind="minimal").pack(fill=tk.X, pady=2)

        settings_card, settings_body = self._create_collapsible(left, "Nest Settings", expanded=True)
        settings_card.pack(fill=tk.X, pady=(0, 10))
        stock_card, stock_body = self._create_collapsible(settings_body, "Stock Lengths", expanded=True)
        stock_card.pack(fill=tk.X, pady=(0, 8))
        for label, var in [("Pipe stock length (in)", self.pipe_len), ("HSS stock length (in)", self.hss_len), ("Angle stock length (in)", self.angle_len)]:
            tk.Label(stock_body, text=label, bg=self.palette["card_bg"], fg=self.palette["muted"]).pack(anchor="w")
            tk.Entry(stock_body, textvariable=var, relief=tk.SOLID, bd=1).pack(fill=tk.X, pady=(0, 6))

        qty_card, qty_body = self._create_collapsible(settings_body, "Quantity", expanded=False)
        qty_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(qty_body, text="Qty overrides (PART=QTY,...)", bg=self.palette["card_bg"], fg=self.palette["muted"]).pack(anchor="w")
        tk.Entry(qty_body, textvariable=self.qty_overrides, relief=tk.SOLID, bd=1).pack(fill=tk.X, pady=(0, 6))
        tk.Label(qty_body, text="Per-part qty (editable)", bg=self.palette["card_bg"], fg=self.palette["muted"]).pack(anchor="w", pady=(4, 2))
        self.qty_grid = tk.Frame(qty_body, bg=self.palette["card_bg"])
        self.qty_grid.pack(fill=tk.X)

        output_card, output_body = self._create_collapsible(left, "Output", expanded=True)
        output_card.pack(fill=tk.X, pady=(0, 10))
        tk.Label(output_body, text="Output directory", bg=self.palette["card_bg"], fg=self.palette["muted"]).pack(anchor="w")
        tk.Entry(output_body, textvariable=self.output_dir, relief=tk.SOLID, bd=1).pack(fill=tk.X, pady=(0, 6))
        self._mk_button(output_body, "Browse Output Dir", self._choose_output_dir, kind="minimal").pack(fill=tk.X)

        controls = tk.Frame(left, bg=self.palette["panel_bg"])
        controls.pack(fill=tk.X, pady=(4, 0))
        self._mk_button(controls, "Preview Nests", self._preview, kind="outlined").pack(fill=tk.X, pady=(0, 6))
        self._mk_button(controls, "Finalize + Export", self._finalize, kind="primary").pack(fill=tk.X)

        appearance = tk.Frame(left, bg=self.palette["panel_bg"], pady=8)
        appearance.pack(fill=tk.X)
        tk.Label(appearance, text="Appearance (future-ready)", bg=self.palette["panel_bg"], fg=self.palette["muted"]).pack(anchor="w")
        ttk.Combobox(appearance, textvariable=self.theme_mode, values=["Light", "Dark"], state="readonly", width=14).pack(anchor="w")

        summary_card = tk.Frame(right, bg=self.palette["card_bg"], bd=1, relief=tk.SOLID, padx=10, pady=10)
        summary_card.pack(fill=tk.X, pady=(0, 10))
        tk.Label(summary_card, text="Nest Summary", bg=self.palette["card_bg"], fg=self.palette["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        preview_frame = tk.Frame(summary_card, bg=self.palette["card_bg"])
        preview_frame.pack(fill=tk.X, pady=(6, 0))
        self.preview_text = tk.Text(preview_frame, width=70, height=8, bg="#ffffff", fg=self.palette["text"], relief=tk.SOLID, bd=1)
        self.preview_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        preview_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        move_panel = tk.Frame(right, bg=self.palette["card_bg"], bd=1, relief=tk.SOLID, padx=10, pady=10)
        move_panel.pack(fill=tk.X, pady=(0, 10))
        tk.Label(move_panel, text="Manual Reassignment (Drag piece list item onto nest list)", bg=self.palette["card_bg"], fg=self.palette["text"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        piece_wrap = tk.Frame(move_panel, bg=self.palette["card_bg"])
        piece_wrap.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(6, 0))
        nest_wrap = tk.Frame(move_panel, bg=self.palette["card_bg"])
        nest_wrap.grid(row=1, column=1, sticky="nsew", pady=(6, 0))
        self.piece_list = tk.Listbox(piece_wrap, width=40, height=7, exportselection=False, bg="#ffffff", fg=self.palette["text"], relief=tk.SOLID, bd=1)
        self.target_nest_list = tk.Listbox(nest_wrap, width=30, height=7, exportselection=False, bg="#ffffff", fg=self.palette["text"], relief=tk.SOLID, bd=1)
        self.piece_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.target_nest_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._add_scrollbar_to_listbox(piece_wrap, self.piece_list)
        self._add_scrollbar_to_listbox(nest_wrap, self.target_nest_list)
        self.piece_list.bind("<ButtonPress-1>", self._on_piece_drag_start)
        self.target_nest_list.bind("<ButtonRelease-1>", self._on_piece_drop_on_nest)
        self._mk_button(move_panel, "Move Selected Piece", self._move_selected_piece, kind="outlined").grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        viz_card = tk.Frame(right, bg=self.palette["card_bg"], bd=1, relief=tk.SOLID, padx=10, pady=10)
        viz_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(viz_card, text="Nesting Visualization", bg=self.palette["card_bg"], fg=self.palette["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        canvas_frame = tk.Frame(viz_card, bg=self.palette["card_bg"])
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.canvas = tk.Canvas(canvas_frame, background=self.palette["main_bg"], highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_scroll_y = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        canvas_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=canvas_scroll_y.set)

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
        y = 16
        scale = 3.0
        part_palette = {
            "PIPE": "#3B82F6",
            "HSS": "#10B981",
            "L": "#F59E0B",
            "ANGLE": "#F59E0B",
            "UNKNOWN": "#7C8A99",
        }
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
            row_h = 30
            # subtle shadow + near-white card background
            self.canvas.create_rectangle(x0 + 2, y + 3, x0 + width + 2, y + row_h + 3, outline="", fill="#d9dfe6")
            self.canvas.create_rectangle(x0, y, x0 + width, y + row_h, outline="#c9d2dc", fill="#ffffff")
            for seg in _build_preview_segments(nest):
                sx = x0 + int(seg.start_in * scale)
                ex = sx + max(1, int(seg.length_in * scale))
                if seg.kind == "part":
                    part_hint = (seg.part_type or "").upper()
                    color = next((v for k, v in part_palette.items() if part_hint.startswith(k)), "#6b7a8a")
                elif seg.kind == "trim":
                    color = "#f97316"
                else:
                    color = "#9ca3af"
                self.canvas.create_rectangle(sx, y + 4, ex, y + row_h - 4, fill=color, outline="")
                if seg.kind == "part":
                    self.canvas.create_text((sx + ex) / 2, y + (row_h / 2), text=seg.label, fill="white", font=("Segoe UI", 8, "bold"))
            self.canvas.create_text(x0 + width + 80, y + (row_h / 2), text=f"Drop {nest.remaining_length_in:.2f} in", anchor="w", fill=self.palette["muted"])
            y += 48
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_piece_drag_start(self, _event: tk.Event[tk.Misc]) -> None:
        sel = self.piece_list.curselection()
        self._drag_piece_index = sel[0] if sel else None

    def _on_piece_drop_on_nest(self, event: tk.Event[tk.Misc]) -> None:
        if self._drag_piece_index is None:
            return
        index = self.target_nest_list.nearest(event.y)
        if index < 0:
            return
        piece_text = self.piece_list.get(self._drag_piece_index)
        instance_id = piece_text.split(" ", 1)[0]
        target_nest_id = self.target_nest_list.get(index)
        try:
            self.move_piece_between_nests(instance_id, target_nest_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Move error", str(exc))
        finally:
            self._drag_piece_index = None

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
