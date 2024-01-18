import numpy as np

class JMA:
    def __init__(self, _src, _length=13, _phase=0):
        self._src = _src
        self._length = _length
        self._phase = _phase
        self.lower_band = _src
        self.upper_band = _src
        self.vola_sum = 0.0
        self.avg_vola = 0.0
        self.ma1 = _src
        self.det0 = 0.0
        self.jma = _src
        self.det1 = 0.0
        self.del2 = 0.0
        self.del1 = 0.0
        self.vola = 0.0
        self.r_vola = 0.0
        self.y = 1

        self.series = [_src]

    def update(self, _src):
        self._src = _src
        ...
        self.jma = self.jma + self.det1
        self.series.append(self.jma)

        self.y += 1

    def get(self):
        return self.jma

    def get_series(self):
        return self.series

    # Because we're not saving all the intermediate steps of the calculations, we can't go back 100%, but this works for a quick undo
    def pop(self):
        if len(self.series) > 1:
            # Remove the last element from the series
            popped_value = self.series.pop()

            # Update internal variables accordingly
            self.jma = self.series[-1]
            self.y -= 1

            return popped_value