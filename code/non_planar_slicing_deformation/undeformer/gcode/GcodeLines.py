from pygcode import Line
from typing_extensions import Callable, List


class GcodeVisitor():

    def __init__(self, rawGcode: List[str]) -> None:
        self.lines: List[Line] = [Line(l) for l in rawGcode]

    def visit(self, f: Callable[[Line], Line]) -> None:
        self.lines = [f(line) for line in self.lines]
