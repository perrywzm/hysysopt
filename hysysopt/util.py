

def get_column_vars(hy_case, op):
    '''
    Obtains commonly used variables of a HYSYS distillation column. Only gets the values and cannot be used to alter
    the column.

    List of variables accessed:
        1. top_pressure: Condenser pressure
        2. bot_pressure: Reboiler pressure
        3. n_trays: Number of trays
        4. q_cond: Condenser heat load
        5. t_cond: Condenser temperature
        6. q_reb: Reboiler heat load
        7. t_reb: Reboiler temperature

    Args:
        hy_case: HYSYS case file object obtained from the interface
        op: Column operation object

    Returns:
        Column object with acquired variable values
    '''

    # 1. column pressure

class Column:
    def __init__(self, hy_case, op):
        '''
        Sets up a Column object that enables access to the most common variables of a HYSYS distillation column.

        Args:
            hy_case: HYSYS case file object
            op: Distillation column operation object
        '''
        _get_column_params(hy_case, op)


def _get_column_params(hy_case, op):
    '''
    Currently we will optimize a column by:
        1. Column pressure (i.e. condenser pressure)
        2. Number of trays
        3. Feed location(s)

    Implemented:
        1. Feed streams
        2. Distillate and Bottoms
    '''

    # Get material FEED streams
    feed_streams = []
    energy_streams = []
    i = 0
    while i >= 0:
        try:
            fs = op.ColumnFlowsheet.FeedStreams.Item(i)
            if fs.TypeName == "materialstream":
                feed_streams.append(fs)
            elif fs.TypeName == "energystream":
                energy_streams.append(fs)
            i += 1
        except Exception as e:
            # Terminate search if there are no more streams
            i = -1

    print([e.name for e in energy_streams])
    # Get Bottoms and Distillate streams
    prod_stream_interface = op.AttachedProducts
    bottoms = hy_case.Flowsheet.MaterialStreams(prod_stream_interface(0))
    distillate = hy_case.Flowsheet.MaterialStreams(prod_stream_interface(1))
    prod_streams = [bottoms, distillate]

    # Get Active Specifications
    active_specs = []

    i = 0
    while i >= 0:
        try:
            spec = op.ColumnFlowsheet.ActiveSpecifications(i)
            print(spec.GoalValue)
            active_specs.append(spec)
            i += 1
        except Exception as e:
            # Terminate search if there are no more specs
            i = -1

    # Get number of trays

    return feed_streams, prod_streams, active_specs

