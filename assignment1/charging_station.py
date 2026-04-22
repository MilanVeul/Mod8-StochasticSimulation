from __future__ import annotations
import random
import os
import sys
import math
import bisect
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from des_library import Simulation, Event, TimeWeightedStatistic, SampleStatistic


class Vehicle:
    def __init__(
            self, 
            vehicle_number: int,
            arrival_time: int, 
            battery_percentage: float
        ):
        self.number = vehicle_number
        self.arrival_time = arrival_time
        self.battery_percentage = battery_percentage
        self.depature_event: DepartureEvent = None
        self.reneging_event: RenegingEvent = None
        self.charging_start: int = -1


class ChargingStationModel:
    def __init__(self, num_stations: int = 4, termination_number: int = 800, seed: int = 70):
        random.seed(seed)

        self.termination_number = termination_number
        self.sim = Simulation()
        self.num_stations = num_stations

        self.stations: List[Vehicle] = []
        self.queue: List[Vehicle] = []
        
        self.completions: int = 0

    def run(self):
        schedule_arrival(self.sim, 0, self)
        self.sim.run()
    
    def queue_vehicle(self, vehicle):
        self.queue.append(vehicle)

    def leave_queue(self, vehicle):
        self.queue.remove(vehicle)

    def charge_vehicle(self, vehicle):
        if len(self.stations) >= self.num_stations: 
            raise Exception("Station is full!")
        self.stations.append(vehicle)
        print(f"Vehicle {vehicle.number} charges. Status: {len(self.stations)}/{self.num_stations}")

    def leave_charging(self, leaving_vehicle: Vehicle) -> Optional[Vehicle]:
        """Removes vehicle from charging stations and removes and returns the first vehicle in queue."""
        
        self.stations.remove(leaving_vehicle)

        first_vehicle = None
        if len(self.queue) > 0:
            first_vehicle = self.queue[0]

        self.completions += 1
        if self.completions >= self.termination_number:
            # TODO: Report statistics
            print("Simulation ended")
            self.sim.stop()
            return None
        return first_vehicle
    
    @property
    def has_capacity(self) -> bool:
        return len(self.stations) < self.num_stations
    

######################################

def schedule_arrival(sim: Simulation, vehicle_number: int, model: ChargingStationModel):
    time = sim.current_time + 15 * (1 + math.sin(vehicle_number*math.pi / 12))**2 + 2
    arrival_event = ArrivalEvent(time, model, vehicle_number+1)
    sim.schedule(arrival_event)

def get_charging_duration(vehicle: Vehicle):
    return 60 * (1-vehicle.battery_percentage)

def schedule_departure_event(sim: Simulation, vehicle: Vehicle, model: ChargingStationModel):
    vehicle.charging_start = sim.current_time
    dep_time = sim.current_time + get_charging_duration(vehicle)
    dep_event = DepartureEvent(dep_time, vehicle, model)
    vehicle.depature_event = dep_event
    sim.schedule(dep_event)

class ArrivalEvent(Event):
    def __init__(self, time: float, model: ChargingStationModel, vehicle_number: int):
        super().__init__(time)
        self.model = model
        self.vehicle_number = vehicle_number
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        print(f"Vehicle {self.vehicle_number} arrived.")
        battery_percentage = 0.5 * abs(math.sin(self.vehicle_number * math.pi / 7) + 1)

        if len(self.model.queue) == 0 and self.model.has_capacity:
            new_vehicle = Vehicle(self.vehicle_number, sim.current_time, battery_percentage)
            self.model.charge_vehicle(new_vehicle)
            schedule_departure_event(sim, new_vehicle, self.model)
        else:
            patience = 20 * (1 + abs(math.cos(self.vehicle_number * math.e)))
            new_vehicle = Vehicle(self.vehicle_number, sim.current_time, battery_percentage)
            reneging_event = RenegingEvent(sim.current_time + patience, new_vehicle, self.model)
            new_vehicle.reneging_event = reneging_event
            self.model.queue_vehicle(new_vehicle)
            sim.schedule(reneging_event)

        # Schedule new arrival
        schedule_arrival(sim, self.vehicle_number, self.model)

class RenegingEvent(Event):
    def __init__(self, time: float, vehicle: Vehicle, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
        self.vehicle = vehicle
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        print(f"A Vehicle renegated.")
        self.model.leave_queue(self.vehicle)

class DepartureEvent(Event):
    def __init__(self, time: float, vehicle: Vehicle, model: ChargingStationModel):
        super().__init__(time)
        self.model = model
        self.vehicle = vehicle
    
    def execute(self, sim: Simulation):
        if self.cancelled: return
        print(f"Vehicle {self.vehicle.number} left.")
        # Replace vehicle in charging station
        new_vehicle = self.model.leave_charging(self.vehicle)

        if not new_vehicle: return
        new_vehicle.reneging_event.cancel()
        self.model.leave_queue(new_vehicle)
        self.model.charge_vehicle(new_vehicle)
        schedule_departure_event(sim, new_vehicle, self.model)

        # Handle early departure
        queue_len = len(self.model.queue)
        if queue_len > 0 and queue_len % 5 == 0:
            for veh in self.model.queue:
                departure_time = veh.charging_start + 60 * (1-veh.battery_percentage)
                if departure_time - sim.current_time <= 15: continue
                if random.random(0,1) > 0.2: continue
                print(f"Vehicle is departing early.")
                # Cancel original departure event
                veh.depature_event.cancel()
                # Create early departure event
                early_dep_time = sim.current_time + 2
                early_dep_event = DepartureEvent(early_dep_time, veh, self.model)
                veh.depature_event = early_dep_event
                sim.schedule(early_dep_event)


if __name__ == "__main__":
    model = ChargingStationModel(4, 800)
    model.run()

