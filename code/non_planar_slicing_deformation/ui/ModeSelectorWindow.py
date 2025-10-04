from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton, QHBoxLayout
from typing_extensions import List

from non_planar_slicing_deformation.ui import Strings
from non_planar_slicing_deformation.ui.Mode import Mode


class ModeSelectorWindow(QWidget):
    """
    A mode selector for different printer and deformer configurations
    """

    @dataclass
    class Item:
        """
        Data models for the items in the dropdown
        """

        mode: Mode
        text: str

    _OPTIONS: List[Item] = [
        Item(Mode.FOUR_AXIS_SIMPLE, Strings.fourAxisSimple),
        # Item(Mode.FOUR_S, Strings.fourS),
        ]

    showLogs = Signal()
    accepted = Signal(Mode)

    def __init__(self) -> None:
        super().__init__()

        self.resize(250, 300)

        self.centralLayout = QVBoxLayout()
        self.centralLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.modeText = QLabel()
        self.modeText.setText(Strings.selectMode)

        self.modeDropDown = QComboBox()
        self.modeDropDown.addItems([option.text for option in self._OPTIONS])

        self.acceptButton = QPushButton()
        self.acceptButton.setText(Strings.accept)
        self.acceptButton.pressed.connect(self.onPressedAccept)

        self.centralLayout.addWidget(self.modeText)
        self.centralLayout.addWidget(self.modeDropDown)
        self.centralLayout.addWidget(self.acceptButton)

        self.headerLayout = QHBoxLayout()
        self.headerLayout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.logsButton = QPushButton()
        self.logsButton.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.InsertText))
        self.logsButton.pressed.connect(self.showLogs)
        self.headerLayout.addWidget(self.logsButton)

        self.rootLayout = QVBoxLayout()
        self.rootLayout.addLayout(self.headerLayout)
        self.rootLayout.addLayout(self.centralLayout)

        self.setLayout(self.rootLayout)

    @Slot()
    def onPressedAccept(self) -> None:
        selected = self._OPTIONS[self.modeDropDown.currentIndex()]
        self.accepted.emit(selected.mode)
        self.close()
