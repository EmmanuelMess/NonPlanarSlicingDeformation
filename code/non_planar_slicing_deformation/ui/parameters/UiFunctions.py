from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QSlider
from typing_extensions import Callable, Tuple


def labeledSlider(text: str, minv: int, maxv: int, default: int, slot: Callable[[int], None]) \
        -> Tuple[QVBoxLayout, QLabel]:
    """
    Create a slider with text on top
    :param text:
    :param minv:
    :param maxv:
    :param default:
    :param slot:
    :return:
    """

    layout = QVBoxLayout()
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    label = QLabel()
    label.setText(text)
    layout.addWidget(label)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    slider.setRange(minv, maxv)
    slider.setValue(default)
    slider.valueChanged.connect(slot)
    layout.addWidget(slider)

    return layout, label
