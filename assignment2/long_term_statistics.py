import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from typing import TYPE_CHECKING
from scipy import stats
import numpy as np
from des_library import SampleStatistic, TimeWeightedStatistic, Counter, Simulation, Event
if TYPE_CHECKING:
    from waste_collection import WasteCollectionModel

def min_batch_number(current_batch_number, data, precision, alpha=0.05):
    t = stats.t.ppf(1-alpha/2, df=current_batch_number-1)
    var = np.var(data, ddof=1)
    mean = np.mean(data)
    min_batch = t*t * var / (precision/(1+precision) * mean)**2
    return min_batch


def print_report(report):
    if not report:
        print("No data to display.")
        return

    headers = ["Index", "Avg Queue Len", "Avg Waiting Time", "Truck Utilisation", "Rerouting Rate"]
    template = "{:<5} | {:<15} | {:<16} | {:<21} | {:<15}"
    
    print("-" * 80)
    print(template.format(*headers))
    print("-" * 80)
    
    for i, row in enumerate(report):
        batch_nr = i + 1
        q_len = f"{row.get(StatisticHolder.AVG_QUEUE_LEN, 0.0):.5f}"
        w_time = f"{row.get(StatisticHolder.AVG_WAITING_TIME, 0.0):.5f}"
        r_rate = f"{row.get(StatisticHolder.REROUTING_RATE, 0.0):.5f}"
        
        utils = row.get(StatisticHolder.TRUCK_UTILISATION, [])
        utils_str = "[" + ", ".join(f"{u:.3f}" for u in utils) + "]"
        
        print(template.format(batch_nr, q_len, w_time, utils_str, r_rate))
        
    print("-" * 80)


class StatisticHolder:
    AVG_WAITING_TIME = 'avg_waiting_time'
    AVG_QUEUE_LEN = 'avg_queue_len'
    REROUTING_RATE = 'rerouting_rate'
    TRUCK_UTILISATION = 'truck_utilisation'

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
        stats = {}
        stats[StatisticHolder.AVG_QUEUE_LEN] = self.stat_queue_len.mean(batch_time)
        stats[StatisticHolder.AVG_WAITING_TIME] = self.stat_sojourn_time.mean()
        stats[StatisticHolder.TRUCK_UTILISATION] = [util.mean(batch_time) for util in self.stat_truck_util]
        stats[StatisticHolder.REROUTING_RATE] = self.stat_rerouting_rate.rate(batch_time)
        return stats


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

    def after_hook(self, sim: Simulation, event: Event):
        empty_queues = all(len(q) == 0 for q in self.model.district_queues)
        vehicles_idle = all(truck.status.value == 0 for truck in self.model.trucks) # IDLE -> I cannot import TruckStatus enum because of circular imports
        if empty_queues and vehicles_idle:
            self.next_batch()
    
        


    
