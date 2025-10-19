import pyvista as pv
import pyvistaqt as pvqt  # type: ignore
from PySide6 import QtGui

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from typing_extensions import override, Optional


class ViewRotatedTrianglesWindow(QWidget):
    """
    View rotated triangles for S4 deformer
    """

    def __init__(self, mesh: pv.UnstructuredGrid, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("")

        self.resize(400, 500)

        self.centralLayout = QVBoxLayout()
        self.centralLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.plotter = pvqt.QtInteractor(self)
        self.plotter.add_mesh(mesh)

        self.centralLayout.addWidget(self.plotter)

        self.setLayout(self.centralLayout)

    @override
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        # HACK horrible hack to make the QtInteractor not break all windows when one window is closed

        if self.plotter is None:
            event.ignore()

        plotter = self.plotter
        self.plotter = None

        plotter.clear()
        self.centralLayout.removeWidget(plotter)
        del plotter

        event.ignore()
