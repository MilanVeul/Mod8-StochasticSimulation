import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from des_library import TimeWeightedStatistic

from scipy import stats
import numpy as np
from typing import List
from itertools import chain

import simtime
from simtime import DayPart

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
        self.stats: List[TimeWeightedStatistic] = [TimeWeightedStatistic(0,0)]
        self._current_value = 0

    # ASSUMPTION: There is an update at least once per day part
    def update(self, time: float, value: float):
        day = simtime.day(time)
        daypart = self._get_daypart(time)
        idx = int(3*day + daypart)
        if idx >= len(self.stats):
            start_daypart = self._get_start_daypart(day, daypart)
            self.stats[-1].update(start_daypart, self.stats[-1]._last_value)
            new_stat = TimeWeightedStatistic(
                initial_value=self.stats[idx-1]._last_value, 
                start_time=start_daypart)
            self.stats.append(new_stat)
        self.stats[idx].update(time, value)
    
    def mean(self, time, office: bool):
        num_stats = len(self.stats)
        if office:
            means = [self.stats[i].mean(min(self._get_end_daypart(i//3, i%3), time)) for i in range(1, num_stats, 3)]
        else: 
            means = [self.stats[i].mean(min(self._get_end_daypart(i//3, i%3), time)) for i in chain(range(0, num_stats, 3), range(2, num_stats, 3))]
        return sum(means) / len(means)

    def reset(self):
        self.stats = [TimeWeightedStatistic(0,0)]

    def _get_start_daypart(self, day, daypart):
        if daypart == 0: return 24*60*day
        if daypart == 1: return 24*60*day + 8*60
        if daypart == 2: return 24*60*day + 16*60   
    def _get_end_daypart(self, day, daypart):
        if daypart == 0: return 24*60*day + 8*60
        if daypart == 1: return 24*60*day + 16*60
        if daypart == 2: return 24*60*day + 24*60 - 1
    
    def _get_daypart(self, time):
        daytime = simtime.daytime(time)
        if daytime < 8*60:
            return 0
        if daytime > 16*60:
            return 2
        return 1
    
