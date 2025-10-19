from PySide6.QtCore import QThread


class DeformerWorker(QThread):
    """
    Implementation of the deformation, that runs on another thread
    """
