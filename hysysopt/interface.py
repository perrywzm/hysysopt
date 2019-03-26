'''
Handles initial connection to HYSYS COM interface and high level actions
such as identifying operations present in the case file.
'''

import os
import win32com.client as win32
from .optimizer import HysysOptimizer
from .distcol import Column


def init(filename=None):
    '''
    Entry point of the Hysys Optimizer. Instantiates a HysysOptimizer object connected to the Hysys COM interface
    of the case file provided (or active document).

    Streams and operations are automatically acquired and can be accessed from HysysOptimizer.operations, .m_streams
    for material streams, or .e_streams for energy streams.

    Args:
        filename: path to the hysys file to connect to (e.g. C:\\hysys\\example.hsc). If input is blank, it will try to
        connect to the active document instead.

    Returns:
        HysysOptimizer object
    '''

    case = connect_hysys(filename)
    ops = identify_ops(case)
    m_streams, e_streams = identify_streams(case)

    optimizer = HysysOptimizer(case, ops, m_streams, e_streams)

    optimizer.columns = identify_columns(ops)
    optimizer.exchangers = identify_exchangers(ops)

    return optimizer


def connect_hysys(filename):
    '''
    Establishes connection with the Hysys COM interface and outputs a HysysOptimizer object.

    Args:
        filename: path to the hysys file to connect to

    Returns:
        Hysys case COM object
    '''

    # Establish connection to Hysys app COM interface
    print('=' * 45)
    print('CONNECTING TO THE HYSYS APPLICATION ...')
    hy_app = win32.gencache.EnsureDispatch('HYSYS.Application')

    if hy_app is None:
        raise FileNotFoundError("HYSYS application was not detected!")

    hy_app.Visible = True

    # Open Hysys Case File
    if filename is not None:
        if os.path.exists(filename):
            print("Opening simulation case file...")
            hy_case = hy_app.SimulationCases.Open(filename)
        else:
            raise FileNotFoundError("File does not exist! Provided filename: " + filename)
    else:
        print("No filename was supplied. Opening active document...")
        hy_case = hy_app.ActiveDocument

    # Ensure Hysys case file can be opened
    hy_case.Visible = True
    hy_title = hy_case.Title.Value
    print('... Hysys case file identified as', hy_title)

    # 06 Aspen Hysys Fluid Package Name
    # package_name = hy_case.Flowsheet.FluidPackage.PropertyPackageName
    # print('... Hysys fluid package identified as', package_name)
    print('Connection Established!')

    return hy_case


def identify_ops(hy_case, verbose=False):
    if verbose: print("Identifying operations present in Hysys file...")

    op_interface = hy_case.Flowsheet.Operations
    ops = [op_interface.Item(i) for i in range(len(op_interface))]

    if verbose:
        print("Identified {} operations:".format(len(ops))) 
        print([o.name for o in ops])
    return ops


def identify_streams(hy_case, verbose=False):
    if verbose: print("Identifying material streams present in Hysys file...")
    ms_interface = hy_case.Flowsheet.MaterialStreams
    m_streams = [ms_interface.Item(i) for i in range(len(ms_interface))]

    if verbose:
        print("Identified {} material streams:".format(len(m_streams)))
        print([ms.name for ms in m_streams])
        print('=' * 45)

    if verbose: print("Identifying energy streams present in Hysys file...")
    es_interface = hy_case.Flowsheet.EnergyStreams
    e_streams = [es_interface.Item(i) for i in range(len(es_interface))]

    if verbose:
        print("Identified {} material streams:".format(len(e_streams)))
        print([es.name for es in e_streams])
        print('=' * 45)

    return m_streams, e_streams


def identify_columns(ops):
    columns = []
    for o in ops:
        if o.TypeName == "distillation":
            columns.append(Column(o))
    if len(columns) > 0:
        print("{} distillation columns were identified!".format(len(columns)))
        print("WARNING: Ensure that the names of the feed streams/product streams of the column are " +
            "the same as those within the column subflowsheet!")
    return columns


def identify_exchangers(ops):
    exchangers = []
    for o in ops:
        if o.TypeName == "heaterop" or o.TypeName == "coolerop":
            exchangers.append(o)
    return exchangers
