from ct_simulation import CTScannerModel
from long_term_statistics import BatchMeansMethod, StatisticHolder as SH

def print_batch_report(report):
    if not report:
        print("No data to display.")
        return

    headers = ["Index", SH.TOTAL_PATIENTS, SH.SCANNER_UTIL_OFFICE, 
               SH.SCANNER_UTIL_OUTSIDE, SH.WAIT_TIME_OUT, SH.WAIT_TIME_EMERGENCY, 
               SH.AVG_ACCESS_TIME, SH.WAIT_OUTSIDE_ROOM, SH.INPATIENTS_OUTSIDE]
    template = "{:<5} | {:<10} | {:<15} | {:<15} | {:<10} | {:<10} | {:<10} | {:<12} | {:<15}"
    
    print("-" * 125)
    print(template.format(*headers))
    print("-" * 125)
    
    for i, row in enumerate(report):
        batch_nr = i + 1
        total = f"{row.get(SH.TOTAL_PATIENTS)}"
        s_util_office = f"{row.get(SH.SCANNER_UTIL_OFFICE, -1):.5f}"
        s_util_outside = f"{row.get(SH.SCANNER_UTIL_OUTSIDE, -1):.5f}"
        wt_out = f"{row.get(SH.WAIT_TIME_OUT, -1):.4f}"
        wt_emergency = f"{row.get(SH.WAIT_TIME_EMERGENCY, -1):.4f}"
        access_time = f"{row.get(SH.AVG_ACCESS_TIME, -1):.2f}"
        wait_outside = f"{row.get(SH.WAIT_OUTSIDE_ROOM, -1):.3f}"
        inp_outside_office = f"{row.get(SH.INPATIENTS_OUTSIDE):.3f}"
        
        print(template.format(batch_nr, total, s_util_office, s_util_outside, wt_out, wt_emergency, access_time, wait_outside, inp_outside_office))
    print("-" * 125)

def run():
    week = 7*24*60
    model = CTScannerModel(70)
    batch_means = BatchMeansMethod(model, 2*week, 4*week, 10)
    model.set_statistics_method(batch_means)
    model.run()
    report = model.report()
    print_batch_report(report)

if __name__ == "__main__":
    run()