#!/usr/bin/env python3
"""
Bounding Box Editor for Machine Learning

Practical annotation tool for computer vision datasets.
Features:
- Load images as canvas background
- Draw bounding boxes around objects
- Multi-class labeling with color coding
- Export annotations in YOLO/COCO format
- Keyboard shortcuts for efficiency
- Real-world ML workflow

Dependencies: customtkinter, Pillow
"""

import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas, DraggableRectangle
import json
from typing import Dict, List, Tuple
from pathlib import Path

try:
    from PIL import Image, ImageTk

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
        - Image loading as canvas background
        - Precise bounding box placement
        - Multi-class annotation
        - Export to standard ML formats
        - Efficient keyboard workflow
    """

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Bounding Box Editor - ML Annotation Tool")
        self.root.geometry("1400x900")

        self.annotations: Dict[int, Tuple[DraggableRectangle, BoundingBox]] = {}
        self.current_class = "person"
        self.image_path = None
        self.image_width = 800
        self.image_height = 600
        self.bg_image_id = None

        self._setup_ui()
        self._bind_shortcuts()

    def _setup_ui(self):
        """Build the user interface."""
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        left_panel = ctk.CTkFrame(main_container, width=250)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)
        left_panel.pack_propagate(False)

        canvas_container = ctk.CTkFrame(main_container)
        canvas_container.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self._create_control_panel(left_panel)
        self._create_canvas(canvas_container)

    def _create_control_panel(self, parent):
        """Create left control panel."""
        title = ctk.CTkLabel(parent, text="Annotation Tool", font=("Arial", 18, "bold"))
        title.pack(pady=10)

        load_btn = ctk.CTkButton(parent, text="Load Image", command=self._load_image, height=40)
        load_btn.pack(pady=10, padx=10, fill="x")

        separator1 = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator1.pack(pady=15, padx=10, fill="x")

        class_label = ctk.CTkLabel(parent, text="Class Selection:", font=("Arial", 14, "bold"))
        class_label.pack(pady=5)

        self.class_var = ctk.StringVar(value="person")

        for class_name, color in CLASS_COLORS.items():
            frame = ctk.CTkFrame(parent)
            frame.pack(pady=2, padx=10, fill="x")

            radio = ctk.CTkRadioButton(
                frame,
                text=class_name.capitalize(),
                variable=self.class_var,
                value=class_name,
                command=lambda c=class_name: self._set_current_class(c),
            )
            radio.pack(side="left", padx=5)

            color_indicator = ctk.CTkFrame(
                frame, width=20, height=20, fg_color=color, corner_radius=3
            )
            color_indicator.pack(side="right", padx=5)

        separator2 = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator2.pack(pady=15, padx=10, fill="x")

        stats_label = ctk.CTkLabel(parent, text="Statistics:", font=("Arial", 14, "bold"))
        stats_label.pack(pady=5)

        self.stats_text = ctk.CTkTextbox(parent, height=150)
        self.stats_text.pack(pady=5, padx=10, fill="x")
        self._update_stats()

        separator3 = ctk.CTkFrame(parent, height=2, fg_color="#444444")
        separator3.pack(pady=15, padx=10, fill="x")

        export_frame = ctk.CTkFrame(parent)
        export_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkButton(
            export_frame,
            text="Export YOLO",
            command=lambda: self._export("yolo"),
            height=35,
            fg_color="#2E7D32",
        ).pack(pady=2, fill="x")

        ctk.CTkButton(
            export_frame,
            text="Export COCO",
            command=lambda: self._export("coco"),
            height=35,
            fg_color="#1565C0",
        ).pack(pady=2, fill="x")

        ctk.CTkButton(
            export_frame,
            text="Load Project",
            command=self._load_project,
            height=35,
            fg_color="#9C27B0",
        ).pack(pady=2, fill="x")

        ctk.CTkButton(
            export_frame, text="Save Project", command=self._save_project, height=35
        ).pack(pady=2, fill="x")

    def _create_canvas(self, parent):
        """Create the interactive canvas."""
        self.canvas = InteractiveCanvas(
            parent, width=1000, height=700, bg="#1a1a1a", select_outline_color="#00ff88", dpi=96
        )
        self.canvas.pack(fill="both", expand=True)

        instructions = [
            "Instructions:",
            "1. Load an image",
            "2. Select a class",
            "3. Click 'Add Box' or press 'A'",
            "4. Drag to position, resize as needed",
            "5. Export annotations when done",
            "",
            "Shortcuts:",
            "A - Add bounding box",
            "Delete - Remove selected",
            "Ctrl+S - Save project",
        ]

        y_offset = 50
        for line in instructions:
            self.canvas.create_text(
                500, y_offset, text=line, fill="#888888", font=("Arial", 11), tags="instructions"
            )
            y_offset += 25

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.root.bind("<a>", lambda e: self._add_bounding_box())
        self.root.bind("<A>", lambda e: self._add_bounding_box())
        self.root.bind("<Control-s>", lambda e: self._save_project())
        self.root.bind("<Control-S>", lambda e: self._save_project())

    def _set_current_class(self, class_name: str):
        """Set the current annotation class."""
        self.current_class = class_name

    def _load_image(self):
        """Load an image as canvas background."""
        if not PIL_AVAILABLE:
            print("Pillow not installed. Install with: pip install Pillow")
            return

        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
        )

        if not file_path:
            return

        self.image_path = file_path

        try:
            image = Image.open(file_path)
            self.image_width, self.image_height = image.size

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            scale_w = (canvas_width - 100) / self.image_width
            scale_h = (canvas_height - 100) / self.image_height
            scale = min(scale_w, scale_h, 1.0)

            new_width = int(self.image_width * scale)
            new_height = int(self.image_height * scale)

            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized_image)

            self.canvas.delete("instructions")

            if self.bg_image_id:
                self.canvas.delete(self.bg_image_id)

            x_center = canvas_width / 2
            y_center = canvas_height / 2

            self.bg_image_id = self.canvas.create_image(
                x_center, y_center, image=self.photo_image, tags="background"
            )

            self.canvas.tag_lower("background")

            self.image_offset_x = x_center - new_width / 2
            self.image_offset_y = y_center - new_height / 2
            self.image_scale = scale

            print(f"Loaded: {Path(file_path).name}")
            print(f"Original size: {self.image_width}x{self.image_height}")
            print(f"Display size: {new_width}x{new_height} (scale: {scale:.2f})")

        except Exception as e:
            print(f"Error loading image: {e}")

    def _add_bounding_box(self):
        """Add a new bounding box."""
        if not self.bg_image_id:
            print("Please load an image first")
            return

        box_size = 100

        rect = self.canvas.create_draggable_rectangle(
            0,
            0,
            box_size,
            box_size,
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
        """Render class label above bounding box."""
        coords = self.canvas.coords(rect.rect)
        x1, y1, _, _ = coords

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
        """Update statistics display."""
        class_counts = {}
        for _, (_, bbox) in self.annotations.items():
            class_counts[bbox.class_name] = class_counts.get(bbox.class_name, 0) + 1

        stats = f"Total boxes: {len(self.annotations)}\n\n"
        for class_name in CLASS_COLORS.keys():
            count = class_counts.get(class_name, 0)
            stats += f"{class_name.capitalize()}: {count}\n"

        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", stats)

    def _export(self, format_type: str):
        """Export annotations to specified format."""
        if not self.annotations:
            print("No annotations to export")
            return

        if format_type == "yolo":
            self._export_yolo()
        elif format_type == "coco":
            self._export_coco()

    def _export_yolo(self):
        """Export in YOLO format (class x_center y_center width height)."""
        if not self.image_path:
            print("No image loaded")
            return

        output_path = Path.home() / f"{Path(self.image_path).stem}.txt"

        class_list = list(CLASS_COLORS.keys())

        with open(output_path, "w") as f:
            for item_id, (rect, bbox) in self.annotations.items():
                coords = self.canvas.coords(rect.rect)
                x1, y1, x2, y2 = coords

                img_x1 = (x1 - self.image_offset_x) / self.image_scale
                img_y1 = (y1 - self.image_offset_y) / self.image_scale
                img_x2 = (x2 - self.image_offset_x) / self.image_scale
                img_y2 = (y2 - self.image_offset_y) / self.image_scale

                x_center = ((img_x1 + img_x2) / 2) / self.image_width
                y_center = ((img_y1 + img_y2) / 2) / self.image_height
                width = (img_x2 - img_x1) / self.image_width
                height = (img_y2 - img_y1) / self.image_height

                class_id = class_list.index(bbox.class_name)

                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

        print(f"YOLO format exported to: {output_path}")

    def _export_coco(self):
        """Export in COCO JSON format."""
        if not self.image_path:
            print("No image loaded")
            return

        output_path = Path.home() / f"{Path(self.image_path).stem}_coco.json"

        categories = [{"id": i, "name": name} for i, name in enumerate(CLASS_COLORS.keys())]

        annotations_list = []
        class_list = list(CLASS_COLORS.keys())

        for ann_id, (item_id, (rect, bbox)) in enumerate(self.annotations.items()):
            coords = self.canvas.coords(rect.rect)
            x1, y1, x2, y2 = coords

            img_x1 = (x1 - self.image_offset_x) / self.image_scale
            img_y1 = (y1 - self.image_offset_y) / self.image_scale
            img_x2 = (x2 - self.image_offset_x) / self.image_scale
            img_y2 = (y2 - self.image_offset_y) / self.image_scale

            width = img_x2 - img_x1
            height = img_y2 - img_y1
            area = width * height

            annotation = {
                "id": ann_id,
                "image_id": 0,
                "category_id": class_list.index(bbox.class_name),
                "bbox": [img_x1, img_y1, width, height],
                "area": area,
                "iscrowd": 0,
            }
            annotations_list.append(annotation)

        coco_format = {
            "images": [
                {
                    "id": 0,
                    "file_name": Path(self.image_path).name,
                    "width": self.image_width,
                    "height": self.image_height,
                }
            ],
            "categories": categories,
            "annotations": annotations_list,
        }

        with open(output_path, "w") as f:
            json.dump(coco_format, f, indent=2)

        print(f"COCO format exported to: {output_path}")

    def _load_project(self):
        """Load project with all annotations."""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Load Project",
            filetypes=[("JSON files", "*_project.json"), ("All files", "*.*")],
            initialdir=str(Path.home()),
        )

        if not file_path:
            return

        try:
            with open(file_path, "r") as f:
                project_data = json.load(f)

            image_path = project_data.get("image_path")
            if image_path and Path(image_path).exists():
                self.image_path = image_path
                self._load_image_from_path(image_path)
            else:
                print(f"Image not found: {image_path}")
                print("Load image manually, then load project again")
                return

            for item_id in list(self.annotations.keys()):
                rect, _ = self.annotations[item_id]
                self.canvas.delete_draggable_rectangle(item_id)

            self.annotations.clear()

            for ann_data in project_data["annotations"]:
                x1, y1, x2, y2 = ann_data["bbox_canvas"]
                class_name = ann_data["class"]

                rect = self.canvas.create_draggable_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    outline=CLASS_COLORS.get(class_name, "#FFFFFF"),
                    width=3,
                    fill="",
                    dpi=96,
                )

                bbox = BoundingBox(
                    class_name=class_name, confidence=ann_data.get("confidence", 1.0)
                )

                item_id = self.canvas.get_item_id(rect)
                self.annotations[item_id] = (rect, bbox)
                self._render_label(rect, bbox)

            self._update_stats()
            print(f"Project loaded from: {file_path}")
            print(f"Loaded {len(self.annotations)} annotations")

        except Exception as e:
            print(f"Error loading project: {e}")

    def _load_image_from_path(self, file_path):
        """Load image from specified path."""
        if not PIL_AVAILABLE:
            return

        try:
            image = Image.open(file_path)
            self.image_width, self.image_height = image.size

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            scale_w = (canvas_width - 100) / self.image_width
            scale_h = (canvas_height - 100) / self.image_height
            scale = min(scale_w, scale_h, 1.0)

            new_width = int(self.image_width * scale)
            new_height = int(self.image_height * scale)

            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized_image)

            self.canvas.delete("instructions")

            if self.bg_image_id:
                self.canvas.delete(self.bg_image_id)

            x_center = canvas_width / 2
            y_center = canvas_height / 2

            self.bg_image_id = self.canvas.create_image(
                x_center, y_center, image=self.photo_image, tags="background"
            )

            self.canvas.tag_lower("background")

            self.image_offset_x = x_center - new_width / 2
            self.image_offset_y = y_center - new_height / 2
            self.image_scale = scale

        except Exception as e:
            print(f"Error loading image: {e}")

    def _save_project(self):
        """Save project with all annotations."""
        if not self.image_path:
            print("No image loaded")
            return

        project_data = {
            "image_path": str(self.image_path),
            "image_size": [self.image_width, self.image_height],
            "annotations": [],
        }

        for item_id, (rect, bbox) in self.annotations.items():
            coords = self.canvas.coords(rect.rect)
            annotation = {
                "class": bbox.class_name,
                "bbox_canvas": list(coords),
                "confidence": bbox.confidence,
            }
            project_data["annotations"].append(annotation)

        output_path = Path.home() / f"{Path(self.image_path).stem}_project.json"
        with open(output_path, "w") as f:
            json.dump(project_data, f, indent=2)

        print(f"Project saved to: {output_path}")

    def run(self):
        """Start the application."""
        print("Bounding Box Editor for Machine Learning")
        print("=" * 50)
        print("Workflow:")
        print("  1. Load an image")
        print("  2. Select object class")
        print("  3. Add bounding boxes (A key)")
        print("  4. Adjust positions and sizes")
        print("  5. Export to YOLO or COCO format")
        print("")
        if not PIL_AVAILABLE:
            print("Note: Install 'Pillow' to load images")
            print("  pip install Pillow")
        print("")

        self.root.mainloop()


def main():
    """Entry point."""
    app = BoundingBoxEditor()
    app.run()


if __name__ == "__main__":
    main()
