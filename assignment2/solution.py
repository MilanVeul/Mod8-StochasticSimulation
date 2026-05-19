from waste_collection import WasteCollectionModel
from long_term_statistics import StatisticHolder, BatchMeansMethod, RegenerativeMethod, print_report, min_batch_number

alpha = 0.05
precision = 0.01
num_batches = 50

def get_stat(report, stat: str):
    data = [batch[stat] for batch in report]
    if isinstance(data[0], list):
        # Transpose so rows represent trucks, and columns represent batches
        return [list(row) for row in zip(*data)]
    return data

def run():
    model = WasteCollectionModel(seed=70)

    # Initiate statistic method
    stat_method = BatchMeansMethod(model, 0, 50000, num_batches)
    # stat_method = RegenerativeMethod(model, 1000)
    model.set_statistics_method(stat_method)

    model.run()
    report = model.report()

    print_report(report)

    print("\nMinimal batch numbers:")
    print("  Waiting time  ", min_batch_number(num_batches, get_stat(report, StatisticHolder.AVG_WAITING_TIME), precision=precision, alpha=alpha))
    print("  Queue len     ", min_batch_number(num_batches, get_stat(report, StatisticHolder.AVG_QUEUE_LEN), precision=precision, alpha=alpha))
    print("  Truck util    ", [min_batch_number(num_batches, truck, precision=precision, alpha=alpha) for truck in get_stat(report, StatisticHolder.TRUCK_UTILISATION)])
    print("  Rerouting     ", min_batch_number(num_batches, get_stat(report, StatisticHolder.REROUTING_RATE), precision=precision, alpha=alpha))


if __name__ == "__main__":
    run()