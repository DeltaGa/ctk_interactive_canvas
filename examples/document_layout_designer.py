#!/usr/bin/env python3
"""
Document Layout Designer

A practical document layout tool demonstrating real-world use of CTk Interactive Canvas.
Features:
- A4/US Letter/A3/Tabloid page templates with accurate dimensions
- Text box and image placeholder management
- Origin-relative coordinate system (relative_pos pattern)
- View-center-aware element creation (center_on_canvas)
- Zoom with proper image rescaling (track_image)
- Alignment and distribution tools
- PDF export with actual text rendering (requires reportlab)
- Save/Load layout to JSON

Dependencies: customtkinter, reportlab (optional), Pillow (optional)
"""

import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas, DraggableRectangle
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path

try:
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.pagesizes import A4, LETTER
    from reportlab.lib.units import mm

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image as PILImage, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


PAGE_FORMATS = {
    "A4": (210, 297),
    "US Letter": (215.9, 279.4),
    "A3": (297, 420),
    "Tabloid": (279.4, 431.8),
}

DPI = 96
SCALE_FACTOR = 2.0


class TextBox:
    """Represents a text box element in the layout."""

    def __init__(
        self,
        text: str = "Sample Text",
        font_size: int = 12,
        font_family: str = "Helvetica",
        alignment: str = "left",
    ):
        self.text = text
        self.font_size = font_size
        self.font_family = font_family
        self.alignment = alignment


class ImageBox:
    """Represents an image placeholder in the layout."""

    def __init__(self, image_path: Optional[str] = None):
        self.image_path = image_path


