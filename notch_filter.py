# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 15:12:58 2020

@author: hong joo LEE
"""

from scipy.signal import lfilter
from scipy import signal


def notch(cutoff, fs, quality):
    w0 = cutoff / (fs / 2)
    Q = quality
    b, a = signal.iirnotch(w0, Q)
    return b, a


def notch_filter(data, cutoff, fs, quality):
    b, a = notch(cutoff, fs, quality)
    y = lfilter(b, a, data)
    return y
