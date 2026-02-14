#!/usr/bin/env python3
"""
Magic methods example.

Demonstrates:
- Mathematical operations on rectangles
- Intersection and union operations
- Point containment testing
- Sorting and comparison
"""

import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas


def main():
    root = ctk.CTk()
    root.title("CTk Interactive Canvas - Magic Methods Demo")
    root.geometry("900x700")
    
    canvas = InteractiveCanvas(root, width=900, height=600, bg='white')
    canvas.pack(pady=10)
    
    rect1 = canvas.create_draggable_rectangle(100, 100, 200, 200, outline='blue', width=2)
    rect2 = canvas.create_draggable_rectangle(300, 100, 400, 200, outline='red', width=2)
    
    button_frame = ctk.CTkFrame(root)
    button_frame.pack(pady=10)
    
    info_label = ctk.CTkLabel(root, text="", font=("Arial", 12))
    info_label.pack()
    
    def translate_right():
        nonlocal rect1
        rect1 += [50, 0]
        info_label.configure(text="Translated rect1 right by 50px using +=")
    
    def scale_double():
        nonlocal rect2
        rect2 *= 1.5
        info_label.configure(text="Scaled rect2 by 1.5x using *=")
    
    def scale_half():
        nonlocal rect2
        rect2 /= 1.5
        info_label.configure(text="Scaled rect2 by 1/1.5 using /=")
    
    def create_copy():
        new_rect = rect1 + [250, 0]
        info_label.configure(text=f"Created new rectangle at offset [250, 0] using +")
    
    def show_intersection():
        intersection = rect1 & rect2
        if intersection:
            info_label.configure(text=f"Intersection exists! Area: {intersection._area():.0f}px²")
        else:
            info_label.configure(text="No intersection between rectangles")
    
    def show_union():
        bounding = rect1 | rect2
        canvas.create_draggable_rectangle(
            *bounding,
            outline='purple',
            width=1,
            dash=(5, 5)
        )
        info_label.configure(text="Created bounding box using | operator")
    
    def test_containment():
        center_x = (rect1[0] + rect1[2]) / 2
        center_y = (rect1[1] + rect1[3]) / 2
        point = [center_x, center_y]
        
        if point in rect1:
            info_label.configure(text=f"Point {point} is IN rect1")
        else:
            info_label.configure(text=f"Point {point} is NOT in rect1")
    
    def compare_sizes():
        if rect1 < rect2:
            info_label.configure(text="rect1 < rect2 (by area)")
        elif rect1 > rect2:
            info_label.configure(text="rect1 > rect2 (by area)")
        else:
            info_label.configure(text="rect1 == rect2 (by area)")
    
    def show_coords():
        x0, y0, x1, y1 = rect1
        info_label.configure(text=f"rect1 coords via unpacking: ({x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f})")
    
    ctk.CTkButton(button_frame, text="Translate Right (+=)", command=translate_right).grid(row=0, column=0, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Scale Up (*=)", command=scale_double).grid(row=0, column=1, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Scale Down (/=)", command=scale_half).grid(row=0, column=2, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Create Copy (+)", command=create_copy).grid(row=1, column=0, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Intersection (&)", command=show_intersection).grid(row=1, column=1, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Union (|)", command=show_union).grid(row=1, column=2, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Test Containment (in)", command=test_containment).grid(row=2, column=0, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Compare Sizes (<>)", command=compare_sizes).grid(row=2, column=1, padx=5, pady=5)
    ctk.CTkButton(button_frame, text="Show Coords (unpack)", command=show_coords).grid(row=2, column=2, padx=5, pady=5)
    
    root.mainloop()


if __name__ == "__main__":
    main()
