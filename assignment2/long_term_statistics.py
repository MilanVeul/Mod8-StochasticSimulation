import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from typing import TYPE_CHECKING
from des_library import SampleStatistic, TimeWeightedStatistic, Counter
if TYPE_CHECKING:
    from waste_collection import WasteCollectionModel




class StatisticHolder:
    AVG_WAITING_TIME = 'avg_waiting_time'
    AVG_QUEUE_LEN = 'avg_queue_len'
    REROUTING_RATE = 'rerouting_rate'
    TRUCK_UTILISATION = 'truck_utilisation'

    def __init__(self, model: "WasteCollectionModel"):
        self.model = model
        self.stat_sojourn_time = SampleStatistic()
        self.stat_rerouting_rate = Counter()
        self.stat_queue_len = TimeWeightedStatistic()
        self.stat_truck_util = [TimeWeightedStatistic() for _ in self.model.trucks]
        for stat in self.stat_truck_util:
            stat.update(self.model.sim.current_time, False)

    def reset(self):
        """Resets all statistics"""
        time = self.model.sim.current_time
        self.stat_sojourn_time.reset()
        self.stat_rerouting_rate.reset()
        self.stat_queue_len.reset()
        self.stat_queue_len.update(time, 0)
        for util in self.stat_truck_util:
            util.reset()
            util.update(time, False)

    def report(self, time):
        stats = {}
        stats[StatisticHolder.AVG_QUEUE_LEN] = self.stat_queue_len.mean(time)
        stats[StatisticHolder.AVG_WAITING_TIME] = self.stat_sojourn_time.mean()
        stats[StatisticHolder.TRUCK_UTILISATION] = [util.mean(time) for util in self.stat_truck_util]
        stats[StatisticHolder.REROUTING_RATE] = self.stat_rerouting_rate.rate(0) #TODO
        return stats

class BatchMeansMethod(StatisticHolder):
    def __init__(self, model: 'WasteCollectionModel'):
        super().__init__(model)
        self.current_batch = 0 # Warm up

    def before_hook(self, sim, event):
        pass

    
