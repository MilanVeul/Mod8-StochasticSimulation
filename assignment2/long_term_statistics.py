import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from typing import TYPE_CHECKING
from scipy import stats
import numpy as np
from des_library import SampleStatistic, TimeWeightedStatistic, Counter, Simulation, Event
if TYPE_CHECKING:
    from waste_collection import WasteCollectionModel

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

def regenerative_confidence_interval(totals, num_requests, alpha):
    N = len(totals)
    t = stats.t.ppf(1-alpha/2, df=N - 1)
    expectation = np.mean(totals) / np.mean(num_requests)

    var_V = np.var(totals, ddof=1) + expectation**2 * np.var(num_requests, ddof=1) - 2*expectation * np.cov(totals, num_requests)[0,1]

    diff = t * (var_V / (np.mean(num_requests)**2 * N))**.5
    return (expectation - diff, expectation + diff)

####################################3

class StatisticHolder:
    BATCH_LENGTH = 'batch_length'

    # Batch means
    AVG_WAITING_TIME = 'avg_waiting_time'
    AVG_QUEUE_LEN = 'avg_queue_len'
    REROUTING_RATE = 'rerouting_rate'
    TRUCK_UTILISATION = 'truck_utilisation'

    # Regenerative
    TOTAL_WAITING_TIME = 'total_waiting_time'
    NUM_REQUESTS = 'num_requests'
    TOTAL_QUEUE_LEN = 'total_q_len'
    TOTAL_TRUCK_UTILISATION = 'total_truck_util'
    TOTAL_REROUTES = 'total_reroutes'


    def __init__(self, model: "WasteCollectionModel"):
        self.model = model
        self.batch_start = 0.0

        self.stat_sojourn_time = SampleStatistic()
        self.stat_rerouting_rate = Counter()
        self.stat_queue_len = TimeWeightedStatistic()
        self.stat_truck_util = [TimeWeightedStatistic() for _ in self.model.trucks]
        
        self.reset()

    def batch_time(self, sim_time = -1):
        if sim_time == -1:
            sim_time = self.model.sim.current_time
        return sim_time - self.batch_start

    def reset(self):
        """Resets all statistics"""
        self.stat_sojourn_time.reset()
        self.stat_rerouting_rate.reset()
        self.stat_queue_len.reset()
        self.stat_queue_len.update(0, 0)
        for util in self.stat_truck_util:
            util.reset()
            util.update(0, False)

    def report(self, batch_time):
        raise Exception("Report function must be overwritten.")


class LongTermStatistic(StatisticHolder):
    def __init__(self, model: "WasteCollectionModel", num_batches: int):
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
    def __init__(self, model: 'WasteCollectionModel', warmup_time: int, batch_len: int, num_batches: int):
        super().__init__(model, num_batches)

        self.warmup_time = warmup_time
        if warmup_time != 0:
            self.batch_number = 0
        self.batch_len = batch_len

    def report(self, batch_time):
        stats = {}
        stats[StatisticHolder.AVG_QUEUE_LEN] = self.stat_queue_len.mean(batch_time)
        stats[StatisticHolder.AVG_WAITING_TIME] = self.stat_sojourn_time.mean()
        stats[StatisticHolder.TRUCK_UTILISATION] = [util.mean(batch_time) for util in self.stat_truck_util]
        stats[StatisticHolder.REROUTING_RATE] = self.stat_rerouting_rate.rate(batch_time)
        stats[StatisticHolder.BATCH_LENGTH] = batch_time
        return stats

    def before_hook(self, sim: Simulation, event: Event):
        sim_time = sim.current_time
        if self.batch_number == 0: # System is in warmup period
            if sim_time > self.warmup_time:
                self.next_batch()
        elif sim_time - self.warmup_time > self.batch_number * self.batch_len: # System is in a batch
            self.next_batch()
    

class RegenerativeMethod(LongTermStatistic):
    def __init__(self, model: 'WasteCollectionModel', num_batches: int):
        super().__init__(model, num_batches)

    def before_hook(self, sim: Simulation, event: Event):
        is_arrival = event.__class__.__name__ == "Arrival"
        if not is_arrival:
            return
        
        empty_queues = all(len(q) == 0 for q in self.model.district_queues)
        vehicles_idle = all(truck.status.value == 0 for truck in self.model.trucks) # IDLE -> I cannot import TruckStatus enum because of circular imports

        if empty_queues and vehicles_idle:
            self.next_batch()

    def report(self, batch_time):
        stats = {}
        stats[StatisticHolder.BATCH_LENGTH] = batch_time
        stats[StatisticHolder.TOTAL_WAITING_TIME] = self.stat_sojourn_time.total
        stats[StatisticHolder.NUM_REQUESTS] = self.stat_sojourn_time.count
        stats[StatisticHolder.TOTAL_QUEUE_LEN] = self.stat_queue_len.accumulated(batch_time)
        stats[StatisticHolder.TOTAL_TRUCK_UTILISATION] = [util.accumulated(batch_time) for util in self.stat_truck_util]
        stats[StatisticHolder.TOTAL_REROUTES] = self.stat_rerouting_rate.value
        return stats
    
        


    
