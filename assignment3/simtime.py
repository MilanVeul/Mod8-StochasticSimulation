def day(simulation_time: int):
    return simulation_time % (24*60)

def weekday(simulation_time: int):
    return day(simulation_time) % 7