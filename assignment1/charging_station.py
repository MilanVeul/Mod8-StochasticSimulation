import random
import os
import sys
import math
import bisect
from typing import List
from __future__ import annotations

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from des_library import Simulation, Event, TimeWeightedStatistic, SampleStatistic


class Vehicle:
    def __init__(
            self, 
            arrival_time: int, 
            battery_percentage: float, 
            reneging_event: RenegingEvent
        ):
        self.arrival_time = arrival_time
        self.battery_percentage = battery_percentage
        self.reneging_event: RenegingEvent = reneging_event
        self.depature_event: DepartureEvent = None
        self.charging_start: int = -1


class ChargingStationModel:
    def __init__(self, num_stations: int = 4, termination_number: int = 800, seed: int = 70):
        self.seed = seed
        self.termination_number = termination_number
        self.sim = Simulation()
        self.num_stations = num_stations

        self.stations: List[Vehicle] = [None] * num_stations
        self.num_vehicles_charging = 0
        self.queue: List[Vehicle] = []
        
        self.completions: int = 0 

        self.init_arrivals(3000)
    
    def init_arrivals(self, num_arrivals):
        prev_time = 0
        for n in range(num_arrivals):
            time = prev_time + 15 * (1 + math.sin(n*math.pi / 12))**2 + 2
            arrival_event = ArrivalEvent(time, self, n)
            self.sim.schedule(arrival_event)
            prev_time = time
    
    def leave_queue(self, vehicle):
        self.queue.remove(vehicle)

    def charge_vehicle(self, vehicle):
        if self.num_vehicles_charging >= self.num_stations: return
        self.queue.append(vehicle)
        self.num_vehicles_charging += 1

    def end_service(self, leaving_vehicle: Vehicle) -> Vehicle:
        self.stations.remove(leaving_vehicle)
        
        if len(self.queue) > 0:
            first_vehicle = self.queue.pop(0)
            self.stations.append(first_vehicle)
        else:
            self.num_vehicles_charging -= 1

        self.completions += 1
        if self.completions >= self.termination_number:
            # TODO: Report statistics
            self.sim.stop()
        return first_vehicle

######################################

def get_charging_duration(vehicle: Vehicle):
    return 60 * (1-vehicle.battery_percentage)

class ArrivalEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel, vehicle_number: int):
        super().__init__(time)
        self.model = model
        self.vehicle_number = vehicle_number

    def schedule_arrival(self):
        time = self.current_time + 15 * (1 + math.sin(self.vehicle_number*math.pi / 12))**2 + 2
        arrival_event = ArrivalEvent(time, self, self.vehicle_number + 1)
        self.sim.schedule(arrival_event)
    
    def execute(self, sim: Simulation):
        if self.cancelled: return

        battery_percentage = 0.5 * abs(math.sin(self.vehicle_number * math.pi / 7) + 1)

        if len(self.model.queue) == 0:
            new_vehicle = Vehicle(sim.current_time, battery_percentage, None)
            self.model.charge_vehicle(new_vehicle)
            schedule_departure_event(sim, new_vehicle, self.model)
        else:
            patience = 20 * (1 + abs(math.cos(self.vehicle_number * math.e)))
            reneging_event = RenegingEvent(sim.current_time + patience, self.model)
            new_vehicle = Vehicle(sim.current_time, battery_percentage, reneging_event)
            self.model.queue_vehicle(new_vehicle)

class RenegingEvent(Event):
    def __init__(self, time: float, vehicle: Vehicle, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
        self.vehicle = vehicle
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        self.model.leave_queue(self.vehicle)

def schedule_departure_event(sim: Simulation, vehicle: Vehicle, model: ChargingStationModel):
    vehicle.set_charging_start(sim.current_time)
    dep_time = sim.current_time + get_charging_duration(vehicle)
    dep_event = DepartureEvent(dep_time, vehicle, model)
    vehicle.depature_event = dep_event
    sim.schedule(dep_event)


class DepartureEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        # Replace vehicle in charging station
        new_vehicle = self.model.end_service(self.vehicle)

        # Schedule new departure event
        schedule_departure_event(sim, new_vehicle, self.model)

        # Handle early departure
        queue_len = len(self.model.queue)
        if queue_len > 0 and queue_len % 5 == 0:
            for veh in self.model.queue:
                departure_time = veh.charging_start + 60 * (1-veh.battery_percentage)
                if departure_time - sim.current_time <= 15: continue
                if random.random(0,1) > 0.2: continue
                # Cancel original departure event
                veh.depature_event.cancel()
                # Create early departure event
                early_dep_time = sim.current_time + 2
                early_dep_event = DepartureEvent(early_dep_time, veh, self.model)
                veh.depature_event = early_dep_event
                sim.schedule(early_dep_event)

