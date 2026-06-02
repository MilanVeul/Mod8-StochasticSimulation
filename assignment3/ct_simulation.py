from __future__ import annotations
import sys, os, random, math
from enum import Enum
from typing import List, Optional
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from des_library import Simulation, Event, Uniform, Exponential

import simtime

NUM_CHAIRS = 3
NUM_SCANNERS_OFFICE_HOURS = 2
NUM_SCANNERS_OUTSIDE_OFFICE_HOURS = 1

class PatientType(Enum):
    IN = 1
    OUT = 2
    EMERGENCY = 3

class Patient:
    def __init__(self, patient_type: PatientType, request_day: int):
        self.type: PatientType = patient_type
        self.request_day: int = request_day 
        self.arrival_time: int = -1

class CTScannerModel:
    def __init__(self, seed: int):
        self.sim: Simulation = Simulation()
        self.init_distribution(seed)

        self.emergency_queue: List = []
        self.normal_queue: List = []
        
        # Simulation starts in the night
        self.active_scanners = 0

    def init_distribution(self, seed):
        random.seed(seed)
        self.distr_scan_time = Uniform(10, 19)
        self.distr_emergency_patients = Exponential(24 / 24 * 60)
        self.distr_out_patients = Exponential(24 / 23 * 60)
        self.distr_in_patients = Exponential(24 / 153 * 60)

    def add_to_queue(self, patient: Patient):
        """Adds a patient to the correct priority queue."""
        if patient.type == PatientType.EMERGENCY:
            self.emergency_queue.append(patient)
        else:
            self.normal_queue.append(patient)
    
    def next_patient(self) -> Optional[Patient]:
        """Removes the first patient from the queue and returns it."""
        if len(self.emergency_queue) > 0:
            return self.emergency_queue.pop(0)
        if len(self.normal_queue) > 0:
            return self.normal_queue.pop(0)
        return None

    @property
    def queue_size(self) -> int:
        """Returns the total queue size."""
        return len(self.normal_queue) + len(self.emergency_queue)
    
    @property
    def in_office_hours(self) -> bool:
        time = self.sim.current_time
        weekday = simtime.day(time) <= 4
        office_hours = 8*60 <= simtime.daytime(time) <= 16*60
        if weekday and office_hours:
            return True
        return False
    
    @property
    def scanners(self) -> int:
        if self.in_office_hours:
            return NUM_SCANNERS_OFFICE_HOURS
        return NUM_SCANNERS_OUTSIDE_OFFICE_HOURS



class RequestScanEvent(Event):
    """Handles a request for a scan for all patient types, and schedules a new request."""
    def __init__(self, time, model, patient_type: PatientType):
        super().__init__(time)
        self.model: CTScannerModel = model
        self.patient_type = patient_type

    def get_current_inpatient_rate(self, simulation_time):
        """Returns the rate of the inpatient requests as determined in the project report."""
        daytime = simtime.day_time(simulation_time)
        if daytime < 9*60 or daytime > 15*60:
            return 9 / (24*60) 
        else:
            return 9 + 72 * (1 + math.cos(2*math.pi*daytime / 180 + math.pi)) / (24*60)
    
    def next_inpatient_request_time(self, simulation_time):
        """Returns the next inpatient request time."""
        time = simulation_time
        while True:
            time = time + self.model.distr_in_patients.sample()

            current_rate = self.get_current_inpatient_rate(time)
            lambda_zero = 1 / self.model.distr_in_patients_office.mean
            p = current_rate / lambda_zero

            if random.random() < p:
                return time # We accept this sample

    def execute(self, sim: Simulation):
        request_day = simtime.day(sim.current_time)
        patient = Patient(self.patient_type, request_day)

        if patient.type == PatientType.EMERGENCY:
            # Place in queue immediately.
            arrival_event = ArrivalEvent(sim.current_time, self.model, patient)
            sim.schedule(arrival_event)
            return
    
        # Schedule patient
        # TODO

        # Schedule next request
        if self.patient_type == PatientType.EMERGENCY:
            next_request_time = sim.current_time + self.model.distr_emergency_patients.sample()
        elif self.patient_type == Patient.OUT:
            next_request_time = sim.current_time + self.model.distr_out_patients.sample()
        elif self.patient_type == Patient.IN:
            next_request_time =  self.next_inpatient_request_time(sim.current_time)

        next_request = RequestScanEvent(next_request_time, self.model, patient.type)
        sim.schedule(next_request)



class ArrivalEvent(Event):
    """Handles the arrival of a Patient in the waiting room. Places the patient in the queue."""
    def __init__(self, time, model, patient: Patient):
        super().__init__(time)
        self.model: CTScannerModel = model
        self.patient: Patient = patient

    def execute(self, sim: Simulation):
        self.patient.arrival_time = sim.current_time

        if self.model.active_scanners < self.model.scanners:
            start_event = StartScanEvent(self.model, sim.current_time, self.patient)
            sim.schedule(start_event)
            return
        # No scanners available; place in queue
        self.model.add_to_queue(self.patient)


class StartScanEvent(Event):
    """Handles the start of a CT scan. Samples the scan time uniformly."""
    def __init__(self, model: CTScannerModel, time, patient: Patient):
        super().__init__(time)
        self.model: CTScannerModel = model
        self.patient = patient
    
    def execute(self, sim: Simulation):
        scan_time = self.model.distr_scan_time.sample()
        end_time = sim.current_time + scan_time
        end_event = EndScanEvent(self.model, end_time)
        sim.schedule(end_event)
        self.model.active_scanners += 1

class EndScanEvent(Event):
    """Handles the end of a CT scan. Starts the scan of next patient if present."""
    def __init__(self, model: CTScannerModel, time):
        super().__init__(time)
        self.model: CTScannerModel = model
    
    def execute(self, sim: Simulation):
        next_patient = self.model.next_patient()
        if next_patient is None:
            return  # Queue is empty
        start_event = StartScanEvent(self.model, sim.current_time, next_patient)
        sim.schedule(start_event)
        self.model.active_scanners -= 1
    
