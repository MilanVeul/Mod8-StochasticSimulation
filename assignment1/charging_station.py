import random
import os
import sys
import math
from typing import List
from __future__ import annotations

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from des_library import Simulation, Event, TimeWeightedStatistic, SampleStatistic


class Vehicle:
    def __init__(
            self, arrival_time: int, 
            battery_percentage: float, 
            reneging_event: RenegingEvent
        ):
        self.arrival_time = arrival_time
        self.battery_percentage = battery_percentage
        self.reneging_event = reneging_event


class ChargingStationModel:
    def __init__(self, num_stations: int = 4, termination_number: int = 800, seed: int = 70):
        self.seed = seed
        self.termination_number = termination_number
        self.sim = Simulation()
        self.num_stations = num_stations
        self.stations: List[Vehicle] = [None] * num_stations
        self.queue: List[Vehicle] = []

        self.init_arrivals(3000)
    
    def init_arrivals(self, num_arrivals):
        prev_time = 0
        for n in range(num_arrivals):
            time = prev_time + 15 * (1 + math.sin(n*math.pi / 12))**2 + 2
            arrival_event = ArrivalEvent(time, self, n)
            self.sim.schedule(arrival_event)
            prev_time = time

    def end_service(self, leaving_vehicle: Vehicle):
        for veh in self.stations:
            if veh != leaving_vehicle: continue
            # TODO: Log statistics
            # Replace the vehicle with the first in queue
            veh = self.queue.pop(0)
            break


######################################

class ArrivalEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel, vehicle_number: int):
        super().__init__(time)
        self.model = model
        self.vehicle_number = vehicle_number
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        battery_percentage = 0.5 * abs(math.sin(self.vehicle_number * math.pi / 7) + 1)
        patience = 20 * (1 + abs(math.cos(self.vehicle_number * math.e)))
        reneging_event = RenegingEvent(sim.current_time + patience, self.model)
        new_vehicle = Vehicle(sim.current_time, battery_percentage, reneging_event)

class RenegingEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        sim.cancel()

class DepartureEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
