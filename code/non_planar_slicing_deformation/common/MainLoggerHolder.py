import logging
import sys
import traceback
from types import TracebackType

from PySide6.QtCore import Signal, QObject
from typing_extensions import Type, Optional

from non_planar_slicing_deformation.common.QtLoggingHandler import QtLoggingHandler
from non_planar_slicing_deformation.common.Singleton import Singleton


class MainLoggerHolder(metaclass=Singleton):
    """
    Helper class for maintaining the logger used by the whole codebase.
    A logger customized for this app
    """

    class DummyQObject(QObject):
        """
        Dummy object to keep the signal alive
        """

        lineLogged = Signal(str)

    qtObject = DummyQObject()

    def __init__(self) -> None:
        super().__init__()

        sys.excepthook = self._onException

        self.logger = logging.getLogger('main_app')
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter("[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s]\t\t%(message)s")

        streamHandler = logging.StreamHandler()
        streamHandler.setLevel(logging.DEBUG)
        streamHandler.setFormatter(formatter)
        self.logger.addHandler(streamHandler)

        qtHandler = QtLoggingHandler(self.qtObject)
        qtHandler.setLevel(logging.INFO)
        qtHandler.setFormatter(formatter)
        qtHandler.lineLogged.connect(self.qtObject.lineLogged)
        self.logger.addHandler(qtHandler)

    def _onException(self, etype: Type[BaseException], value: Optional[BaseException],
                     tb: Optional[TracebackType]) -> None:
        # TODO use logging.Logger.traceback
        self.logger.error(''.join(traceback.format_exception(etype, value, tb)))


MAIN_LOGGER = MainLoggerHolder().logger
