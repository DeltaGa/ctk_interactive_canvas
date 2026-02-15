#!/usr/bin/env python3
"""
Seating Chart Planner

Event planning tool for arranging seats, tables, and guest assignments.
Features:
- Drag-and-drop table arrangement
- Guest name assignment
- Different table shapes and sizes
- Distance measurement
- Export seating arrangements
- Real-world event planning workflow

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

TABLE_COLORS = {"VIP": "#FFD700", "Family": "#87CEEB", "Friends": "#98FB98", "General": "#DDA0DD"}

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
        - Spatial planning and layout
        - Distance measurement
        - Category-based organization
        - Export for printing
        - Professional event management
    """

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Seating Chart Planner - Event Planning Tool")
        self.root.geometry("1400x900")

        self.tables: Dict[int, Tuple[DraggableRectangle, Table]] = {}
        self.table_counter = 0
        self.room_width_m = 20
        self.room_height_m = 15

        self._setup_ui()
        self._create_room_boundary()

    def _setup_ui(self):
        """Build the user interface."""
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        left_panel = ctk.CTkFrame(main_container, width=280)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)
        left_panel.pack_propagate(False)

        canvas_container = ctk.CTkFrame(main_container)
        canvas_container.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self._create_control_panel(left_panel)
        self._create_canvas(canvas_container)

    def _create_control_panel(self, parent):
        """Create left control panel."""
        title = ctk.CTkLabel(parent, text="Seating Planner", font=("Arial", 18, "bold"))
        title.pack(pady=10)

        venue_frame = ctk.CTkFrame(parent)
        venue_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(venue_frame, text="Venue Dimensions:", font=("Arial", 12, "bold")).pack(pady=5)

        ctk.CTkLabel(
            venue_frame, text=f"{self.room_width_m}m × {self.room_height_m}m", font=("Arial", 11)
        ).pack()

        separator1 = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator1.pack(pady=10, padx=10, fill="x")

        table_label = ctk.CTkLabel(parent, text="Add Table:", font=("Arial", 14, "bold"))
        table_label.pack(pady=5)

        for table_type in TABLE_TYPES.keys():
            ctk.CTkButton(
                parent, text=table_type, command=lambda t=table_type: self._add_table(t), height=35
            ).pack(pady=2, padx=10, fill="x")

        separator2 = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator2.pack(pady=10, padx=10, fill="x")

        category_label = ctk.CTkLabel(parent, text="Table Category:", font=("Arial", 14, "bold"))
        category_label.pack(pady=5)

        self.category_var = ctk.StringVar(value="General")

        for category, color in TABLE_COLORS.items():
            frame = ctk.CTkFrame(parent)
            frame.pack(pady=2, padx=10, fill="x")

            radio = ctk.CTkRadioButton(
                frame, text=category, variable=self.category_var, value=category
            )
            radio.pack(side="left", padx=5)

            color_box = ctk.CTkFrame(frame, width=20, height=20, fg_color=color, corner_radius=3)
            color_box.pack(side="right", padx=5)

        separator3 = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator3.pack(pady=10, padx=10, fill="x")

        tools_label = ctk.CTkLabel(parent, text="Tools:", font=("Arial", 14, "bold"))
        tools_label.pack(pady=5)

        ctk.CTkButton(
            parent, text="Align Tables", command=lambda: self._align_selected("center"), height=35
        ).pack(pady=2, padx=10, fill="x")

        ctk.CTkButton(
            parent,
            text="Distribute Evenly",
            command=lambda: self._distribute_selected("horizontal"),
            height=35,
        ).pack(pady=2, padx=10, fill="x")

        separator4 = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator4.pack(pady=10, padx=10, fill="x")

        export_frame = ctk.CTkFrame(parent)
        export_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkButton(
            export_frame,
            text="Save Layout",
            command=self._save_layout,
            height=40,
            fg_color="#2E7D32",
        ).pack(pady=2, fill="x")

        ctk.CTkButton(
            export_frame, text="Export Guest List", command=self._export_guest_list, height=40
        ).pack(pady=2, fill="x")

    def _create_canvas(self, parent):
        """Create the interactive canvas."""
        self.canvas = InteractiveCanvas(
            parent, width=1000, height=750, bg="#2b2b2b", select_outline_color="#00ff88", dpi=96
        )
        self.canvas.pack(fill="both", expand=True)

    def _create_room_boundary(self):
        """Draw room boundary."""
        room_width_px = self.room_width_m * PIXELS_PER_METER
        room_height_px = self.room_height_m * PIXELS_PER_METER

        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()

        x1 = (canvas_width - room_width_px) / 2
        y1 = (canvas_height - room_height_px) / 2
        x2 = x1 + room_width_px
        y2 = y1 + room_height_px

        self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="white", width=2, dash=(10, 5), tags="room_boundary"
        )

        self.room_coords = (x1, y1, x2, y2)

        title_text = f"Event Space ({self.room_width_m}m × {self.room_height_m}m)"
        self.canvas.create_text(
            (x1 + x2) / 2,
            y1 - 20,
            text=title_text,
            fill="white",
            font=("Arial", 14, "bold"),
            tags="room_title",
        )

        for i in range(0, self.room_width_m + 1, 5):
            x = x1 + i * PIXELS_PER_METER
            self.canvas.create_line(x, y2, x, y2 + 10, fill="#666666", tags="scale")
            self.canvas.create_text(
                x, y2 + 20, text=f"{i}m", fill="#888888", font=("Arial", 9), tags="scale"
            )

        for i in range(0, self.room_height_m + 1, 5):
            y = y1 + i * PIXELS_PER_METER
            self.canvas.create_line(x1 - 10, y, x1, y, fill="#666666", tags="scale")
            self.canvas.create_text(
                x1 - 25, y, text=f"{i}m", fill="#888888", font=("Arial", 9), tags="scale"
            )

    def _add_table(self, table_type: str):
        """Add a table to the layout."""
        self.table_counter += 1

        table_info = TABLE_TYPES[table_type]
        category = self.category_var.get()

        rx1, ry1, rx2, ry2 = self.room_coords
        center_x = (rx1 + rx2) / 2
        center_y = (ry1 + ry2) / 2

        width_px = table_info["width"]
        height_px = table_info["height"]

        rect = self.canvas.create_draggable_rectangle(
            center_x - width_px / 2,
            center_y - height_px / 2,
            center_x + width_px / 2,
            center_y + height_px / 2,
            outline=TABLE_COLORS[category],
            width=3,
            fill=TABLE_COLORS[category] + "40",
            dpi=96,
        )

        table = Table(table_type=table_type, category=category, table_number=self.table_counter)

        item_id = self.canvas.get_item_id(rect)
        self.tables[item_id] = (rect, table)

        self._render_table_label(rect, table)

    def _render_table_label(self, rect: DraggableRectangle, table: Table):
        """Render table information."""
        coords = self.canvas.coords(rect.rect)
        x1, y1, x2, y2 = coords

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        self.canvas.create_text(
            center_x,
            center_y - 10,
            text=f"Table {table.table_number}",
            fill="black",
            font=("Arial", 11, "bold"),
            tags=f"label_{id(rect)}",
        )

        self.canvas.create_text(
            center_x,
            center_y + 10,
            text=f"{table.max_seats} seats",
            fill="black",
            font=("Arial", 9),
            tags=f"label_{id(rect)}",
        )

    def _align_selected(self, mode: str):
        """Align selected tables."""
        selected = self.canvas.get_selected()
        if len(selected) < 2:
            return

        DraggableRectangle.align(selected, mode=mode)

    def _distribute_selected(self, mode: str):
        """Distribute selected tables evenly."""
        selected = self.canvas.get_selected()
        if len(selected) < 3:
            return

        DraggableRectangle.distribute(selected, mode=mode)

    def _save_layout(self):
        """Save seating arrangement to JSON."""
        layout_data = {"venue_size": [self.room_width_m, self.room_height_m], "tables": []}

        for item_id, (rect, table) in self.tables.items():
            coords = self.canvas.coords(rect.rect)
            x1, y1, x2, y2 = coords

            rx1, ry1, _, _ = self.room_coords

            pos_x_m = (x1 + x2) / 2 - rx1
            pos_y_m = (y1 + y2) / 2 - ry1
            pos_x_m /= PIXELS_PER_METER
            pos_y_m /= PIXELS_PER_METER

            table_data = {
                "number": table.table_number,
                "type": table.table_type,
                "category": table.category,
                "position_m": [round(pos_x_m, 2), round(pos_y_m, 2)],
                "seats": table.max_seats,
                "guests": table.guests,
            }
            layout_data["tables"].append(table_data)

        output_path = Path.home() / "seating_chart.json"
        with open(output_path, "w") as f:
            json.dump(layout_data, f, indent=2)

        print(f"Seating chart saved to: {output_path}")
        print(f"Total tables: {len(self.tables)}")
        print(f"Total capacity: {sum(t.max_seats for _, t in self.tables.values())} guests")

    def _export_guest_list(self):
        """Export guest assignment list."""
        output_path = Path.home() / "guest_assignments.txt"

        with open(output_path, "w") as f:
            f.write("SEATING CHART - GUEST ASSIGNMENTS\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Venue: {self.room_width_m}m × {self.room_height_m}m\n")
            f.write(f"Total Tables: {len(self.tables)}\n")
            f.write(
                f"Total Capacity: {sum(t.max_seats for _, t in self.tables.values())} guests\n\n"
            )

            f.write("-" * 60 + "\n\n")

            for item_id, (rect, table) in sorted(
                self.tables.items(), key=lambda x: x[1][1].table_number
            ):
                f.write(f"TABLE {table.table_number}\n")
                f.write(f"  Type: {table.table_type}\n")
                f.write(f"  Category: {table.category}\n")
                f.write(f"  Capacity: {table.max_seats} seats\n")

                if table.guests:
                    f.write(f"  Assigned Guests:\n")
                    for i, guest in enumerate(table.guests, 1):
                        f.write(f"    {i}. {guest}\n")
                else:
                    f.write(f"  No guests assigned\n")

                f.write("\n")

        print(f"Guest list exported to: {output_path}")

    def run(self):
        """Start the application."""
        print("Seating Chart Planner")
        print("=" * 50)
        print("Features:")
        print("  - Drag tables to arrange layout")
        print("  - Choose table types and categories")
        print("  - Align and distribute for clean layouts")
        print("  - Save seating arrangements")
        print("  - Export guest assignments")
        print("")
        print("Controls:")
        print("  - Drag: Move tables")
        print("  - Multi-select: Shift+click or drag-select")
        print("  - Delete: Remove selected tables")
        print("")

        self.root.mainloop()


def main():
    """Entry point."""
    app = SeatingChartPlanner()
    app.run()


if __name__ == "__main__":
    main()
