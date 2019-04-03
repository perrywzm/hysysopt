import sys
import time
import csv
import numpy as np
import pandas as pd
from .optimizers.pso import PSO


INF = 1e9


class HysysOptimizer:
    def __init__(self, case, ops, m_streams, e_streams):
        '''
        Constructor for the main Hysys Optimizer class.

        Args:
            case: Hysys case file COM object
            ops: List of acquired Hysys case file operations
            m_streams: List of acquired Hysys case file material streams
            e_streams: List of acquired Hysys case file energy streams
        '''

        # Main COM interface objects
        self.case = case
        self.operations = ops
        self.m_streams = m_streams
        self.e_streams = e_streams

        # Parameter and cost function lists
        self.params = []
        self.efficiency_specs = []
        self.cost_funcs = []

        # Lists of potentially costed operations
        self.columns = []
        self.exchangers = []
        self.exclusions = []

        # Additional parameters
        self.display_convergence = False
        self.save_loc = "data.csv"

        # Special functions
        self.get_column_deltaP = _default_column_pressure_drop


    def get_opt_vars(self, sheet_name):
        '''
        Automatic variable acquisition from the specified spreadsheet. Search string is not case-sensitive.
        Requires the HYSYS parameters to be listed in the following format:

         -------------------------------------------------
        | param 1 to optimize | lower bound | upper bound |
        | param 2 to optimize | lower bound | upper bound |
        | param 3 to optimize | lower bound | upper bound |
        | etc...              |             |             |
         -------------------------------------------------

        Args:
            sheet_name: Name of spreadsheet object in Hysys case file
        '''

        print("Initializing optimization variables...")
        results = list(filter(lambda o: o.name.lower() == sheet_name.lower(), self.operations))
        # Terminate if no matching operations are found
        if len(results) <= 0:
            raise LookupError("Spreadsheet object does not exist!")

        # Take the first hit of the search
        ss = results[0]
        print("... Acquired {} optimizer spreadsheet object".format(ss.name))

        # Extract out parameter data from spreadsheet
        # Each parameter will be a dictionary of {"name", "value", "lb", "ub", "unit"}

        # Sanity check for number of columns
        if ss.NumberOfColumns < 3:
            raise ValueError("Invalid variable inputs!")

        # Extract info from each row
        for i in range(1, ss.NumberOfRows + 1):
            cell = ss.Cell(_get_cell_ref(i, 1))

            # 1. Validation and name info extraction
            name = cell.VariableName
            # If there's no attached variable, invalid input or ended search
            if name == "":
                break

            # 2. Extract value and units
            unit = cell.Units
            value = cell.ImportedVariable.GetValue(unit)

            # 4. Extract lower and upper bounds
            try:
                lb = ss.Cell(_get_cell_ref(i, 2)).CellValue
                ub = ss.Cell(_get_cell_ref(i, 3)).CellValue
            except Exception as e:
                raise ValueError("Could not read valid lower/upper bounds of row {}!".format(i))

            param = {"name": name, "value": value, "lb": lb, "ub": ub, "unit": unit, "interface": cell}

            # 5. Special considerations if the variable is the column pressure parameter
            if name == "Top Stage Press":
                print("Column condenser pressure detected! Linking bottom pressure with condenser pressure...")
                if ss.Cell(_get_cell_ref(i, 4)).VariableName != "Bottom Stage Press":
                    raise ValueError("Bottom pressure cell not found! Please link column bottom pressure "
                        + "to {}.".format(_get_cell_ref(i, 4)))
                print("Linked column reboiler pressure with cell {}. Using default 0.1psi pressure drop per tray.".format(_get_cell_ref(i, 4)))
                print("Note: Please refer to the set_column_deltaP() method to change the pressure drop calculation method.")
                
                param["col_interface"] = None
                param["btm_interface"] = ss.Cell(_get_cell_ref(i, 4))

            # 6. Add the parameter to the list
            self.params.append(param)
            print("... Identified: {}{} with lb={}, ub={}".format(
                param["name"], " ({})".format(unit) if unit != "" else "", param["lb"], param["ub"]))

        print("Acquired {} optimization variables. Please ensure that this number is correct.".format(len(self.params)))
        return self.params

    def optimize_feed_location(self, col_name, stream_name=None, lb_frac=0.1, ub_frac=0.9):
        '''
        Adds the feed location as an optimization variable. Location is specified by fraction of the tower's total
        trays. (E.g. 0.2 of a 100 stage column places the feed location at 20)

        Args:
            col_name: Column name. Case-insensitive.
            lb_frac: Lower bound of fraction position (0 to 1) Default value: 0.1
            ub_frac: Upper bound of fraction position (0 to 1 and greater than lb_frac) Default value: 0.9
            stream_name: Feed stream name. If left as None, will default to the first feed stream. Optional for single-
                feed column. Case-insensitive.
        '''

        print("Adding Feed Location optimization variable...")
        result = list(filter(lambda o: o.name.lower() == col_name.lower(), self.operations))

        if len(result) == 0:
            raise LookupError("Failed to find column with matching column name!")

        col = result[0]
        found = False
        for f in col.ColumnFlowsheet.FeedStreams.Names:
            s = col.ColumnFlowsheet.FeedStreams.Item(f)
            if s.TypeName == "materialstream":
                if stream_name is None:
                    # Since no stream name is specified, we just use the first material feed stream we can find.
                    found = True
                    break
                elif stream_name.lower() == f.lower():
                    # Stream specified has been found
                    found = True
                    break

        if not found:
            raise LookupError("Failed to find stream in specified column operation!")

        param = {"name": col.name + ": Feed Location (" + f + ")",
                 "stream_name": f,
                 "value": -1,
                 "lb": lb_frac,
                 "ub": ub_frac,
                 "unit": "feed_location",
                 "interface": col,
                 "stream_interface": s}

        print("... Identified: {}, lb={}, ub={}".format(param["name"], param["lb"], param["ub"]))

        self.params.append(param)
        print("{} variables currently identified.".format(len(self.params)))

    def list_params(self):
        for p in self.params:
            print("{}: lb={} ub={} unit={}".format(p["name"], p["lb"], p["ub"], p["unit"]))

    def attach_cost_function(self, cost_func, optype=None):
        '''
        Defines the cost functions for each operation. Link it to a function that contains strategies
        for determining the costs for the optimizer to minimize.

        Can specify the cost function of a particular operation or for a particular type of operation.

        Args:
            cost_func: Cost function to optimize for
            optype: Name of the type of operation to set the cost function for.
                Available: (Not case-sensitive)
                1. Columns
                2. Heaters/Coolers

        '''
        if optype is None:
            raise ValueError("No operation type or name was supplied.")
        
        if optype.lower() == "columns":
            print("Detected distillation column as optype. Ensure the cost function handles a Column object and " +
                "not the COM object itself.")
        elif optype.lower() == "heatexchangers":
            print("Detected heat exchangers as optype. Ensure the cost function handles the heater/cooler COM object.")
        else:
            raise NotImplementedError("Type of operation specified is unknown!")
        self.cost_funcs.append({"fn": cost_func, "op": optype.lower()})

    def run(self, n_iter=20, num=20, algo="pso", save_data=False):
        if len(self.cost_funcs) == 0:
            raise ValueError("No cost functions were supplied!")
        
        # Save settings
        callback = self.save_current_iteration if save_data else None

        if algo == "pso":
            pso = PSO(objfunc=self.objective_function,
                      num=num,
                      lb=[p["lb"] for p in self.params],
                      ub=[p["ub"] for p in self.params])
            
            
            pso.run(n_iter, callback=callback)

            self.optimal_params = pso.global_best
        else:
            raise NotImplementedError("Algorithm type supplied is either not implemented or unknown.")
    
    def save_current_iteration(self, idx, x, y):
        output = np.concatenate([x, y.reshape(-1,1)], axis=1).flatten()
        df = pd.DataFrame([output], index=None)
        df.to_csv(self.save_loc, mode='a', header=False, index=False)


    def set_save_location(self, filepath):
        '''
        Data is saved in the following format:
        Each iteration is saved as an entire row in the .csv
        Each row is composed of each set of parameters followed by their cost.
        Example:
        If we have an input (a, b, c) and an output y, and 2 particles, the iteration will be saved in the .csv as:
        a1, b1, c1, y1, a2, b2, c2, y2
        '''
        self.save_loc = filepath

    def objective_function(self, x):
        '''
        Takes in a set of new vars to load into the HYSYS model. Runs all the provided cost functions
        to obtain the final cost.
        '''

        # Reset the columns
        for col in self.columns:
            col.op.ColumnFlowsheet.Reset()

        # Update the parameters (We reset params for both paused and unpaused modes to ensure that all changes will be made)
        for solver_state in range(2):
            self.case.Solver.CanSolve = solver_state

            for i, p in enumerate(self.params):
                if p["unit"] == "feed_location":
                    feed_stage = round(x[i] * p["interface"].ColumnFlowsheet.Operations.Item(0).NumberOfTrays)
                    p["interface"].ColumnFlowsheet.Operations.Item(0).SpecifyFeedLocation(p["stream_interface"], feed_stage)
                elif p["name"] == "Top Stage Press":
                    # Erase column pressures before setting new ones (erasing once is enough)
                    if solver_state == 0:
                        p["interface"].ImportedVariable.Erase()
                        p["btm_interface"].ImportedVariable.Erase()
                    continue
                else:
                    p["interface"].ImportedVariable.SetValue(x[i], p["unit"])

        # Update column pressures
        for i, p in enumerate(self.params):
            if p["name"] == "Top Stage Press":
                # Get columnflowsheet operation and parameters
                cfs_op = p[i]["interface"].ImportedVariable.Parent.ColumnFlowsheet
                n_trays = cfs_op.Operations.Item(0).NumberOfTrays
                dp_cond = cfs_op.Operations.Item(1).VesselPressureDrop.GetValue('kPa')
                dp_reb = cfs_op.Operations.Item(2).VesselPressureDrop.GetValue('kPa')
                pressure_drop = self.get_column_deltaP(x[i], n_trays, dp_cond, dp_reb)

                # Set condenser pressure
                p["interface"].ImportedVariable.SetValue(x[i], p["unit"])

                # Set reboiler pressure
                p["btm_interface"].ImportedVariable.SetValue(pressure_drop, p["unit"])
        
        # Set efficiency (requires solver pause)
        if len(self.efficiency_specs) > 0:
            self.case.Solver.CanSolve = False
            for col, eff in self.efficiency_specs:
                ss_interface = col.tower.SeparationStages
                n = len(ss_interface.Names)
                for i in range(n):
                    ss_interface.Item(i).OverallEfficiency.SetValue(eff)

            self.case.Solver.CanSolve = True

        # Run the columns
        for col in self.columns:
            col.op.ColumnFlowsheet.Run()
        
        # Small delay for stability
        time.sleep(0.2)

        # Check for column convergence. If any column is not converged, we will reject the current
        # set of parameters and return an infinite cost value.
        t = time.time()
        for col in self.columns:
            while col.op.ColumnFlowsheet.SolvingStatus or (time.time() - t) > 3:
                time.sleep(0.25)

        # Small delay for stability
        time.sleep(0.2)

        for col in self.columns:
            if not col.op.ColumnFlowsheet.CfsConverged:
                return INF

        cost = self.calculate_costs()
        if self.display_convergence:
            print("Columns converged at {} with cost of {}".format(x, cost))

        if np.isnan(cost):
            return INF

        # Calculate total annualized cost
        return cost

    def calculate_costs(self, verbose=False):
        # Usually total annualized cost
        cost = 0

        for cf in self.cost_funcs:
            # Implemented for columns
            if cf["op"] == "columns":
                for col in self.columns:
                    if not col.op.ColumnFlowsheet.CfsConverged:
                        print("Costs cannot be calculated for a column which has not converged!")
                        return -1
                    unit_cost = cf["fn"](col)
                    cost += unit_cost

                    if verbose:
                        print("Operation {} incurs cost of {}".format(col.op.name, unit_cost))
            if cf["op"] == "heatexchangers":
                for hx in self.exchangers:
                    unit_cost = cf["fn"](hx)
                    cost += unit_cost
                    if verbose:
                        print("Operation {} incurs cost of {}".format(hx.name, unit_cost))
        
        return cost

    def set_column_efficiency(self, col_name, efficiency):
        if efficiency <= 0 or efficiency > 1:
            raise ValueError("Invalid efficiency value provided!")
        for c in self.columns:
            if c.op.name.lower() == col_name.lower():
                self.efficiency_specs.append([c, efficiency])
                print("Added column efficiency specification.")
                return

    def set_to_optimal(self):
        self.objective_function(self.optimal_params)

    def show_individual_costs(self):
        print("Total cost is", self.calculate_costs(verbose=True))

    def get_current_params(self):
        '''
        Returns a list of the current parameters, EXCEPT FEED LOCATION!!
        '''
        params = []
        for p in self.params:
            if p["unit"] == "feed_location":
                stream_idx = p["interface"].ColumnFeeds.index(p["stream_name"])
                stgs = _parse_feed_stages(p["interface"].ColumnFlowsheet.Operations.Item(0).FeedStages.Names)
                total_trays = p["interface"].ColumnFlowsheet.Operations(0).NumberOfTrays
                params.append(stgs[stream_idx] / total_trays)
            else:
                params.append(p["interface"].ImportedVariable.GetValue(p["unit"]))
        
        return params
        
        
        


