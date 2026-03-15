#!/usr/bin/env python3
"""
Seating Chart Planner

Event planning tool for arranging seats, tables, and guest assignments.
Features:
- Drag-and-drop table arrangement with view-center creation (center_on_canvas)
- Room boundary as coordinate origin (get_origin_pos / relative_pos)
- Alignment and distribution using origin-relative coordinates
- Zoom with proper view centering
- Real-world distance measurement (meters)
- Guest assignment tracking
- Export seating arrangements and guest lists

Dependencies: customtkinter
"""

import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas, DraggableRectangle
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path

TABLE_TYPES = {
    "Round 8": {"width": 60, "height": 60, "seats": 8, "shape": "circle"},
    "Round 10": {"width": 75, "height": 75, "seats": 10, "shape": "circle"},
    "Rectangular": {"width": 80, "height": 40, "seats": 8, "shape": "rect"},
    "Long Table": {"width": 120, "height": 30, "seats": 12, "shape": "rect"},
}

TABLE_COLORS = {
    "VIP": "#FFD700",
    "Family": "#87CEEB",
    "Friends": "#98FB98",
    "General": "#DDA0DD",
}

PIXELS_PER_METER = 50


class Table:
    """Represents a table in the seating arrangement."""

    def __init__(
        self,
        table_type: str,
        category: str = "General",
        table_number: int = 1,
        guests: Optional[List[str]] = None,
    ):
        self.table_type = table_type
        self.category = category
        self.table_number = table_number
        self.guests = guests or []
        self.max_seats = TABLE_TYPES[table_type]["seats"]


