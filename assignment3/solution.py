from ct_simulation import CTScannerModel
from long_term_statistics import BatchMeansMethod

def run():
    model = CTScannerModel(70)
    batch_means = BatchMeansMethod(model, 0, 10000, 50)
    model.set_statistics_method(batch_means)
    model.run()
    report = model.report()


if __name__ == "__main__":
    run()