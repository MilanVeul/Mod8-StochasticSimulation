import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from des_library import TimeWeightedStatistic

from scipy import stats
import numpy as np
from typing import List
from itertools import chain

import simtime

def batch_number_lower_bound(data, precision, alpha=0.05):
    r = len(data)
    t = stats.t.ppf(1-alpha/2, df=r-1)
    var = np.var(data, ddof=1)
    mean = np.mean(data)
    min_batch = t*t * var / (precision/(1+precision) * mean)**2
    return min_batch

def batch_confidence_interval(data, alpha):
    r = len(data)
    mean = np.mean(data)
    t = stats.t.ppf(1-alpha/2, df=r-1)
    var = np.var(data, ddof=1)

    diff = t * (var/r)**0.5
    return (mean - diff, mean + diff)



class ScannerUtilityStatistic:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last_time = 0.0
        self.last_value = 0.0

        # Accumulators for Office Hours
        self.office_area = 0.0
        self.office_duration = 0.0

        # Accumulators for Outside Office Hours
        self.outside_area = 0.0
        self.outside_duration = 0.0

    def update(self, time: float, value: float):
        if time <= self.last_time:
            self.last_value = value
            return

        # Slice the elapsed interval across daypart boundaries
        current = self.last_time
        while current < time:
            day = simtime.day(current)
            daypart = self._get_daypart(current)

            end_of_daypart = self._get_end_daypart(day, daypart)
            next_stop = min(end_of_daypart, time)
            duration = next_stop - current

            # Prevent infinite looping when current lies exactly on a boundary
            if duration <= 1e-6:
                current = next_stop + 1e-6
                continue

            is_weekend = (day % 7) >= 5
            is_office = (daypart == 1) and not is_weekend

            if is_office:
                self.office_area += self.last_value * duration
                self.office_duration += duration
            else:
                self.outside_area += self.last_value * duration
                self.outside_duration += duration

            current = next_stop

        self.last_time = time
        self.last_value = value

    def mean(self, time: float, office: bool) -> float:
        # Flush any remaining unlogged time up to the reporting time
        if time > self.last_time:
            self.update(time, self.last_value)

        if office:
            return self.office_area / self.office_duration if self.office_duration > 0 else 0.0
        else:
            return self.outside_area / self.outside_duration if self.outside_duration > 0 else 0.0
        
    def _get_start_daypart(self, day, daypart):
        if daypart == 0: return 24*60*day
        if daypart == 1: return 24*60*day + 8*60
        if daypart == 2: return 24*60*day + 16*60   
    def _get_end_daypart(self, day, daypart):
        if daypart == 0: return 24*60*day + 8*60
        if daypart == 1: return 24*60*day + 16*60
        if daypart == 2: return 24*60*day + 24*60
    
    def _get_daypart(self, time):
        daytime = simtime.daytime(time)
        if daytime < 8*60:
            return 0
        if daytime > 16*60:
            return 2
        return 1