# Helper private static functions that will not be exposed for use
def _extract_cell_name(cell):
    # Validation and name info extraction
    varname = cell.VariableName

    # If no attached variable, invalid input or ended search
    if varname == "":
        return False

    return cell.AttachedObjectName + ": " + varname


def _get_cell_ref(row, col):
    '''
    Converts row and column index to Excel spreadsheet cell index (E.g. row 2 col 1 becomes "A2")
    Index starts from 1.

    Args:
        row: Cell row
        col: Cell column

    Returns:
        String corresponding to the cell index reference.
    '''

    if col > 26:
        raise NotImplementedError("Referencing columns beyond Z has not been implemented yet!")
    return chr(ord('A') + col - 1) + str(row)


# Default column pressure drop equation
def _default_column_pressure_drop(p_cond, n_trays, dp_cond, dp_reb):
    '''
    Uses a 0.1psi pressure drop (or 0.69 kPa) per tray.
    Pressure drops of condenser and reboiler will follow their existing values in the case file.
    '''
    return p_cond + dp_cond + dp_reb + (n_trays * 0.689476)


# For parsing the feed stage numbers
def _parse_feed_stages(feed_stage_names):
    '''
    Feed stage comes in e.g. "10__Main Tower"
    '''
    return [int(stg.split("__")[0]) for stg in feed_stage_names]

