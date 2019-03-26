import hysysopt
from costing import column_cost_function, hx_cost_function

opt = hysysopt.init()

opt.get_params('opt')

opt.optimize_feed_location("C-3501", "Solvent", lb_frac=0, ub_frac=0.7)
opt.optimize_feed_location("C-3501", "Heated Feed", lb_frac=0.3, ub_frac=1)

opt.list_params()

opt.attach_cost_function(column_cost_function, optype="columns")
opt.attach_cost_function(hx_cost_function, optype="heatexchangers")

opt.set_column_efficiency('C-3501', 0.62240826)

opt.display_convergence = True
opt.set_save_location('actual_1.csv')
opt.run(n_iter=20, num=40, save_data=True)

opt.set_to_optimal()
opt.show_individual_costs()
