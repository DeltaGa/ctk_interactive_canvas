"""
Tests for DraggableRectangle.
"""

from ctk_interactive_canvas import DraggableRectangle


def test_rectangle_creation(rect):
    """Test basic rectangle creation."""
    assert rect is not None
    coords = list(rect)
    assert len(coords) == 4
    assert coords[0] == 10
    assert coords[1] == 10


def test_position_getters(rect):
    """Test position getter methods."""
    topleft = rect.get_topleft_pos()
    assert topleft == [10, 10]

    size = rect.get_size()
    assert size == [90, 90]


def test_position_setters(rect):
    """Test position setter methods."""
    rect.set_topleft_pos([50, 50])
    assert rect.get_topleft_pos() == [50, 50]

    rect.set_size([100, 100])
    assert rect.get_size() == [100, 100]


def test_magic_add(rect):
    """Test addition operator."""
    new_rect = rect + [50, 30]
    new_pos = new_rect.get_topleft_pos()
    assert new_pos == [60, 40]


def test_magic_mul(rect):
    """Test multiplication operator."""
    new_rect = rect * 2
    new_size = new_rect.get_size()
    assert new_size == [180, 180]


def test_magic_iadd(rect):
    """Test in-place addition."""
    original_pos = rect.get_topleft_pos()
    rect += [10, 10]
    new_pos = rect.get_topleft_pos()
    assert new_pos == [original_pos[0] + 10, original_pos[1] + 10]


def test_magic_contains(rect):
    """Test point containment."""
    assert [50, 50] in rect
    assert [150, 150] not in rect


def test_magic_len(rect):
    """Test length."""
    assert len(rect) == 4


def test_magic_getitem(rect):
    """Test indexing."""
    assert rect[0] == 10
    assert rect[1] == 10
    coords = rect[:]
    assert len(coords) == 4


def test_magic_iter(rect):
    """Test iteration."""
    coords = list(rect)
    assert len(coords) == 4


def test_comparison_eq(canvas):
    """Test equality comparison."""
    # Create a rectangle and copy it with no offset
    rect1 = canvas.create_draggable_rectangle(10, 10, 100, 100)
    rect2_copy = rect1.copy_(offset=[0, 0])  # Same position as rect1
    assert rect1 == rect2_copy


def test_comparison_lt(canvas):
    """Test less-than comparison."""
    small = canvas.create_draggable_rectangle(0, 0, 50, 50)
    large = canvas.create_draggable_rectangle(0, 0, 100, 100)
    assert small < large


def test_intersection(canvas):
    """Test intersection operator."""
    rect1 = canvas.create_draggable_rectangle(0, 0, 100, 100)
    rect2 = canvas.create_draggable_rectangle(50, 50, 150, 150)
    intersection = rect1 & rect2
    assert intersection is not None
    assert intersection._area() == 2500


def test_union(canvas):
    """Test union operator."""
    rect1 = canvas.create_draggable_rectangle(0, 0, 100, 100)
    rect2 = canvas.create_draggable_rectangle(50, 50, 150, 150)
    bounding = rect1 | rect2
    topleft = bounding.get_topleft_pos()
    assert topleft == [0, 0]


def test_align(multiple_rects):
    """Test alignment."""
    DraggableRectangle.align(multiple_rects, mode="top")
    positions = [rect.get_topleft_pos() for rect in multiple_rects]
    y_coords = [pos[1] for pos in positions]
    assert len(set(y_coords)) == 1


def test_distribute(multiple_rects):
    """Test distribution."""
    DraggableRectangle.distribute(multiple_rects, mode="horizontal")
    positions = [rect.get_topleft_pos() for rect in multiple_rects]
    assert positions[0][0] < positions[1][0] < positions[2][0]


def test_copy(rect):
    """Test copying."""
    new_rect = rect.copy_(offset=[100, 100])
    assert new_rect is not None
    assert new_rect != rect


def test_unit_conversion(rect):
    """Test mm/px conversion."""
    px_value = 100
    mm_value = rect.convert_px_to_mm(px_value, dpi=300)
    px_back = rect.convert_mm_to_px(mm_value, dpi=300)
    assert px_back == px_value
