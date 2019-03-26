import hysysopt
import numpy as np
import pandas as pd
from costing import column_cost_function, hx_cost_function

opt = hysysopt.init()

opt.get_params('opt')

opt.optimize_feed_location("C-3501", "Solvent", lb_frac=0, ub_frac=0.7)
opt.optimize_feed_location("C-3501", "Heated Feed", lb_frac=0.3, ub_frac=1)

opt.attach_cost_function(column_cost_function, optype="columns")
opt.attach_cost_function(hx_cost_function, optype="heatexchangers")

opt.set_column_efficiency('C-3501', 0.62240826)

opt.display_convergence = True

params = opt.get_current_params()

print("Original parameters are: ", params)

# Number of stages is 0th variable, and column pressure is 1st variable
# Bounds of no. of stages is (40, 81), bounds of column pressure is (120, 160)
X = np.linspace(40, 81, num=20)
Y = np.linspace(120, 160, num=20)
X, Y = np.meshgrid(X, Y)

x_idx = 0
y_idx = 1

# List of variables that will be varied
varlist = np.repeat(np.array(params).reshape(1, -1), X.size, axis=0)

print(varlist.shape)
varlist[:, x_idx] = X.flatten()
varlist[:, y_idx] = Y.flatten()

try:
    costs = []
    for set_of_params in varlist:
        costs.append(opt.objective_function(set_of_params))
finally:
    # Always try to reset back to original settings if something goes wrong/user interrupted during the process.
    print("Interrupted, resetting Hysys file to original settings. Please do not exit.")
    opt.objective_function(params)
    print("Reset complete.")

df = pd.DataFrame({
    "X": X.flatten(),
    "Y": Y.flatten(),
    "cost": costs
})

df.to_csv("grid_data.csv")
