import random
import os
import sys
from collections import deque
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from des_library import Simulation, Event, TimeWeightedStatistic, SampleStatistic

class Vehicle:
    def __init__(self, arrival_time: int, battery_percentage: float):
        self.arrival_time = arrival_time
        self.battery_percentage = battery_percentage

class ChargingStationModel:
    def __init__(self, num_stations: int = 4, termination_number: int = 800, seed: int = 70):
        self.seed = seed
        self.termination_number = termination_number
        self.sim = Simulation()
        self.num_stations = num_stations
        self.stations: List[Vehicle] = [None] * num_stations
        self.queue: deque[Vehicle] = deque()

######################################

class ArrivalEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
    
    def execute(self, sim: Simulation):
        pass

class RenegingEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
    
    def execute(self, sim: Simulation):
        pass

class DepartureEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
    
    def execute(self, sim: Simulation):
        pass