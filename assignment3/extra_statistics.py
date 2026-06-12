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
        self.stats: List[TimeWeightedStatistic] = [TimeWeightedStatistic(0,0)]
        self._current_value = 0

    def update(self, time: float, value: float):
        day = simtime.day(time)
        daypart = self._get_daypart(time)
        idx = int(3 * day + daypart)
        
        # Sequentially backfill all missed day parts
        while idx >= len(self.stats):
            current_missing_idx = len(self.stats)
            m_day = current_missing_idx // 3
            m_daypart = current_missing_idx % 3
            
            start_time = self._get_start_daypart(m_day, m_daypart)
            last_val = self.stats[-1]._last_value
            
            # Close out the previous day part at the boundary line
            self.stats[-1].update(start_time, last_val)
            
            self.stats.append(TimeWeightedStatistic(initial_value=last_val, start_time=start_time))
            
        self.stats[idx].update(time, value)
    
    def mean(self, time: float, office: bool) -> float:
        total_duration = 0.0
        total_weighted_sum = 0.0
        
        for i, stat in enumerate(self.stats):
            day = i // 3
            daypart = i % 3
            
            # Determine if this specific day part belongs to office hours
            is_weekend = (day % 7) >= 5
            is_office_part = (daypart == 1) and not is_weekend
            
            if is_office_part != office:
                continue
                
            end = min(self._get_end_daypart(day, daypart), time)
            duration = 8*60
            
            total_duration += duration
            total_weighted_sum += stat.mean(end) * duration

        if total_duration == 0: return 0.0
        return total_weighted_sum / total_duration

    def reset(self):
        self.stats = [TimeWeightedStatistic(0,0)]

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