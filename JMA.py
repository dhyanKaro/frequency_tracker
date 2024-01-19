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
        self.del2 = abs(self._src - self.lower_band)
        self.del1 = abs(self._src - self.upper_band)

        self.vola = 0 if self.del1 == self.del2 else max(self.del1, self.del2)

        self.vola_sum = self.vola_sum + 0.1 * (self.vola - self.vola)

        avg_len = 65

        if self.y <= avg_len + 1:
            self.avg_vola = self.avg_vola + 2.0 * (self.vola_sum - self.avg_vola) / (avg_len + 1)
        else:
            self.avg_vola = self.vola_sum.mean()

        length = 0.5 * (self._length - 1)
        len1 = max(np.log(np.sqrt(length)) / np.log(2) + 2, 0)
        pow1 = max(len1 - 2, 0.5)

        self.r_vola = self.vola / self.avg_vola if self.avg_vola > 0 else 0
        self.r_vola = min(max(self.r_vola, 1), pow(len1, 1 / pow1))

        pow2 = pow(self.r_vola, pow1)
        len2 = np.sqrt(length) * len1
        bet = len2 / (len2 + 1)
        kv = pow(bet, np.sqrt(pow2))

        self.lower_band = self._src if self.del2 < 0 else self._src - kv * self.del2
        self.upper_band = self._src if self.del1 < 0 else self._src + kv * self.del1

        beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
        pr = 0.5 if self._phase < -100 else 2.5 if self._phase > 100 else self._phase / 100 + 1.5
        alpha = pow(beta, pow2)

        self.ma1 = (1 - alpha) * self._src + alpha * self.ma1
        self.det0 = (self._src - self.ma1) * (1 - beta) + beta * self.det0
        ma2 = self.ma1 + pr * self.det0
        self.det1 = (ma2 - self.jma) * pow((1 - alpha), 2) + pow(alpha, 2) * self.det1
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
