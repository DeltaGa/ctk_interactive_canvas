#!/usr/bin/env python3
"""
Basic usage example for CTk Interactive Canvas.

Demonstrates:
- Creating an interactive canvas
- Adding draggable rectangles
- Basic interaction (drag, select, resize)
"""

import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas


def main():
    root = ctk.CTk()
    root.title("CTk Interactive Canvas - Basic Example")
    root.geometry("800x600")
    
    canvas = InteractiveCanvas(
        root,
        width=800,
        height=600,
        bg='white',
        select_outline_color='#16fff6'
    )
    canvas.pack(fill='both', expand=True)
    
    rect1 = canvas.create_draggable_rectangle(
        50, 50, 150, 150,
        outline='blue',
        width=2,
        fill=''
    )
    
    rect2 = canvas.create_draggable_rectangle(
        200, 200, 300, 300,
        outline='red',
        width=2,
        fill=''
    )
    
    rect3 = canvas.create_draggable_rectangle(
        400, 100, 500, 200,
        outline='green',
        width=2,
        fill=''
    )
    
    print("Controls:")
    print("- Click and drag rectangles to move")
    print("- Drag bottom-right handle to resize")
    print("- Shift+Click to multi-select")
    print("- Drag on empty space to select multiple")
    print("- Middle-mouse or Space+Drag to pan")
    print("- Delete key to remove selected")
    print("\nModifier keys:")
    print("- Shift during move: Lock to 45° angles")
    print("- Shift during resize: Maintain aspect ratio")
    print("- Ctrl during resize: Resize from center")
    print("- Alt during resize: Constrain to one axis")
    
    root.mainloop()


if __name__ == "__main__":
    main()
