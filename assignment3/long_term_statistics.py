import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from typing import TYPE_CHECKING
from scipy import stats
import numpy as np
from des_library import SampleStatistic, TimeWeightedStatistic, Counter, Simulation, Event
if TYPE_CHECKING:
    from ct_simulation import CTScannerModel

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

####################################3

class StatisticHolder:
    BATCH_LENGTH = 'batch_length'

    ############### Batch means statistics #################
    SCANNER_UTIL_OUTSIDE = "S. Util Office"
    SCANNER_UTIL_OFFICE = "S. Util Outside"
    AVG_ACCESS_TIME = "Avg Access Time"

    WAIT_TIME_EMERGENCY = "WT Emergency"
    WAIT_TIME_OUT = "WT Out"
    # Number of patients waiting outside
    WAIT_OUTSIDE_ROOM = "Waiting Outside"
    # Fraction of Inpatients that request during office hours but cannot be scanned during
    INPATIENTS_OUTSIDE = "Inp. not s. during office"

    def __init__(self, model: "CTScannerModel"):
        self.model = model
        self.batch_start = 0.0

        self.stat_scanner_util_office = TimeWeightedStatistic()
        self.stat_scanner_util_outside = TimeWeightedStatistic()
        self.stat_wait_time_out = SampleStatistic() #
        self.stat_wait_time_emergency = SampleStatistic() #
        self.stat_access_time = SampleStatistic()  #
        self.stat_total_patients = Counter() #
        self.stat_wait_outside = Counter() #
        self.stat_inp_req_office_total = Counter()
        self.stat_inp_req_office_wait = Counter()
        
        self.reset()

    def batch_time(self, sim_time = -1):
        if sim_time == -1:
            sim_time = self.model.sim.current_time
        return sim_time - self.batch_start

    def reset(self):
        """Resets all statistics"""
        self.stat_scanner_util_office.reset()
        self.stat_scanner_util_outside.reset()
        self.stat_wait_time_out.reset()
        self.stat_wait_time_emergency.reset()
        self.stat_access_time.reset()
        self.stat_total_patients.reset()
        self.stat_wait_outside.reset()
        self.stat_inp_req_office_total.reset()
        self.stat_inp_req_office_wait.reset() 

    def report(self, batch_time):
        raise Exception("Report function must be overwritten.")


class LongTermStatistic(StatisticHolder):
    def __init__(self, model: "CTScannerModel", num_batches: int):
        super().__init__(model)
        self.num_batches = num_batches
        self.reports = []
        self.batch_number = 1
        self.batch_start = 0


    def next_batch(self):
        sim = self.model.sim
        if self.batch_number != 0:
            self.reports.append(self.report(sim.current_time - self.batch_start))

        self.batch_start = sim.current_time
        self.batch_number += 1
        self.reset()

        if self.batch_number > self.num_batches:
            sim.stop()

    # Overwrite these
    def before_hook(self, sim: Simulation, event: Event): pass
    def after_hook(self, sim: Simulation, event: Event): pass
    

class BatchMeansMethod(LongTermStatistic):
    def __init__(self, model: 'CTScannerModel', warmup_time: int, batch_len: int, num_batches: int):
        super().__init__(model, num_batches)

        self.warmup_time = warmup_time
        if warmup_time != 0:
            self.batch_number = 0
        self.batch_len = batch_len

    def report(self, batch_time):
        stats = {}
        stats[StatisticHolder.SCANNER_UTIL_OFFICE] = self.stat_scanner_util_office.mean(batch_time)
        stats[StatisticHolder.SCANNER_UTIL_OUTSIDE] = self.stat_scanner_util_outside.mean(batch_time)
        stats[StatisticHolder.WAIT_TIME_OUT] = self.stat_wait_time_out.mean()
        stats[StatisticHolder.WAIT_TIME_EMERGENCY] = self.stat_wait_time_emergency.mean()
        stats[StatisticHolder.AVG_ACCESS_TIME] = self.stat_access_time.mean()
        stats[StatisticHolder.WAIT_OUTSIDE_ROOM] = self.stat_wait_outside.fraction(self.stat_total_patients)
        stats[StatisticHolder.INPATIENTS_OUTSIDE] = self.stat_inp_req_office_wait.fraction(self.stat_inp_req_office_total)
        return stats

    def before_hook(self, sim: Simulation, event: Event):
        sim_time = sim.current_time
        if self.batch_number == 0: # System is in warmup period
            if sim_time > self.warmup_time:
                self.next_batch()
        elif sim_time - self.warmup_time > self.batch_number * self.batch_len: # System is in a batch
            self.next_batch()