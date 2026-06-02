def day(simulation_time: int):
    return simulation_time // (24*60)

def daytime(simulation_time: int):
    return simulation_time % (60*24)

def weekday(simulation_time: int):
    return day(simulation_time) % 7