"""
This module contains classes that represent single-channel measurements.
"""
from __future__ import division
import numpy as np
from matplotlib.pyplot import mlab  # TODO: replace with a scipy PSD estimator
import pandas as pd
from kid_readout.analysis.resonator import resonator
from kid_readout.analysis.timedomain.despike import deglitch_window
from kid_readout.measurement.core import Measurement, MeasurementTuple


class StreamArray(Measurement):
    """
    This class represents simultaneously-sampled data from multiple channels.
    """
    def __init__(self, frequency=np.array([0]), epoch=np.array([0]), s21=np.array([[1]]), state=None, analyze=False):
        """
        The frequency and epoch arrays are 1-D, while s21 is 2-D. The arrays should obey
        s21.shape == (frequency.size, epoch.size)
        """
        self.frequency = np.array(frequency)
        self.s21 = np.array(s21)
        self.epoch = np.array(epoch)
        # Check sizes
        self._s21_mean = None
        self._s21_mean_error = None
        super(StreamArray, self).__init__(state, analyze)

    @property
    def s21_mean(self):
        if self._s21_mean is None:
            self._s21_mean = self.s21.mean(axis=0)
        return self._s21_mean

    @property
    def s21_mean_error(self):
        if self._s21_mean_error is None:
            self._s21_mean_error = ((self.s21.real.std(axis=0) + 1j * self.s21.imag.std(axis=0)) /
                                    self.s21.size ** (1 / 2))
        return self._s21_mean_error


class FrequencySweepArray(Measurement):
    """
    This class represents a set of streams .
    """

    def __init__(self, streams=(), state=None, analyze=False):
        # Don't sort by frequency so that non-monotonic order can be preserved if needed.
        self.streams = MeasurementTuple(streams)
        for stream in self.streams:
            stream._parent = self
        self._frequency = None
        self._s21 = None
        self._s21_error = None
        super(FrequencySweep, self).__init__(state, analyze)

    @property
    def frequency(self):
        if self._frequency is None:
            self._frequency = np.array([stream.frequency for stream in self.streams])
        return self._frequency

    @property
    def s21(self):
        if self._s21 is None:
            self._s21 = np.array([stream.s21_mean for stream in self.streams])
        return self._s21

    @property
    def s21_error(self):
        if self._s21_error is None:
            self._s21_error = np.array([stream.s21_mean_error for stream in self.streams])
        return self._s21_error


class ResonatorSweepArray(FrequencySweepArray):
    def __init__(self, streams=(), state=None, analyze=False):
        self._resonator = None
        super(ResonatorSweepArray, self).__init__(streams, state, analyze)

    def analyze(self):
        self.resonator

    @property
    def resonator(self):
        if self._resonator is None:
            self._resonator = resonator.fit_best_resonator(self.frequency, self.s21, errors=self.s21_error)
        return self._resonator


class SweepStreamArray(Measurement):

    def __init__(self, sweep=None, stream=None, state=None, analyze=False):
        self.sweep = sweep
        if self.sweep is not None:
            self.sweep._parent = self
        self.stream = stream
        if self.stream is not None:
            self.stream._parent = self
        self._sweep_s21_normalized = None
        self._stream_s21_normalized = None
        self._stream_s21_normalized_deglitched = None
        self._i = None
        self._x = None
        self._psd_frequency = None
        self._psd_ii = None
        self._psd_xx = None
        super(SweepStreamArray, self).__init__(state, analyze)

    def analyze(self):
        self._set_sweep_s21_normalized()
        self._set_stream_s21_normalized_deglitched()
        self._set_i_and_x()
        self._set_psd_i_and_x()

    @property
    def sweep_s21_normalized(self):
        if self._sweep_s21_normalized is None:
            self._set_sweep_s21_normalized()
        return self._sweep_s21_normalized

    def _set_sweep_s21_normalized(self):
        self._sweep_s21_normalized = np.array([self.sweep.resonator.normalize(f, s21)
                                               for f, s21 in zip(self.sweep.frequency, self.sweep.s21)])

    @property
    def stream_s21_normalized(self):
        if self._stream_s21_normalized is None:
            self._stream_s21_normalized = self.sweep.resonator.normalize(self.stream.frequency, self.stream.s21)
        return self._stream_s21_normalized

    @property
    def stream_s21_normalized_deglitched(self):
        if self._stream_s21_normalized_deglitched is None:
            self._set_stream_s21_normalized_deglitched()
        return self._stream_s21_normalized_deglitched

    def _set_stream_s21_normalized_deglitched(self, window_in_seconds=1, deglitch_threshold=5):
        window = int(2 ** np.ceil(np.log2(window_in_seconds * self.stream.sample_frequency)))
        self._stream_s21_normalized_deglitched = deglitch_window(self.stream_s21_normalized, window,
                                                                 thresh=deglitch_threshold)

    @property
    def i(self):
        if self._i is None:
            self._set_i_and_x()
        return self._i

    @property
    def x(self):
        if self._x is None:
            self._set_i_and_x()
        return self._x

    def _set_i_and_x(self, deglitch=True):
        if deglitch:
            s21 = self.stream_s21_normalized_deglitched
        else:
            s21 = self.stream_s21_normalized
        iQ_e = 1 / self.sweep.resonator.Q_e
        z = iQ_e / (1 - s21)
        self._i = z.real - iQ_e.real
        self._x = 1 / 2 * z.imag

    @property
    def psd_frequency(self):
        if self._psd_frequency is None:
            self._set_psd_i_and_x()
        return self._psd_frequency

    @property
    def psd_ii(self):
        if self._psd_ii is None:
            self._set_psd_i_and_x()
        return self._psd_ii

    @property
    def psd_xx(self):
        if self._psd_xx is None:
            self._set_psd_i_and_x()
        return self._psd_xx

    # TODO: calculate errors in PSDs
    def _set_psd_i_and_x(self, NFFT=None, window=mlab.window_none, **kwargs):
        # Use the same length calculation as SweepNoiseMeasurement
        if NFFT is None:
            NFFT = int(2**(np.floor(np.log2(self.stream.s21.size)) - 3))
        psd_ii, f = mlab.psd(self.i, Fs=self.stream.sample_frequency, NFFT=NFFT, window=window, **kwargs)
        psd_xx, f = mlab.psd(self.x, Fs=self.stream.sample_frequency, NFFT=NFFT, window=window, **kwargs)
        self._psd_frequency = f
        self._psd_ii = psd_ii
        self._psd_xx = psd_xx

    # TODO: move this forward to a usable version.
    def to_dataframe(self):
        data = {}
        for param in self.sweep.resonator.result.params.values():
            data['resonator_{}'.format(param.name)] = [param.value]
            data['resonator_{}_error'.format(param.name)] = [param.stderr]
        data['resonator_redchi'] = self.sweep.resonator.result.redchi
        # temperatures
        # roach state
        return pd.DataFrame(data, index=[0])


class SweepArray(Measurement):
    """
    This class is an array of sweeps.
    """
    pass
