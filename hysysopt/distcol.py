class Column:
    def __init__(self, column_op):
        # Collect ColumnOp interface
        self.op = column_op

        # Expose main tower interface
        self.tower = column_op.ColumnFlowsheet.Operations(0)

        # Expose condenser interface
        self.condenser = column_op.ColumnFlowsheet.Operations(1)

        # Expose reboiler interface
        self.reboiler = column_op.ColumnFlowsheet.Operations(2)

    def get_condenser_temps(self, unit="C"):
        '''
        Returns tuple of inlet_temp, outlet_temp.
        Ensure that the column flowsheet reflux stream (condenser outlet) is named 'To Condenser'.
        '''
        return (self.condenser.AttachedFeeds.Item('To Condenser').Temperature.GetValue(unit),
                self.condenser.VesselTemperature.GetValue(unit))

    def get_reboiler_temps(self,unit="C"):
        '''
        Returns tuple of inlet_temp, outlet_temp.
        Ensure that the column flowsheet boilup stream (reboiler outlet) is named 'To Reboiler'.
        '''
        return (self.reboiler.AttachedFeeds.Item('To Reboiler').Temperature.GetValue(unit),
                self.reboiler.VesselTemperature.GetValue(unit))

    def get_condenser_duty(self, unit="kW"):
        return self.condenser.EnergyStream.HeatFlow.GetValue(unit)

    def get_reboiler_duty(self, unit="kW"):
        return self.reboiler.EnergyStream.HeatFlow.GetValue(unit)
    
    def get_column_diameter(self, unit="m"):
        return self.tower.ColumnDiameter.GetValue(unit)

    def get_num_trays(self):
        return self.tower.NumberOfTrays

    def get_feed_stages(self):
        feed_stages = self.op.ColumnFeeds