class SeatingChartPlanner:
    """
    Event seating arrangement tool.

    Demonstrates:
        - Room boundary as coordinate origin (get_origin_pos / relative_pos)
        - View-center-aware table placement (center_on_canvas)
        - Origin-relative alignment and distribution
        - Zoom with proper view centering
        - Metric distance measurement
        - Save/Load with origin-relative coordinates
    """

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Seating Chart Planner - Event Planning Tool")
        self.root.geometry("1400x900")

        self.tables: Dict[int, Tuple[DraggableRectangle, Table]] = {}
        self.table_counter = 0
        self.room_width_m = 25
        self.room_height_m = 20

        self._setup_ui()
        self._create_room_boundary()
        self._load_default_layout()

    # ─── UI Setup ───────────────────────────────────────────────────────

    def _setup_ui(self):
        main = ctk.CTkFrame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(main, width=580)
        left.pack(side="left", fill="y", padx=5, pady=5)
        left.pack_propagate(False)

        canvas_frame = ctk.CTkFrame(main)
        canvas_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self._create_control_panel(left)
        self._create_canvas(canvas_frame)

    def _create_control_panel(self, parent):
        ctk.CTkLabel(parent, text="Seating Planner", font=("Arial", 18, "bold")).pack(pady=10)

        # ── Venue info ──
        venue = ctk.CTkFrame(parent)
        venue.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(venue, text="Venue Dimensions:", font=("Arial", 12, "bold")).pack(pady=5)
        ctk.CTkLabel(
            venue, text=f"{self.room_width_m}m x {self.room_height_m}m", font=("Arial", 11)
        ).pack()

        self._sep(parent)

        # ── Table creation ──
        ctk.CTkLabel(parent, text="Add Table:", font=("Arial", 14, "bold")).pack(pady=5)
        for tt in TABLE_TYPES:
            ctk.CTkButton(parent, text=tt, command=lambda t=tt: self._add_table(t), height=35).pack(
                pady=2, padx=10, fill="x"
            )

        self._sep(parent)

        # ── Category selection ──
        ctk.CTkLabel(parent, text="Table Category:", font=("Arial", 14, "bold")).pack(pady=5)
        self.category_var = ctk.StringVar(value="General")
        for cat, color in TABLE_COLORS.items():
            frame = ctk.CTkFrame(parent)
            frame.pack(pady=2, padx=10, fill="x")
            ctk.CTkRadioButton(frame, text=cat, variable=self.category_var, value=cat).pack(
                side="left", padx=5
            )
            ctk.CTkFrame(frame, width=50, height=20, fg_color=color, corner_radius=3).pack(
                side="right", padx=5
            )

        self._sep(parent)

        # ── Alignment / Distribution ──
        ctk.CTkLabel(parent, text="Tools:", font=("Arial", 14, "bold")).pack(pady=5)
        ctk.CTkButton(
            parent, text="Align Selected", command=lambda: self._align_selected("center"), height=35
        ).pack(pady=2, padx=10, fill="x")
        ctk.CTkButton(
            parent,
            text="Distribute H",
            command=lambda: self._distribute_selected("horizontal"),
            height=35,
        ).pack(pady=2, padx=10, fill="x")
        ctk.CTkButton(
            parent,
            text="Distribute V",
            command=lambda: self._distribute_selected("vertical"),
            height=35,
        ).pack(pady=2, padx=10, fill="x")

        self._sep(parent)

        # ── Zoom ──
        ctk.CTkLabel(parent, text="Zoom:", font=("Arial", 14, "bold")).pack(pady=5)
        zf = ctk.CTkFrame(parent)
        zf.pack(padx=10, fill="x")
        ctk.CTkButton(zf, text="+", command=self._zoom_in, width=50).pack(
            side="left", padx=2, expand=True, fill="x"
        )
        ctk.CTkButton(zf, text="-", command=self._zoom_out, width=50).pack(
            side="left", padx=2, expand=True, fill="x"
        )

        self._sep(parent)

        # ── Export / Save / Load ──
        export = ctk.CTkFrame(parent)
        export.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(
            export,
            text="Load Layout",
            command=self._load_layout,
            height=40,
            fg_color="#1565C0",
        ).pack(pady=2, fill="x")
        ctk.CTkButton(
            export,
            text="Save Layout",
            command=self._save_layout,
            height=40,
            fg_color="#2E7D32",
        ).pack(pady=2, fill="x")
        ctk.CTkButton(
            export,
            text="Export Guest List",
            command=self._export_guest_list,
            height=40,
        ).pack(pady=2, fill="x")

    @staticmethod
    def _sep(parent):
        ctk.CTkFrame(parent, height=2, fg_color="#444").pack(pady=10, padx=10, fill="x")

    def _create_canvas(self, parent):
        self.canvas = InteractiveCanvas(
            parent,
            width=1000,
            height=750,
            bg="#2b2b2b",
            select_outline_color="#00ff88",
            dpi=96,
            enable_zoom=True,
        )
        self.canvas.pack(fill="both", expand=True)

    # ─── Room Boundary (Origin Rectangle) ──────────────────────────────

    def _create_room_boundary(self):
        """
        Draw the room boundary.

        This rectangle serves as our coordinate origin. All table positions
        are stored as meters relative to this boundary's top-left corner,
        using the get_origin_pos / relative_pos pattern.
        """
        rw = self.room_width_m * PIXELS_PER_METER
        rh = self.room_height_m * PIXELS_PER_METER

        cw = self.canvas.winfo_reqwidth()
        ch = self.canvas.winfo_reqheight()

        x1 = (cw - rw) / 2
        y1 = (ch - rh) / 2
        x2 = x1 + rw
        y2 = y1 + rh

        self.room_rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="white", width=5, dash=(10, 5), tags="room_boundary"
        )

        title = f"Event Space ({self.room_width_m}m x {self.room_height_m}m)"
        self.canvas.create_text(
            (x1 + x2) / 2,
            y1 - 20,
            text=title,
            fill="white",
            font=("Arial", 14, "bold"),
            tags="room_title",
        )

        # Scale markers
        for i in range(0, self.room_width_m + 1, 5):
            x = x1 + i * PIXELS_PER_METER
            self.canvas.create_line(x, y2, x, y2 + 10, fill="#666", tags="scale")
            self.canvas.create_text(
                x, y2 + 20, text=f"{i}m", fill="#888", font=("Arial", 9), tags="scale"
            )
        for i in range(0, self.room_height_m + 1, 5):
            y = y1 + i * PIXELS_PER_METER
            self.canvas.create_line(x1 - 10, y, x1, y, fill="#666", tags="scale")
            self.canvas.create_text(
                x1 - 25, y, text=f"{i}m", fill="#888", font=("Arial", 9), tags="scale"
            )

    def _get_room_origin(self) -> List[float]:
        """
        Get the room boundary's top-left position -- our coordinate origin.

        Mirrors format_editor._canvas_get_origin_pos(). All table positions
        are stored relative to this point.
        """
        return self.canvas.get_origin_pos(self.room_rect_id)

    # ─── Default Wedding Layout ──────────────────────────────────────────

    def _load_default_layout(self):
        """
        Preload a wedding/marriage ceremony seating layout.

        Layout (25m wide x 20m tall):
          - Altar/stage at the front (top center)
          - Red-carpet aisle running down the center
          - VIP/Head Table for the wedding party near the altar
          - Bride's side tables (left): Family closest to aisle, Friends farther out
          - Groom's side tables (right): mirror of bride's side
          - General tables at the back
        """
        origin = self._get_room_origin()
        room_cx = self.room_width_m / 2  # 12.5m center

        # ── Altar / Stage (non-interactive canvas rectangle) ──
        altar_w, altar_h = 6, 2  # meters
        ax1 = (room_cx - altar_w / 2) * PIXELS_PER_METER + origin[0]
        ay1 = 1.0 * PIXELS_PER_METER + origin[1]
        ax2 = (room_cx + altar_w / 2) * PIXELS_PER_METER + origin[0]
        ay2 = (1.0 + altar_h) * PIXELS_PER_METER + origin[1]
        self.canvas.create_rectangle(
            ax1,
            ay1,
            ax2,
            ay2,
            fill="#4a3728",
            outline="#654321",
            width=3,
            tags="decor_altar",
        )
        self.canvas.create_text(
            (ax1 + ax2) / 2,
            (ay1 + ay2) / 2,
            text="Altar",
            fill="white",
            font=("Arial", 14, "bold"),
            tags="decor_altar",
        )

        # ── Red-Carpet Aisle (non-interactive canvas rectangle) ──
        carpet_w = 1.2  # meters wide
        carpet_top = 3.5  # starts just below the altar
        carpet_bottom = 19.0  # extends almost to the back
        cx1 = (room_cx - carpet_w / 2) * PIXELS_PER_METER + origin[0]
        cy1 = carpet_top * PIXELS_PER_METER + origin[1]
        cx2 = (room_cx + carpet_w / 2) * PIXELS_PER_METER + origin[0]
        cy2 = carpet_bottom * PIXELS_PER_METER + origin[1]
        self.canvas.create_rectangle(
            cx1,
            cy1,
            cx2,
            cy2,
            fill="#8B0000",
            outline="#C41E3A",
            width=2,
            tags="decor_carpet",
        )

        # ── Helper to place a table ──
        def place_table(pos_m, table_type, category, number):
            info = TABLE_TYPES[table_type]
            size_px = (info["width"], info["height"])
            x1, y1, x2, y2 = self._room_meters_to_canvas(pos_m, size_px)
            rect = self.canvas.create_draggable_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=TABLE_COLORS[category],
                width=3,
                fill=TABLE_COLORS[category],
                dpi=96,
            )
            table = Table(
                table_type=table_type,
                category=category,
                table_number=number,
            )
            item_id = self.canvas.get_item_id(rect)
            self.tables[item_id] = (rect, table)
            self._render_table_label(rect, table)

        # ── VIP / Head Table (Long Table near the altar) ──
        self.table_counter += 1
        place_table((room_cx, 4.5), "Long Table", "VIP", self.table_counter)

        # ── Bride's Side (left of aisle) ──
        # Family tables — closest to aisle (Round 8)
        bride_family_positions = [
            (8.5, 7.0),
            (8.5, 10.0),
            (8.5, 13.0),
        ]
        for pos in bride_family_positions:
            self.table_counter += 1
            place_table(pos, "Round 8", "Family", self.table_counter)

        # Friends tables — farther from aisle (Round 10)
        bride_friends_positions = [
            (4.5, 7.0),
            (4.5, 10.0),
            (4.5, 13.0),
        ]
        for pos in bride_friends_positions:
            self.table_counter += 1
            place_table(pos, "Round 10", "Friends", self.table_counter)

        # ── Groom's Side (right of aisle) — mirror layout ──
        # Family tables — closest to aisle (Round 8)
        groom_family_positions = [
            (16.5, 7.0),
            (16.5, 10.0),
            (16.5, 13.0),
        ]
        for pos in groom_family_positions:
            self.table_counter += 1
            place_table(pos, "Round 8", "Family", self.table_counter)

        # Friends tables — farther from aisle (Round 10)
        groom_friends_positions = [
            (20.5, 7.0),
            (20.5, 10.0),
            (20.5, 13.0),
        ]
        for pos in groom_friends_positions:
            self.table_counter += 1
            place_table(pos, "Round 10", "Friends", self.table_counter)

        # ── General tables at the back ──
        general_positions = [
            (5.0, 17.0),
            (10.0, 17.0),
            (15.0, 17.0),
            (20.0, 17.0),
        ]
        for pos in general_positions:
            self.table_counter += 1
            place_table(pos, "Rectangular", "General", self.table_counter)

    # ─── Table Creation ─────────────────────────────────────────────────

    def _add_table(self, table_type: str):
        """
        Add a table centered on the current view.

        center_on_canvas=True ensures it appears where the user is looking,
        even after panning. The canvas internally uses canvasx/canvasy.
        """
        self.table_counter += 1
        info = TABLE_TYPES[table_type]
        category = self.category_var.get()

        rect = self.canvas.create_draggable_rectangle(
            0,
            0,
            info["width"],
            info["height"],
            outline=TABLE_COLORS[category],
            width=3,
            fill=TABLE_COLORS[category],
            dpi=96,
            center_on_canvas=True,
        )

        table = Table(table_type=table_type, category=category, table_number=self.table_counter)
        item_id = self.canvas.get_item_id(rect)
        self.tables[item_id] = (rect, table)
        self._render_table_label(rect, table)

    def _render_table_label(self, rect: DraggableRectangle, table: Table):
        """Attach table number and seat count labels."""
        x1, y1, x2, y2 = self.canvas.coords(rect.rect)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

        t1 = self.canvas.create_text(
            cx,
            cy - 10,
            text=f"Table {table.table_number}",
            fill="black",
            font=("Arial", 11, "bold"),
            tags=f"label_{id(rect)}",
        )
        t2 = self.canvas.create_text(
            cx,
            cy + 10,
            text=f"{table.max_seats} seats",
            fill="black",
            font=("Arial", 9),
            tags=f"label_{id(rect)}",
        )
        self.canvas.attach_text_to_rectangle(t1, rect)
        self.canvas.attach_text_to_rectangle(t2, rect)

    # ─── Alignment / Distribution (using relative_pos) ──────────────────

    def _align_selected(self, mode: str):
        """Align tables relative to the room origin."""
        selected = self.canvas.get_selected()
        if len(selected) < 2:
            return
        origin = self._get_room_origin()
        DraggableRectangle.align(selected, mode=mode, relative_pos=origin)
        self.canvas.save_state()

    def _distribute_selected(self, mode: str):
        """Distribute tables evenly relative to the room origin."""
        selected = self.canvas.get_selected()
        if len(selected) < 3:
            return
        origin = self._get_room_origin()
        DraggableRectangle.distribute(selected, mode=mode, relative_pos=origin)
        self.canvas.save_state()

    # ─── Zoom ───────────────────────────────────────────────────────────

    def _zoom_in(self):
        self.canvas.zoom_in(1.25)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _zoom_out(self):
        self.canvas.zoom_out(1.25)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # ─── Coordinate Conversion (canvas <-> room-relative meters) ───────

    def _canvas_to_room_meters(self, rect: DraggableRectangle) -> Tuple[float, float]:
        """
        Get the center of a rectangle in room-relative meters.

        Uses the origin-relative pattern: subtract room origin, then
        convert from pixels to meters.
        """
        origin = self._get_room_origin()
        x1, y1, x2, y2 = self.canvas.coords(rect.rect)
        cx = ((x1 + x2) / 2 - origin[0]) / PIXELS_PER_METER
        cy = ((y1 + y2) / 2 - origin[1]) / PIXELS_PER_METER
        return (round(cx, 2), round(cy, 2))

    def _room_meters_to_canvas(
        self, pos_m: Tuple[float, float], size_px: Tuple[int, int]
    ) -> Tuple[float, float, float, float]:
        """Convert room-relative meters + size back to canvas pixel coords."""
        origin = self._get_room_origin()
        cx = pos_m[0] * PIXELS_PER_METER + origin[0]
        cy = pos_m[1] * PIXELS_PER_METER + origin[1]
        return (
            cx - size_px[0] / 2,
            cy - size_px[1] / 2,
            cx + size_px[0] / 2,
            cy + size_px[1] / 2,
        )

    # ─── Save / Load ────────────────────────────────────────────────────

    def _save_layout(self):
        """Save layout with positions in room-relative meters."""
        layout = {"venue_size": [self.room_width_m, self.room_height_m], "tables": []}

        for _, (rect, table) in self.tables.items():
            pos_m = self._canvas_to_room_meters(rect)
            layout["tables"].append(
                {
                    "number": table.table_number,
                    "type": table.table_type,
                    "category": table.category,
                    "position_m": list(pos_m),
                    "seats": table.max_seats,
                    "guests": table.guests,
                }
            )

        out = Path.home() / "seating_chart.json"
        with open(out, "w") as f:
            json.dump(layout, f, indent=2)

        total_seats = sum(t.max_seats for _, t in self.tables.values())
        print(f"Saved to: {out} ({len(self.tables)} tables, {total_seats} seats)")

    def _load_layout(self):
        """Load layout, reconstructing tables from room-relative meter positions."""
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Load Layout",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(Path.home()),
        )
        if not path:
            return

        try:
            with open(path, "r") as f:
                layout = json.load(f)

            for iid in list(self.tables.keys()):
                self.canvas.delete_draggable_rectangle(iid)
            self.tables.clear()
            self.table_counter = 0

            for td in layout["tables"]:
                self.table_counter = max(self.table_counter, td["number"])
                tt = td["type"]
                info = TABLE_TYPES[tt]
                cat = td["category"]

                x1, y1, x2, y2 = self._room_meters_to_canvas(
                    tuple(td["position_m"]), (info["width"], info["height"])
                )

                rect = self.canvas.create_draggable_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    outline=TABLE_COLORS.get(cat, "#DDA0DD"),
                    width=3,
                    fill=TABLE_COLORS.get(cat, "#DDA0DD"),
                    dpi=96,
                )

                table = Table(
                    table_type=tt,
                    category=cat,
                    table_number=td["number"],
                    guests=td.get("guests", []),
                )
                iid = self.canvas.get_item_id(rect)
                self.tables[iid] = (rect, table)
                self._render_table_label(rect, table)

            print(f"Loaded {len(self.tables)} tables from: {path}")

        except Exception as e:
            print(f"Error loading layout: {e}")

    def _export_guest_list(self):
        """Export guest assignment list with table positions in meters."""
        out = Path.home() / "guest_assignments.txt"

        with open(out, "w") as f:
            f.write("SEATING CHART - GUEST ASSIGNMENTS\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Venue: {self.room_width_m}m x {self.room_height_m}m\n")
            f.write(f"Total Tables: {len(self.tables)}\n")

            total = sum(t.max_seats for _, t in self.tables.values())
            f.write(f"Total Capacity: {total} guests\n\n")
            f.write("-" * 60 + "\n\n")

            for _, (rect, table) in sorted(self.tables.items(), key=lambda x: x[1][1].table_number):
                pos_m = self._canvas_to_room_meters(rect)
                f.write(f"TABLE {table.table_number}\n")
                f.write(f"  Type: {table.table_type}\n")
                f.write(f"  Category: {table.category}\n")
                f.write(f"  Position: ({pos_m[0]:.1f}m, {pos_m[1]:.1f}m)\n")
                f.write(f"  Capacity: {table.max_seats} seats\n")

                if table.guests:
                    f.write("  Assigned Guests:\n")
                    for i, guest in enumerate(table.guests, 1):
                        f.write(f"    {i}. {guest}\n")
                else:
                    f.write("  No guests assigned\n")
                f.write("\n")

        print(f"Guest list exported to: {out}")

    # ─── Run ────────────────────────────────────────────────────────────

    def run(self):
        print("Seating Chart Planner")
        print("=" * 50)
        print("Features:")
        print("  Tables appear at the center of the current view")
        print("  Positions stored in meters relative to the room origin")
        print("  Alignment/Distribution uses origin-relative coords")
        print("  +/- to zoom (centered on current view)")
        print("  Middle-mouse or Space+Drag to pan")
        print("  Shift+Click to multi-select, Delete to remove")
        print()
        self.root.mainloop()


def main():
    app = SeatingChartPlanner()
    app.run()


if __name__ == "__main__":
    main()
