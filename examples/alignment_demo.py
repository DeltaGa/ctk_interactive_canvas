#!/usr/bin/env python3
"""
Alignment and distribution example.

Demonstrates:
- Aligning multiple rectangles
- Distributing rectangles evenly
- Using class methods for batch operations
"""

import customtkinter as ctk
from ctk_interactive_canvas import DraggableRectangle, InteractiveCanvas


def main():
    root = ctk.CTk()
    root.title("CTk Interactive Canvas - Alignment Demo")
    root.geometry("900x700")

    canvas = InteractiveCanvas(root, width=900, height=600, bg="white")
    canvas.pack(pady=10)

    rectangles = []
    for i in range(5):
        rect = canvas.create_draggable_rectangle(
            50 + i * 150, 50 + i * 30, 130 + i * 150, 130 + i * 30, outline="blue", width=2
        )
        rectangles.append(rect)

    button_frame = ctk.CTkFrame(root)
    button_frame.pack(pady=10)

    def align_top():
        DraggableRectangle.align(rectangles, mode="top")

    def align_middle():
        DraggableRectangle.align(rectangles, mode="middle")

    def align_bottom():
        DraggableRectangle.align(rectangles, mode="bottom")

    def align_start():
        DraggableRectangle.align(rectangles, mode="start")

    def align_center():
        DraggableRectangle.align(rectangles, mode="center")

    def align_end():
        DraggableRectangle.align(rectangles, mode="end")

    def distribute_h():
        DraggableRectangle.distribute(rectangles, mode="horizontal")

    def distribute_v():
        DraggableRectangle.distribute(rectangles, mode="vertical")

    ctk.CTkButton(button_frame, text="Align Top", command=align_top).grid(row=0, column=0, padx=5)
    ctk.CTkButton(button_frame, text="Align Middle", command=align_middle).grid(
        row=0, column=1, padx=5
    )
    ctk.CTkButton(button_frame, text="Align Bottom", command=align_bottom).grid(
        row=0, column=2, padx=5
    )
    ctk.CTkButton(button_frame, text="Align Start", command=align_start).grid(
        row=1, column=0, padx=5, pady=5
    )
    ctk.CTkButton(button_frame, text="Align Center", command=align_center).grid(
        row=1, column=1, padx=5, pady=5
    )
    ctk.CTkButton(button_frame, text="Align End", command=align_end).grid(
        row=1, column=2, padx=5, pady=5
    )
    ctk.CTkButton(button_frame, text="Distribute Horizontal", command=distribute_h).grid(
        row=2, column=0, columnspan=2, padx=5, pady=5
    )
    ctk.CTkButton(button_frame, text="Distribute Vertical", command=distribute_v).grid(
        row=2, column=2, columnspan=2, padx=5, pady=5
    )

    root.mainloop()


if __name__ == "__main__":
    main()
