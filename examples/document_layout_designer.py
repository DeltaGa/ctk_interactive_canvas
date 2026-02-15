#!/usr/bin/env python3
"""
Document Layout Designer

A practical document layout tool demonstrating real-world use of CTk Interactive Canvas.
Features:
- A4/US Letter page templates
- Text box placement with live preview
- Image placeholder boxes
- Alignment and distribution tools
- Export to PDF with actual text rendering
- Professional print layout workflow

Dependencies: customtkinter, reportlab, Pillow
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
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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
        - Page boundary visualization
        - Text and image box management
        - Professional alignment tools
        - PDF export with actual content
    """

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
        """Create toolbar with controls."""
        left_section = ctk.CTkFrame(parent)
        left_section.pack(side="left", padx=5)

        ctk.CTkLabel(left_section, text="Add:", font=("Arial", 12, "bold")).pack(
            side="left", padx=5
        )

        ctk.CTkButton(left_section, text="Text Box", command=self._add_text_box, width=100).pack(
            side="left", padx=2
        )

        ctk.CTkButton(left_section, text="Image Box", command=self._add_image_box, width=100).pack(
            side="left", padx=2
        )

        middle_section = ctk.CTkFrame(parent)
        middle_section.pack(side="left", padx=20)

        ctk.CTkLabel(middle_section, text="Align:", font=("Arial", 12, "bold")).pack(
            side="left", padx=5
        )

        align_buttons = [
            ("Left", lambda: self._align_selected("start")),
            ("Center", lambda: self._align_selected("center")),
            ("Right", lambda: self._align_selected("end")),
            ("Top", lambda: self._align_selected("top")),
            ("Middle", lambda: self._align_selected("middle")),
            ("Bottom", lambda: self._align_selected("bottom")),
        ]

        for text, cmd in align_buttons:
            ctk.CTkButton(middle_section, text=text, command=cmd, width=70).pack(
                side="left", padx=2
            )

        right_section = ctk.CTkFrame(parent)
        right_section.pack(side="right", padx=5)

        ctk.CTkButton(
            right_section,
            text="Export PDF",
            command=self._export_pdf,
            width=100,
            fg_color="#2E7D32",
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            right_section,
            text="Load Layout",
            command=self._load_layout,
            width=100,
            fg_color="#1565C0",
        ).pack(side="left", padx=2)

        ctk.CTkButton(right_section, text="Save Layout", command=self._save_layout, width=100).pack(
            side="left", padx=2
        )

    def _create_canvas(self, parent):
        """Create the interactive canvas with page boundary."""
        canvas_width = int(self.page_width_mm * DPI / 25.4 * SCALE_FACTOR) + 200
        canvas_height = int(self.page_height_mm * DPI / 25.4 * SCALE_FACTOR) + 200

        self.canvas = InteractiveCanvas(
            parent,
            width=canvas_width,
            height=canvas_height,
            bg="#2b2b2b",
            select_outline_color="#00ff88",
            dpi=DPI,
        )
        self.canvas.pack(fill="both", expand=True)

    def _create_page_boundary(self):
        """Draw page boundary as non-draggable rectangle."""
        page_width_px = self.page_width_mm * DPI / 25.4 * SCALE_FACTOR
        page_height_px = self.page_height_mm * DPI / 25.4 * SCALE_FACTOR

        canvas_center_x = self.canvas.winfo_reqwidth() / 2
        canvas_center_y = self.canvas.winfo_reqheight() / 2

        x1 = canvas_center_x - page_width_px / 2
        y1 = canvas_center_y - page_height_px / 2
        x2 = canvas_center_x + page_width_px / 2
        y2 = canvas_center_y + page_height_px / 2

        self.page_rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="white", width=2, fill="white", tags="page_boundary"
        )

        self.page_coords = (x1, y1, x2, y2)

        title_text = (
            f"{self.page_format} ({self.page_width_mm:.1f}mm × {self.page_height_mm:.1f}mm)"
        )
        self.canvas.create_text(
            canvas_center_x,
            y1 - 20,
            text=title_text,
            fill="white",
            font=("Arial", 12, "bold"),
            tags="page_title",
        )

    def _add_text_box(self):
        """Add a text box to the layout."""
        self.element_counter += 1

        box_width = 150
        box_height = 50

        rect = self.canvas.create_draggable_rectangle(
            0,
            0,
            box_width,
            box_height,
            outline="#ff1694",
            width=2,
            fill="",
            dpi=DPI,
            center_on_canvas=True,
        )

        text_element = TextBox(
            text=f"Text Box {self.element_counter}", font_size=12, alignment="left"
        )

        item_id = self.canvas.get_item_id(rect)
        self.elements[item_id] = (rect, "text", text_element)

        self._render_text_preview(rect, text_element)

    def _add_image_box(self):
        """Add an image placeholder to the layout."""
        self.element_counter += 1

        box_width = 100
        box_height = 100

        rect = self.canvas.create_draggable_rectangle(
            0,
            0,
            box_width,
            box_height,
            outline="#20ff16",
            width=2,
            fill="",
            dpi=DPI,
            center_on_canvas=True,
        )

        image_element = ImageBox()

        item_id = self.canvas.get_item_id(rect)
        self.elements[item_id] = (rect, "image", image_element)

        self._render_image_preview(rect)

    def _render_text_preview(self, rect: DraggableRectangle, text_box: TextBox):
        """Render text preview inside rectangle."""
        coords = self.canvas.coords(rect.rect)
        x1, y1, x2, y2 = coords

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        text_id = self.canvas.create_text(
            center_x,
            center_y,
            text=text_box.text,
            fill="#ff1694",
            font=("Arial", 10),
            tags=f"preview_{id(rect)}",
        )

        self.canvas.attach_text_to_rectangle(text_id, rect)

    def _render_image_preview(self, rect: DraggableRectangle):
        """Render image placeholder icon."""
        coords = self.canvas.coords(rect.rect)
        x1, y1, x2, y2 = coords

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        text_id = self.canvas.create_text(
            center_x,
            center_y,
            text="[IMAGE]",
            fill="#20ff16",
            font=("Arial", 10, "bold"),
            tags=f"preview_{id(rect)}",
        )

        self.canvas.attach_text_to_rectangle(text_id, rect)
        x1, y1, x2, y2 = coords

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        self.canvas.create_text(
            center_x,
            center_y,
            text="[IMAGE]",
            fill="#20ff16",
            font=("Arial", 10, "bold"),
            tags=f"preview_{id(rect)}",
        )

    def _align_selected(self, mode: str):
        """Align selected elements."""
        selected = self.canvas.get_selected()
        if len(selected) < 2:
            return

        DraggableRectangle.align(selected, mode=mode)

    def _load_layout(self):
        """Load layout from JSON file."""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Load Layout",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(Path.home()),
        )

        if not file_path:
            return

        try:
            with open(file_path, "r") as f:
                layout_data = json.load(f)

            for item_id in list(self.elements.keys()):
                rect, _, _ = self.elements[item_id]
                self.canvas.delete_draggable_rectangle(item_id)

            self.elements.clear()
            self.element_counter = 0

            px1, py1, px2, py2 = self.page_coords

            for elem_info in layout_data["elements"]:
                rel_x1, rel_y1, rel_x2, rel_y2 = elem_info["position_mm"]

                x1 = px1 + (rel_x1 / self.page_width_mm) * (px2 - px1)
                y1 = py1 + (rel_y1 / self.page_height_mm) * (py2 - py1)
                x2 = px1 + (rel_x2 / self.page_width_mm) * (px2 - px1)
                y2 = py1 + (rel_y2 / self.page_height_mm) * (py2 - py1)

                self.element_counter += 1

                if elem_info["type"] == "text":
                    rect = self.canvas.create_draggable_rectangle(
                        x1, y1, x2, y2, outline="#ff1694", width=2, fill="", dpi=DPI
                    )

                    text_element = TextBox(
                        text=elem_info.get("text", f"Text Box {self.element_counter}"),
                        font_size=elem_info.get("font_size", 12),
                        alignment=elem_info.get("alignment", "left"),
                    )

                    item_id = self.canvas.get_item_id(rect)
                    self.elements[item_id] = (rect, "text", text_element)
                    self._render_text_preview(rect, text_element)

                elif elem_info["type"] == "image":
                    rect = self.canvas.create_draggable_rectangle(
                        x1, y1, x2, y2, outline="#20ff16", width=2, fill="", dpi=DPI
                    )

                    image_element = ImageBox()

                    item_id = self.canvas.get_item_id(rect)
                    self.elements[item_id] = (rect, "image", image_element)
                    self._render_image_preview(rect)

            print(f"Layout loaded from: {file_path}")
            print(f"Loaded {len(self.elements)} elements")

        except Exception as e:
            print(f"Error loading layout: {e}")

    def _save_layout(self):
        """Save layout to JSON file."""
        layout_data = {"page_format": self.page_format, "elements": []}

        for item_id, (rect, elem_type, elem_data) in self.elements.items():
            x1, y1, x2, y2 = self.canvas.coords(rect.rect)

            px1, py1, px2, py2 = self.page_coords

            rel_x1 = (x1 - px1) / (px2 - px1) * self.page_width_mm
            rel_y1 = (y1 - py1) / (py2 - py1) * self.page_height_mm
            rel_x2 = (x2 - px1) / (px2 - px1) * self.page_width_mm
            rel_y2 = (y2 - py1) / (py2 - py1) * self.page_height_mm

            element_info = {"type": elem_type, "position_mm": [rel_x1, rel_y1, rel_x2, rel_y2]}

            if elem_type == "text":
                element_info["text"] = elem_data.text
                element_info["font_size"] = elem_data.font_size
                element_info["alignment"] = elem_data.alignment

            layout_data["elements"].append(element_info)

        file_path = Path.home() / "document_layout.json"
        with open(file_path, "w") as f:
            json.dump(layout_data, f, indent=2)

        print(f"Layout saved to: {file_path}")

    def _export_pdf(self):
        """Export layout to PDF with actual text rendering."""
        if not REPORTLAB_AVAILABLE:
            print("ReportLab not installed. Install with: pip install reportlab")
            return

        output_path = Path.home() / "document_layout.pdf"

        page_size = A4 if self.page_format == "A4" else LETTER

        pdf = pdf_canvas.Canvas(str(output_path), pagesize=page_size)

        for item_id, (rect, elem_type, elem_data) in self.elements.items():
            x1, y1, x2, y2 = self.canvas.coords(rect.rect)

            px1, py1, px2, py2 = self.page_coords

            rel_x1 = (x1 - px1) / (px2 - px1) * self.page_width_mm
            rel_y1 = (y1 - py1) / (py2 - py1) * self.page_height_mm
            rel_x2 = (x2 - px1) / (px2 - px1) * self.page_width_mm
            rel_y2 = (y2 - py1) / (py2 - py1) * self.page_height_mm

            if elem_type == "text":
                pdf.setFont("Helvetica", elem_data.font_size)
                pdf.drawString(rel_x1 * mm, (self.page_height_mm - rel_y1 - 5) * mm, elem_data.text)
            elif elem_type == "image":
                pdf.rect(
                    rel_x1 * mm,
                    (self.page_height_mm - rel_y2) * mm,
                    (rel_x2 - rel_x1) * mm,
                    (rel_y2 - rel_y1) * mm,
                    stroke=1,
                    fill=0,
                )

        pdf.save()
        print(f"PDF exported to: {output_path}")

    def run(self):
        """Start the application."""
        print("Document Layout Designer")
        print("=" * 50)
        print("Controls:")
        print("  - Add text/image boxes")
        print("  - Drag to position")
        print("  - Shift+Drag to constrain angles")
        print("  - Ctrl+Resize to resize from center")
        print("  - Select multiple and align")
        print("  - Export to PDF with actual content")
        print("")
        if not REPORTLAB_AVAILABLE:
            print("Note: Install 'reportlab' for PDF export")
            print("  pip install reportlab")
        print("")

        self.root.mainloop()


def main():
    """Entry point."""
    app = DocumentLayoutDesigner()
    app.run()


if __name__ == "__main__":
    main()
