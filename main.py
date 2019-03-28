'''
This is an example of sample usage of the optimizer package.
'''

import hysysopt
from costing import column_cost_function, hx_cost_function

# Establishes the connection to the HYSYS COM interface and collects basic data
# about the case such as what kind of operations it has (e.g. dist columns).
opt = hysysopt.init()

# Links up to a HYSYS spreadsheet object which contains the optimization variables.
# Each row should be: | var_import | lower_bound | upper_bound |
opt.get_params('opt')

# Adds feed stage location parameter to the optimization variable list.
# Lower and upper bounds are specified as a fraction of the total stages.
# The column name and stream name are specified.
opt.optimize_feed_location("C-3501", "Solvent", lb_frac=0, ub_frac=0.7)
opt.optimize_feed_location("C-3501", "Heated Feed", lb_frac=0.3, ub_frac=1)

# Shows all the optimization parameters for confirmation before the program runs.
opt.list_params()

# Attaches cost functions to each type of equipment for the optimizer to minimize.
opt.attach_cost_function(column_cost_function, optype="columns")
opt.attach_cost_function(hx_cost_function, optype="heatexchangers")

# [OPTIONAL] Sets the column tray overall efficiency. Every time the column
# changes its number of stages, the efficiency spec is removed. This command
# ensures that the efficiency is continuously reapplied whenever the number
# of stages is changed.
opt.set_column_efficiency('C-3501', 0.62240826)

# Run the optimizer while saving the output data out for visualization later.
opt.display_convergence = True
opt.set_save_location('actual_1.csv')
opt.run(n_iter=20, num=40, save_data=True)

# Sets the HYSYS case file to the optimal params found by the optimizer.
opt.set_to_optimal()

# Recalculates costs to show what the final total annualized cost for this set
# of optimal params is.
opt.show_individual_costs()
