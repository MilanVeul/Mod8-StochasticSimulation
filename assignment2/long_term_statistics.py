import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from typing import TYPE_CHECKING
from des_library import SampleStatistic, TimeWeightedStatistic, Counter, Simulation, Event
from waste_collection import TruckStatus
if TYPE_CHECKING:
    from waste_collection import WasteCollectionModel




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


    def next_batch(self):
        if self.batch_number != 0:
            self.reports.append(self.report(self.batch_len))

        self.batch_start = self.model.sim.current_time
        self.batch_number += 1
        self.reset()

        if self.batch_number > self.num_batches:
            self.model.sim.stop()

    def before_hook(self, sim: Simulation, event: Event): pass
    def after_hook(self, sim: Simulation, event: Event): pass
    

class BatchMeansMethod(LongTermStatistic):
    def __init__(self, model: 'WasteCollectionModel', warmup_time: int, batch_len: int, num_batches: int):
        super().__init__(model, num_batches)

        self.warmup_time = warmup_time
        if warmup_time == 0:
            self.batch_number = 1
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
        vehicles_idle = all(truck.status == TruckStatus.IDLE for truck in self.model.trucks)
        
    
        


    
