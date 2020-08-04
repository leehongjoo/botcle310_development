# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 15:33:56 2020

@author: hong joo LEE
"""

from scipy.signal import butter, lfilter, lfilter_zi


def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a


def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    zi = lfilter_zi(b, a)
    y, _ = lfilter(b, a, data, zi=zi * data[0])
    return y