class DocumentLayoutDesigner:
    """
    Document layout designer with interactive canvas.

    Demonstrates:
        - Page boundary as a coordinate origin (get_origin_pos / relative_pos)
        - View-aware centering of new elements (center_on_canvas)
        - Proper image zoom via track_image
        - Professional alignment tools
        - PDF export with actual content
    """

    TEXT_OUTLINE = "#ff1694"
    IMAGE_OUTLINE = "#20ff16"

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Document Layout Designer - CTk Interactive Canvas")
        self.root.geometry("1400x900")

        self.page_format = "A4"
        self.page_width_mm, self.page_height_mm = PAGE_FORMATS[self.page_format]

        self.elements: Dict[int, Tuple[DraggableRectangle, str, object]] = {}
        self.element_counter = 0

        self._setup_ui()
        self._create_page_boundary()

    # ─── UI Setup ───────────────────────────────────────────────────────

    def _setup_ui(self):
        """Build the user interface."""
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        toolbar = ctk.CTkFrame(main_container, height=60)
        toolbar.pack(fill="x", padx=5, pady=5)

        canvas_frame = ctk.CTkFrame(main_container)
        canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._create_toolbar(toolbar)
        self._create_canvas(canvas_frame)

    def _create_toolbar(self, parent):
        """Create toolbar with element, alignment, and export controls."""
        # ── Element creation ──
        left = ctk.CTkFrame(parent)
        left.pack(side="left", padx=5)
        ctk.CTkLabel(left, text="Add:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(left, text="Text Box", command=self._add_text_box, width=100).pack(
            side="left", padx=2
        )
        ctk.CTkButton(left, text="Image Box", command=self._add_image_box, width=100).pack(
            side="left", padx=2
        )

        # ── Alignment tools ──
        mid = ctk.CTkFrame(parent)
        mid.pack(side="left", padx=20)
        ctk.CTkLabel(mid, text="Align:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        for label, mode in [
            ("Left", "start"),
            ("Center", "center"),
            ("Right", "end"),
            ("Top", "top"),
            ("Middle", "middle"),
            ("Bottom", "bottom"),
        ]:
            ctk.CTkButton(
                mid, text=label, command=lambda m=mode: self._align_selected(m), width=70
            ).pack(side="left", padx=2)

        # ── Distribute ──
        dist = ctk.CTkFrame(parent)
        dist.pack(side="left", padx=10)
        ctk.CTkLabel(dist, text="Distribute:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(
            dist, text="H", command=lambda: self._distribute_selected("horizontal"), width=40
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            dist, text="V", command=lambda: self._distribute_selected("vertical"), width=40
        ).pack(side="left", padx=2)

        # ── Zoom ──
        zoom = ctk.CTkFrame(parent)
        zoom.pack(side="left", padx=10)
        ctk.CTkButton(zoom, text="+", command=self._zoom_in, width=35).pack(side="left", padx=1)
        ctk.CTkButton(zoom, text="-", command=self._zoom_out, width=35).pack(side="left", padx=1)

        # ── Export / Save / Load ──
        right = ctk.CTkFrame(parent)
        right.pack(side="right", padx=5)
        ctk.CTkButton(
            right, text="Export PDF", command=self._export_pdf, width=100, fg_color="#2E7D32"
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            right, text="Load", command=self._load_layout, width=80, fg_color="#1565C0"
        ).pack(side="left", padx=2)
        ctk.CTkButton(right, text="Save", command=self._save_layout, width=80).pack(
            side="left", padx=2
        )

    def _create_canvas(self, parent):
        """Create the interactive canvas."""
        canvas_width = int(self.page_width_mm * DPI / 25.4 * SCALE_FACTOR) + 200
        canvas_height = int(self.page_height_mm * DPI / 25.4 * SCALE_FACTOR) + 200

        self.canvas = InteractiveCanvas(
            parent,
            width=canvas_width,
            height=canvas_height,
            bg="#2b2b2b",
            select_outline_color="#00ff88",
            dpi=DPI,
            enable_zoom=True,
        )
        self.canvas.pack(fill="both", expand=True)

    # ─── Page Boundary (Origin Rectangle) ───────────────────────────────

    def _create_page_boundary(self):
        """
        Draw the page boundary and store it as our coordinate origin.

        All element positions are stored relative to this rectangle's
        top-left corner, using the get_origin_pos / relative_pos pattern
        (mirrors format_editor._canvas_get_origin_pos).
        """
        page_w_px = self.page_width_mm * DPI / 25.4 * SCALE_FACTOR
        page_h_px = self.page_height_mm * DPI / 25.4 * SCALE_FACTOR

        canvas_cx = self.canvas.winfo_reqwidth() / 2
        canvas_cy = self.canvas.winfo_reqheight() / 2

        x1 = canvas_cx - page_w_px / 2
        y1 = canvas_cy - page_h_px / 2
        x2 = canvas_cx + page_w_px / 2
        y2 = canvas_cy + page_h_px / 2

        self.page_rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="white", width=2, fill="white", tags="page_boundary"
        )

        title = f"{self.page_format} ({self.page_width_mm:.1f}mm x {self.page_height_mm:.1f}mm)"
        self.canvas.create_text(
            canvas_cx,
            y1 - 20,
            text=title,
            fill="white",
            font=("Arial", 12, "bold"),
            tags="page_title",
        )

    def _get_page_origin(self) -> List[float]:
        """
        Get the page boundary's top-left position -- our coordinate origin.

        This mirrors format_editor._canvas_get_origin_pos() and is used
        as the relative_pos argument for DraggableRectangle position methods.
        """
        return self.canvas.get_origin_pos(self.page_rect_id)

    # ─── Element Creation ───────────────────────────────────────────────

    def _add_text_box(self):
        """
        Add a text box centered on the current view.

        Uses center_on_canvas=True which internally calls canvasx/canvasy
        to find the TRUE visible center, even after panning.
        """
        self.element_counter += 1

        rect = self.canvas.create_draggable_rectangle(
            0,
            0,
            150,
            50,
            outline=self.TEXT_OUTLINE,
            width=2,
            fill="",
            dpi=DPI,
            center_on_canvas=True,
        )

        text_element = TextBox(text=f"Text Box {self.element_counter}")
        item_id = self.canvas.get_item_id(rect)
        self.elements[item_id] = (rect, "text", text_element)
        self._render_label(rect, text_element.text, self.TEXT_OUTLINE)

    def _add_image_box(self):
        """Add an image placeholder centered on the current view."""
        self.element_counter += 1

        rect = self.canvas.create_draggable_rectangle(
            0,
            0,
            100,
            100,
            outline=self.IMAGE_OUTLINE,
            width=2,
            fill="",
            dpi=DPI,
            center_on_canvas=True,
        )

        image_element = ImageBox()
        item_id = self.canvas.get_item_id(rect)
        self.elements[item_id] = (rect, "image", image_element)
        self._render_label(rect, "[IMAGE]", self.IMAGE_OUTLINE, bold=True)

    def _render_label(self, rect: DraggableRectangle, text: str, color: str, bold: bool = False):
        """Attach a centered text label to a rectangle so it moves with it."""
        x0, y0, x1, y1 = self.canvas.coords(rect.rect)
        font = ("Arial", 10, "bold") if bold else ("Arial", 10)
        text_id = self.canvas.create_text(
            (x0 + x1) / 2,
            (y0 + y1) / 2,
            text=text,
            fill=color,
            font=font,
            tags=f"preview_{id(rect)}",
        )
        self.canvas.attach_text_to_rectangle(text_id, rect)

    # ─── Alignment / Distribution (using relative_pos) ──────────────────

    def _align_selected(self, mode: str):
        """
        Align selected elements using the page origin as relative_pos.

        By passing the page origin, alignment operates in page-relative
        coordinate space -- consistent regardless of canvas pan/zoom.
        """
        selected = self.canvas.get_selected()
        if len(selected) < 2:
            return
        origin = self._get_page_origin()
        DraggableRectangle.align(selected, mode=mode, relative_pos=origin)
        self.canvas.save_state()

    def _distribute_selected(self, mode: str):
        """Distribute selected elements evenly relative to the page origin."""
        selected = self.canvas.get_selected()
        if len(selected) < 3:
            return
        origin = self._get_page_origin()
        DraggableRectangle.distribute(selected, mode=mode, relative_pos=origin)
        self.canvas.save_state()

    # ─── Zoom ───────────────────────────────────────────────────────────

    def _zoom_in(self):
        """Zoom in centered on the current view. Images auto-rescale."""
        self.canvas.zoom_in(1.25)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _zoom_out(self):
        """Zoom out centered on the current view. Images auto-rescale."""
        self.canvas.zoom_out(1.25)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # ─── Coordinate Conversion (canvas <-> page-relative mm) ───────────

    def _canvas_to_page_mm(self, coords: List[float]) -> List[float]:
        """
        Convert canvas pixel coordinates to page-relative millimeters.

        Subtracts the page origin, then converts px -> mm using DPI and scale.
        """
        origin = self._get_page_origin()
        px_per_mm = DPI / 25.4 * SCALE_FACTOR
        return [
            (coords[0] - origin[0]) / px_per_mm,
            (coords[1] - origin[1]) / px_per_mm,
            (coords[2] - origin[0]) / px_per_mm,
            (coords[3] - origin[1]) / px_per_mm,
        ]

    def _page_mm_to_canvas(self, mm_coords: List[float]) -> List[float]:
        """Convert page-relative mm back to canvas pixels (adds origin offset)."""
        origin = self._get_page_origin()
        px_per_mm = DPI / 25.4 * SCALE_FACTOR
        return [
            mm_coords[0] * px_per_mm + origin[0],
            mm_coords[1] * px_per_mm + origin[1],
            mm_coords[2] * px_per_mm + origin[0],
            mm_coords[3] * px_per_mm + origin[1],
        ]

    # ─── Save / Load ────────────────────────────────────────────────────

    def _save_layout(self):
        """Save layout to JSON with page-relative mm coordinates."""
        layout = {"page_format": self.page_format, "elements": []}

        for item_id, (rect, elem_type, elem_data) in self.elements.items():
            canvas_coords = list(self.canvas.coords(rect.rect))
            mm_coords = self._canvas_to_page_mm(canvas_coords)

            entry = {"type": elem_type, "position_mm": [round(v, 2) for v in mm_coords]}
            if elem_type == "text":
                entry["text"] = elem_data.text
                entry["font_size"] = elem_data.font_size
                entry["alignment"] = elem_data.alignment
            layout["elements"].append(entry)

        out = Path.home() / "document_layout.json"
        with open(out, "w") as f:
            json.dump(layout, f, indent=2)
        print(f"Layout saved to: {out}")

    def _load_layout(self):
        """Load layout from JSON, restoring elements at their page-relative positions."""
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

            for iid in list(self.elements.keys()):
                self.canvas.delete_draggable_rectangle(iid)
            self.elements.clear()
            self.element_counter = 0

            for elem in layout["elements"]:
                canvas_coords = self._page_mm_to_canvas(elem["position_mm"])
                x1, y1, x2, y2 = canvas_coords
                self.element_counter += 1

                if elem["type"] == "text":
                    text_data = TextBox(
                        text=elem.get("text", f"Text Box {self.element_counter}"),
                        font_size=elem.get("font_size", 12),
                        alignment=elem.get("alignment", "left"),
                    )
                    rect = self.canvas.create_draggable_rectangle(
                        x1, y1, x2, y2, outline=self.TEXT_OUTLINE, width=2, fill="", dpi=DPI
                    )
                    iid = self.canvas.get_item_id(rect)
                    self.elements[iid] = (rect, "text", text_data)
                    self._render_label(rect, text_data.text, self.TEXT_OUTLINE)

                elif elem["type"] == "image":
                    rect = self.canvas.create_draggable_rectangle(
                        x1, y1, x2, y2, outline=self.IMAGE_OUTLINE, width=2, fill="", dpi=DPI
                    )
                    iid = self.canvas.get_item_id(rect)
                    self.elements[iid] = (rect, "image", ImageBox())
                    self._render_label(rect, "[IMAGE]", self.IMAGE_OUTLINE, bold=True)

            print(f"Loaded {len(self.elements)} elements from: {path}")

        except Exception as e:
            print(f"Error loading layout: {e}")

    # ─── PDF Export ─────────────────────────────────────────────────────

    def _export_pdf(self):
        """Export layout to PDF using page-relative mm coordinates."""
        if not REPORTLAB_AVAILABLE:
            print("ReportLab not installed. Install with: pip install reportlab")
            return

        out = Path.home() / "document_layout.pdf"
        page_size = A4 if self.page_format == "A4" else LETTER
        pdf = pdf_canvas.Canvas(str(out), pagesize=page_size)

        for item_id, (rect, elem_type, elem_data) in self.elements.items():
            canvas_coords = list(self.canvas.coords(rect.rect))
            rel = self._canvas_to_page_mm(canvas_coords)

            if elem_type == "text":
                pdf.setFont("Helvetica", elem_data.font_size)
                pdf.drawString(rel[0] * mm, (self.page_height_mm - rel[1] - 5) * mm, elem_data.text)
            elif elem_type == "image":
                pdf.rect(
                    rel[0] * mm,
                    (self.page_height_mm - rel[3]) * mm,
                    (rel[2] - rel[0]) * mm,
                    (rel[3] - rel[1]) * mm,
                    stroke=1,
                    fill=0,
                )

        pdf.save()
        print(f"PDF exported to: {out}")

    # ─── Run ────────────────────────────────────────────────────────────

    def run(self):
        """Start the application."""
        print("Document Layout Designer")
        print("=" * 55)
        print("Controls:")
        print("  Click 'Text Box' / 'Image Box' to add elements")
        print("  Elements appear at the center of the current view")
        print("  Drag to position, resize via bottom-right handle")
        print("  Shift+Click to multi-select, then use Align/Distribute")
        print("  +/- buttons to zoom (images scale properly)")
        print("  Middle-mouse or Space+Drag to pan")
        print("  Coordinates are stored relative to the page boundary")
        print()
        if not REPORTLAB_AVAILABLE:
            print("Note: pip install reportlab  for PDF export")
        print()
        self.root.mainloop()


def main():
    app = DocumentLayoutDesigner()
    app.run()


if __name__ == "__main__":
    main()
