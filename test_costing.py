import hysysopt
from costing import column_cost_function, hx_cost_function

opt = hysysopt.init()

opt.attach_cost_function(column_cost_function, optype="columns")
opt.attach_cost_function(hx_cost_function, optype="heatexchangers")

opt.show_individual_costs()