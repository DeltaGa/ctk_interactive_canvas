#!/usr/bin/env python3
"""
Bounding Box Editor for Machine Learning

Practical annotation tool for computer vision datasets.
Features:
- Load images as canvas background with proper zoom via track_image
- Draw bounding boxes centered on the current view (center_on_canvas)
- Origin-relative coordinate export (relative_pos pattern)
- Multi-class labeling with color coding
- Export annotations in YOLO and COCO JSON formats
- Save/Load project state
- Keyboard shortcuts for efficient workflow

Dependencies: customtkinter, Pillow
"""

import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas, DraggableRectangle
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path

try:
    from PIL import Image as PILImage, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


CLASS_COLORS = {
    "person": "#FF6B6B",
    "vehicle": "#4ECDC4",
    "animal": "#FFD93D",
    "object": "#95E1D3",
    "other": "#C7CEEA",
}


class BoundingBox:
    """Represents an annotated bounding box."""

    def __init__(self, class_name: str, confidence: float = 1.0):
        self.class_name = class_name
        self.confidence = confidence


class BoundingBoxEditor:
    """
    ML annotation tool for object detection datasets.

    Demonstrates:
        - Image loading with track_image for proper zoom behaviour
        - Image boundary as coordinate origin (get_origin_pos / relative_pos)
        - View-center-aware bounding box creation (center_on_canvas)
        - Export using origin-relative coordinates (YOLO / COCO)
    """

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Bounding Box Editor - ML Annotation Tool")
        self.root.geometry("1400x900")

        self.annotations: Dict[int, Tuple[DraggableRectangle, BoundingBox]] = {}
        self.current_class = "person"
        self.image_path: Optional[str] = None
        self.image_width = 800
        self.image_height = 600
        self.bg_image_id: Optional[int] = None
        self.image_boundary_id: Optional[int] = None
        self.display_scale = 1.0

        self._setup_ui()
        self._bind_shortcuts()

    # ─── UI ─────────────────────────────────────────────────────────────

    def _setup_ui(self):
        main = ctk.CTkFrame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(main, width=250)
        left.pack(side="left", fill="y", padx=5, pady=5)
        left.pack_propagate(False)

        canvas_frame = ctk.CTkFrame(main)
        canvas_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self._create_control_panel(left)
        self._create_canvas(canvas_frame)

    def _create_control_panel(self, parent):
        ctk.CTkLabel(parent, text="Annotation Tool", font=("Arial", 18, "bold")).pack(pady=10)

        ctk.CTkButton(parent, text="Load Image", command=self._load_image, height=40).pack(
            pady=10, padx=10, fill="x"
        )

        ctk.CTkButton(
            parent, text="Add Box (A)", command=self._add_bounding_box, height=35, fg_color="#555"
        ).pack(pady=5, padx=10, fill="x")

        ctk.CTkFrame(parent, height=2, fg_color="#444").pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(parent, text="Class Selection:", font=("Arial", 14, "bold")).pack(pady=5)

        self.class_var = ctk.StringVar(value="person")
        for cls, color in CLASS_COLORS.items():
            frame = ctk.CTkFrame(parent)
            frame.pack(pady=2, padx=10, fill="x")
            ctk.CTkRadioButton(
                frame,
                text=cls.capitalize(),
                variable=self.class_var,
                value=cls,
                command=lambda c=cls: self._set_class(c),
            ).pack(side="left", padx=5)
            ctk.CTkFrame(frame, width=20, height=20, fg_color=color, corner_radius=3).pack(
                side="right", padx=5
            )

        ctk.CTkFrame(parent, height=2, fg_color="#444").pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(parent, text="Statistics:", font=("Arial", 14, "bold")).pack(pady=5)
        self.stats_text = ctk.CTkTextbox(parent, height=130)
        self.stats_text.pack(pady=5, padx=10, fill="x")
        self._update_stats()

        ctk.CTkFrame(parent, height=2, fg_color="#444").pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(parent, text="Zoom:", font=("Arial", 14, "bold")).pack(pady=5)
        zoom_frame = ctk.CTkFrame(parent)
        zoom_frame.pack(padx=10, fill="x")
        ctk.CTkButton(zoom_frame, text="+", command=self._zoom_in, width=50).pack(
            side="left", padx=2, expand=True, fill="x"
        )
        ctk.CTkButton(zoom_frame, text="-", command=self._zoom_out, width=50).pack(
            side="left", padx=2, expand=True, fill="x"
        )

        ctk.CTkFrame(parent, height=2, fg_color="#444").pack(pady=10, padx=10, fill="x")
        export = ctk.CTkFrame(parent)
        export.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(
            export,
            text="Export YOLO",
            command=lambda: self._export("yolo"),
            height=35,
            fg_color="#2E7D32",
        ).pack(pady=2, fill="x")
        ctk.CTkButton(
            export,
            text="Export COCO",
            command=lambda: self._export("coco"),
            height=35,
            fg_color="#1565C0",
        ).pack(pady=2, fill="x")
        ctk.CTkButton(
            export,
            text="Save Project",
            command=self._save_project,
            height=35,
        ).pack(pady=2, fill="x")
        ctk.CTkButton(
            export,
            text="Load Project",
            command=self._load_project,
            height=35,
            fg_color="#9C27B0",
        ).pack(pady=2, fill="x")

    def _create_canvas(self, parent):
        self.canvas = InteractiveCanvas(
            parent,
            width=1000,
            height=700,
            bg="#1a1a1a",
            select_outline_color="#00ff88",
            dpi=96,
            enable_zoom=True,
        )
        self.canvas.pack(fill="both", expand=True)

        for i, line in enumerate(
            [
                "Instructions:",
                "1. Load an image",
                "2. Select a class from the left panel",
                "3. Click 'Add Box' or press A",
                "4. Drag to position, resize as needed",
                "5. Use +/- to zoom (image scales properly)",
                "6. Export annotations when done",
            ]
        ):
            self.canvas.create_text(
                500, 50 + i * 25, text=line, fill="#888", font=("Arial", 11), tags="instructions"
            )

    def _bind_shortcuts(self):
        self.root.bind("<a>", lambda e: self._add_bounding_box())
        self.root.bind("<A>", lambda e: self._add_bounding_box())
        self.root.bind("<Control-s>", lambda e: self._save_project())
        self.root.bind("<Control-S>", lambda e: self._save_project())

    def _set_class(self, name: str):
        self.current_class = name

    # ─── Image Loading (with track_image for zoom) ─────────────────────

    def _load_image(self):
        """
        Load an image as canvas background.

        Uses canvas.track_image() so that zoom_in/zoom_out will properly
        rescale the bitmap via PIL instead of just moving its anchor point.
        """
        if not PIL_AVAILABLE:
            print("Pillow not installed. Install with: pip install Pillow")
            return

        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
        )
        if not path:
            return

        self._load_image_from_path(path)

    def _load_image_from_path(self, file_path: str):
        """Load and display an image, setting up origin tracking."""
        if not PIL_AVAILABLE:
            return

        try:
            image = PILImage.open(file_path)
            self.image_path = file_path
            self.image_width, self.image_height = image.size

            cw = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1000
            ch = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 700

            scale = min((cw - 100) / self.image_width, (ch - 100) / self.image_height, 1.0)
            self.display_scale = scale

            dw = int(self.image_width * scale)
            dh = int(self.image_height * scale)
            display_image = image.resize((dw, dh), PILImage.LANCZOS)

            self.canvas.delete("instructions")

            if self.bg_image_id is not None:
                self.canvas.untrack_image(self.bg_image_id)
                self.canvas.delete(self.bg_image_id)
            if self.image_boundary_id is not None:
                self.canvas.delete(self.image_boundary_id)

            cx, cy = cw / 2, ch / 2
            self.photo_image = ImageTk.PhotoImage(display_image)
            self.bg_image_id = self.canvas.create_image(
                cx, cy, image=self.photo_image, tags="background"
            )
            self.canvas.tag_lower("background")

            # Register the image for automatic zoom rescaling
            self.canvas.track_image(self.bg_image_id, display_image)

            # Draw a thin invisible boundary around the image to serve as
            # our coordinate origin for annotation export.
            ix1 = cx - dw / 2
            iy1 = cy - dh / 2
            ix2 = cx + dw / 2
            iy2 = cy + dh / 2
            self.image_boundary_id = self.canvas.create_rectangle(
                ix1, iy1, ix2, iy2, outline="", width=0, tags="image_boundary"
            )

            print(f"Loaded: {Path(file_path).name} ({self.image_width}x{self.image_height})")
            print(f"Display: {dw}x{dh} (scale: {scale:.2f})")

        except Exception as e:
            print(f"Error loading image: {e}")

    def _get_image_origin(self) -> List[float]:
        """
        Get the displayed image's top-left position -- our annotation origin.

        All YOLO/COCO coordinates are exported relative to this origin,
        mirroring the format_editor._canvas_get_origin_pos() pattern.
        """
        if self.image_boundary_id is None:
            return [0.0, 0.0]
        return self.canvas.get_origin_pos(self.image_boundary_id)

    # ─── Bounding Box Creation ──────────────────────────────────────────

    def _add_bounding_box(self):
        """
        Add a bounding box centered on the current view.

        center_on_canvas=True uses canvasx/canvasy internally, so the box
        always appears where the user is looking, even after panning.
        """
        if self.bg_image_id is None:
            print("Please load an image first")
            return

        rect = self.canvas.create_draggable_rectangle(
            0,
            0,
            100,
            100,
            outline=CLASS_COLORS[self.current_class],
            width=3,
            fill="",
            dpi=96,
            center_on_canvas=True,
        )

        bbox = BoundingBox(class_name=self.current_class)
        item_id = self.canvas.get_item_id(rect)
        self.annotations[item_id] = (rect, bbox)
        self._render_label(rect, bbox)
        self._update_stats()

    def _render_label(self, rect: DraggableRectangle, bbox: BoundingBox):
        """Attach a class label above the bounding box."""
        x1, y1, _, _ = self.canvas.coords(rect.rect)
        text_id = self.canvas.create_text(
            x1,
            y1 - 10,
            text=bbox.class_name,
            fill=CLASS_COLORS[bbox.class_name],
            font=("Arial", 10, "bold"),
            anchor="sw",
            tags=f"label_{id(rect)}",
        )
        self.canvas.attach_text_to_rectangle(text_id, rect)

    def _update_stats(self):
        counts: Dict[str, int] = {}
        for _, (_, bbox) in self.annotations.items():
            counts[bbox.class_name] = counts.get(bbox.class_name, 0) + 1

        text = f"Total boxes: {len(self.annotations)}\n\n"
        for cls in CLASS_COLORS:
            text += f"{cls.capitalize()}: {counts.get(cls, 0)}\n"

        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", text)

    # ─── Zoom ───────────────────────────────────────────────────────────

    def _zoom_in(self):
        """Zoom in -- tracked images auto-rescale via PIL."""
        self.canvas.zoom_in(1.25)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _zoom_out(self):
        """Zoom out -- tracked images auto-rescale via PIL."""
        self.canvas.zoom_out(1.25)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # ─── Coordinate Conversion (canvas -> image-relative) ──────────────

    def _canvas_to_image_coords(self, canvas_coords: List[float]) -> List[float]:
        """
        Convert canvas pixel coords to original image pixel coords.

        Uses the image origin (relative_pos pattern) and display_scale
        to map back to the original image's coordinate space.
        """
        origin = self._get_image_origin()
        zoom = self.canvas.zoom_level if self.canvas.enable_zoom else 1.0
        effective_scale = self.display_scale * zoom

        return [
            (canvas_coords[0] - origin[0]) / effective_scale,
            (canvas_coords[1] - origin[1]) / effective_scale,
            (canvas_coords[2] - origin[0]) / effective_scale,
            (canvas_coords[3] - origin[1]) / effective_scale,
        ]

    # ─── Export ─────────────────────────────────────────────────────────

    def _export(self, fmt: str):
        if not self.annotations:
            print("No annotations to export")
            return
        if fmt == "yolo":
            self._export_yolo()
        elif fmt == "coco":
            self._export_coco()

    def _export_yolo(self):
        """Export in YOLO format using origin-relative coordinates."""
        if not self.image_path:
            print("No image loaded")
            return

        out = Path.home() / f"{Path(self.image_path).stem}.txt"
        class_list = list(CLASS_COLORS.keys())

        with open(out, "w") as f:
            for _, (rect, bbox) in self.annotations.items():
                canvas_coords = list(self.canvas.coords(rect.rect))
                ix1, iy1, ix2, iy2 = self._canvas_to_image_coords(canvas_coords)

                x_center = ((ix1 + ix2) / 2) / self.image_width
                y_center = ((iy1 + iy2) / 2) / self.image_height
                w = (ix2 - ix1) / self.image_width
                h = (iy2 - iy1) / self.image_height
                cid = class_list.index(bbox.class_name)

                f.write(f"{cid} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")

        print(f"YOLO format exported to: {out}")

    def _export_coco(self):
        """Export in COCO JSON format using origin-relative coordinates."""
        if not self.image_path:
            print("No image loaded")
            return

        out = Path.home() / f"{Path(self.image_path).stem}_coco.json"
        class_list = list(CLASS_COLORS.keys())
        categories = [{"id": i, "name": n} for i, n in enumerate(class_list)]
        anns = []

        for ann_id, (_, (rect, bbox)) in enumerate(self.annotations.items()):
            canvas_coords = list(self.canvas.coords(rect.rect))
            ix1, iy1, ix2, iy2 = self._canvas_to_image_coords(canvas_coords)

            w, h = ix2 - ix1, iy2 - iy1
            anns.append(
                {
                    "id": ann_id,
                    "image_id": 0,
                    "category_id": class_list.index(bbox.class_name),
                    "bbox": [ix1, iy1, w, h],
                    "area": w * h,
                    "iscrowd": 0,
                }
            )

        coco = {
            "images": [
                {
                    "id": 0,
                    "file_name": Path(self.image_path).name,
                    "width": self.image_width,
                    "height": self.image_height,
                }
            ],
            "categories": categories,
            "annotations": anns,
        }

        with open(out, "w") as f:
            json.dump(coco, f, indent=2)
        print(f"COCO format exported to: {out}")

    # ─── Save / Load Project ───────────────────────────────────────────

    def _save_project(self):
        """Save all annotations with image-relative coordinates."""
        if not self.image_path:
            print("No image loaded")
            return

        project = {
            "image_path": str(self.image_path),
            "image_size": [self.image_width, self.image_height],
            "annotations": [],
        }

        for _, (rect, bbox) in self.annotations.items():
            canvas_coords = list(self.canvas.coords(rect.rect))
            img_coords = self._canvas_to_image_coords(canvas_coords)
            project["annotations"].append(
                {
                    "class": bbox.class_name,
                    "bbox_image": [round(v, 2) for v in img_coords],
                    "confidence": bbox.confidence,
                }
            )

        out = Path.home() / f"{Path(self.image_path).stem}_project.json"
        with open(out, "w") as f:
            json.dump(project, f, indent=2)
        print(f"Project saved to: {out}")

    def _load_project(self):
        """Load project and reconstruct annotations at image-relative positions."""
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Load Project",
            filetypes=[("JSON files", "*_project.json"), ("All files", "*.*")],
            initialdir=str(Path.home()),
        )
        if not path:
            return

        try:
            with open(path, "r") as f:
                project = json.load(f)

            img_path = project.get("image_path")
            if img_path and Path(img_path).exists():
                self._load_image_from_path(img_path)
            else:
                print(f"Image not found: {img_path}")
                return

            for iid in list(self.annotations.keys()):
                self.canvas.delete_draggable_rectangle(iid)
            self.annotations.clear()

            origin = self._get_image_origin()
            zoom = self.canvas.zoom_level if self.canvas.enable_zoom else 1.0
            effective_scale = self.display_scale * zoom

            for ann in project["annotations"]:
                ix1, iy1, ix2, iy2 = ann["bbox_image"]
                # Convert image coords back to canvas coords via origin + scale
                cx1 = ix1 * effective_scale + origin[0]
                cy1 = iy1 * effective_scale + origin[1]
                cx2 = ix2 * effective_scale + origin[0]
                cy2 = iy2 * effective_scale + origin[1]

                cls = ann["class"]
                rect = self.canvas.create_draggable_rectangle(
                    cx1,
                    cy1,
                    cx2,
                    cy2,
                    outline=CLASS_COLORS.get(cls, "#FFF"),
                    width=3,
                    fill="",
                    dpi=96,
                )
                bbox = BoundingBox(class_name=cls, confidence=ann.get("confidence", 1.0))
                iid = self.canvas.get_item_id(rect)
                self.annotations[iid] = (rect, bbox)
                self._render_label(rect, bbox)

            self._update_stats()
            print(f"Loaded {len(self.annotations)} annotations from: {path}")

        except Exception as e:
            print(f"Error loading project: {e}")

    # ─── Run ────────────────────────────────────────────────────────────

    def run(self):
        print("Bounding Box Editor for Machine Learning")
        print("=" * 50)
        print("Workflow:")
        print("  1. Load an image (zoom tracks the image properly)")
        print("  2. Select object class")
        print("  3. Add bounding boxes (A key / button)")
        print("  4. Boxes appear at the center of the current view")
        print("  5. +/- to zoom (image and annotations scale together)")
        print("  6. Export to YOLO or COCO format")
        print()
        if not PIL_AVAILABLE:
            print("Note: pip install Pillow  to load images")
        print()
        self.root.mainloop()


def main():
    app = BoundingBoxEditor()
    app.run()


if __name__ == "__main__":
    main()
