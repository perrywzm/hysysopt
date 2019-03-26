'''
Costing is NOT part of the optimizer and should be manually researched and set by the user. However, this is used to
introduce the variable acquisition capabilities of the optimizer.
'''

import math
import numpy as np
import os



def eqn_type_k(c1, c2, c3):
    '''
    Generates a function that computes a purchase cost based on the format of 3 constant K-values:
    log(y) = a + b*log(A) + c*log(A)^2
    '''

    return lambda x: np.power(10, c1 + c2 * np.log10(x) + c3 * (np.log10(x)**2))

# # Equipment and Utility Cost Parameters

# CEPCI
CEPCI_Actual = 567.5  # Annual Index 2017
CEPCI_2001 = 397  # Base Annual Index
cost_factor = CEPCI_Actual / CEPCI_2001

# Annualization Factor parameters
interest_rate = 0.07
# payback period
n_years = 3  

# Utility Costs (in $/kWh) from R.Turton 5th Edition Table 8.3
# Converted from $/GJ to $/kWh
util_water_cost = 0.378 / 1e9 * 3600 * 1e3  # [30 C to 40-45 C]
util_refrig_cost = 4.77 / 1e9 * 3600 * 1e3 # [5 C to 15 C]
util_cryo_cost = 8.49 / 1e9 * 3600 * 1e3 # [5 C to 15 C]
util_steam_cost = 4.54 / 1e9 * 3600 * 1e3  # Low Pressure Steam [5 barg, 160 C]
util_hpsteam_cost = 5.66 / 1e9 * 3600 * 1e3 # High Pressure Steam [41 barg, 254 C]
h_year = 8000  # Operating hours per year

# Equip Cost Equations based on (K). See Appendix A - R .Turton
purchase_cost_tray = eqn_type_k(2.9949, 0.4465, 0.3961) # Area m2
purchase_cost_tower = eqn_type_k(3.4974, 0.4485, 0.1074) # Volume m3
purchase_cost_hx = eqn_type_k(4.3247, -0.3030, 0.1634) # Area m2 - Fixed tube heat exchanger
purchase_cost_kettle = eqn_type_k(4.4646, -0.5277, 0.3955) # Kettle Reboiler
tray_factor = eqn_type_k(0.4771, 0.0816, -0.3473)

# Bare module Cost Factor: direct and indirect costs for each unit
fbm_tray = 1  # Table A.6 & Figure A.9 (Trays - sieve trays)
fbm_tower = (2.25 + 1.82 * 1.0)  # Table A.4 & Figure A.8 (Process vessels - vertical (including towers)) 
fbm_hx = (1.63 + 1.66 * 1.3)  # Table A.4 & Figure A.8 (fixed tube sheet)
fbm_kettle = (1.63 + 1.66 * 1.7) # Table A.4 & Figure A.8 (fixed tube sheet)

# Heat exchanger hyperparameters
DTMIN = 10

# Cooler using cooling water or refrigeration
U_cooler = 800  # [W/(m2 K)] 
t_water_in = 30  # Cooling water inlet  [ºC]
t_water_out = 40  # Cooling water outlet  Condenser [ºC]
t_refrig_in = 5
t_refrig_out = 15
t_cryo_in = -20
t_cryo_out = -19

# Heater using steam or HP steam
U_heater = 820  # [W/(m2 K)]
t_steam = 160  # Low Pressure Steam Temperature (R.Turton 4º Ed. Table 8.3)
t_hp_steam = 254  # High Pressure Steam Temperature

# Tower Column
tray_spacing = 0.6096  # [m]   


def column_cost_function(column):
    '''
    Takes in a HYSYS column operation and calculates the total annualized cost (capital + operating cost).

    Args:
        col: Column operation object

    Returns:
        Total annualized cost of the column
    '''

    # Hyperparameters
    tray_effic = 0.7 

    # --- 2 - Import Data from Aspen Hysys Model
    n_trays = np.ceil(column.get_num_trays() / tray_effic)  # Trays efficiency correction

    t_cond_in, t_cond_out = column.get_condenser_temps()
    t_reb_in, t_reb_out = column.get_reboiler_temps()

    q_cond = column.get_condenser_duty()
    q_reb = column.get_reboiler_duty()

    # 03 # Run Aspen Hysys Script "Col_diam_V8.SCP" to update column diameter
    # Problem.HyObject.HyCase.Application.PlayScript(os.path.abspath('Column_Diameter.SCP'))

    column_diameter = column.get_column_diameter()  # [m]

    # 05 # Capital Cost ##########################################################

    # Column dimensions
    column_area = np.pi * column_diameter**2 / 4  # Sieve area [m2]
    column_height = (n_trays) * tray_spacing + 3  # Tower Height [m]
    column_volume = column_area * column_height  # Volume Tower [m3]

    # Bare Module cost
    column_CBM = purchase_cost_tower(column_volume) * fbm_tower * cost_factor

    # Column trays
    tray_CBM = tray_cost_bm(column_area, n_trays)

    # Column Condenser CBM
    if t_cond_out >= t_water_in + DTMIN and t_cond_in >= t_water_out + DTMIN:
        # Cooling water
        lmtd_cond = lmtd(t_cond_in, t_cond_out, t_water_in, t_water_out)
        cond_cooling_cost = q_cond * util_water_cost * h_year
    elif t_cond_out >= t_refrig_in + DTMIN and t_cond_in >= t_refrig_out + DTMIN:
        # Refrigeration
        lmtd_cond = lmtd(t_cond_in, t_cond_out, t_refrig_in, t_refrig_out)
        cond_cooling_cost = q_cond * util_refrig_cost * h_year
    elif t_cond_out >= t_cryo_in + DTMIN and t_cond_in >= t_cryo_out + DTMIN:
        # Colder Refrigeration
        lmtd_cond = lmtd(t_cond_in, t_cond_out, t_cryo_in, t_cryo_out)
        cond_cooling_cost = q_cond * util_cryo_cost * h_year
    else:
        err_str = "None of the utilities provided can cool stream from {} degC to {} degC.".format(t_cond_in, t_cond_out)
        raise ValueError(err_str)
    condenser_CBM = heat_exchanger_cost_bm(q_cond, lmtd_cond, U_cooler)

    # Column Reboiler CBM (assume Thermosiphon reboiler)
    # For a heater, we can use LP steam (160C) or HP Steam (254C)
    if t_reb_out <= 160 - DTMIN:
        lmtd_reb = lmtd(t_reb_in, t_reb_out, t_steam, t_steam)
        reb_heating_cost = q_reb * util_steam_cost * h_year
    elif t_reb_out <= 254 - DTMIN:
        lmtd_reb = lmtd(t_reb_in, t_reb_out, t_hp_steam, t_hp_steam)
        reb_heating_cost = q_reb * util_hpsteam_cost * h_year
    else:
        err_str = "None of the utilities provided can heat stream from {} degC to {} degC.".format(t_reb_in, t_reb_out)
        raise ValueError(err_str)
    reboiler_CBM = heat_exchanger_cost_bm(q_reb, lmtd_reb, U_heater)

    # 06 # Total Annual Cost #####################################################

    # Total Operating Cost
    op_cost = cond_cooling_cost + reb_heating_cost

    # Total Capital Cost
    cap_cost = column_CBM + tray_CBM + condenser_CBM + reboiler_CBM

    print("Operating cost breakdown: Condenser={}, Reboiler={}".format(cond_cooling_cost, reb_heating_cost))
    print("Capital cost breakdown: Column={}, Trays={}, Condenser={}, Reboiler={}".format(column_CBM, tray_CBM, condenser_CBM, reboiler_CBM))
    # # Discounted annualisation factor based on interest rate and payback period
    discount = discount_factor(n_years, interest_rate)

    total_annualized_cost = (op_cost + cap_cost * discount) * 1e-6  # [MM $/yr]

    return total_annualized_cost


def discount_factor(n, i):
    return i * (1 + i) ** n / ((1 + i) ** n - 1)


def tray_cost_bm(column_area, n_trays):
    # Tray factor
    if n_trays < 20:
        Fq = tray_factor(n_trays)
    else:
        Fq = 1
    
    return purchase_cost_tray(column_area) * fbm_tray * Fq * n_trays * cost_factor


def heat_exchanger_cost_bm(q, lmtd, U):
    area = q / (U * lmtd) * 1000

    return purchase_cost_hx(area) * fbm_hx * cost_factor


def lmtd(t1_in, t1_out, t2_in, t2_out, bypass=True):
    # Handles constant temperature by using arithmetic mean instead of log mean
    if t1_in == t1_out or t2_in == t2_out:
        return np.abs(np.mean([t1_in - t2_out, t1_out - t2_in]))

    if bypass:
        return ((t1_in - t2_out) - (t1_out - t2_in)) / np.log((t1_in - t2_out) / (t1_out - t2_in))
    return ((t1_in - t2_out) - (t1_out - t2_in)) / np.log((t1_in - t2_out) / (t1_out - t2_in))


def pressure_factor(diameter, pressure, ca, t_min, max_stress=944):
    # E is weld efficiency
    return (pressure * diameter / (2 * max_stress * 0.9 - 1.2 * pressure) + ca) / t_min


def hx_cost_function(hx_op):
    '''
    Cost functions for heat exchangers. Implemented by interfacing with the COM objects from the optimizer.
    Automatically picks a valid utility based on minimum approach temperature of 10degC.
    '''
    # If no heat load/temp difference is detected, return 0 (no heat exchanger required)
    q = abs(hx_op.Duty.GetValue('kW'))
    if q == 0:
        return 0

    # Automatically detect if cooling or heating is required. A heater with negative heat load becomes a cooler, etc
    t_in = hx_op.AttachedFeeds.Item(0).Temperature.GetValue('C')
    t_out = hx_op.AttachedProducts.Item(0).Temperature.GetValue('C')

    if t_in < t_out:
        # For a heater, we can use LP steam (160C) or HP Steam (254C)
        if t_out <= 160 - DTMIN:
            lmtd_heater = lmtd(t_in, t_out, t_steam, t_steam)
            cap_cost = heat_exchanger_cost_bm(q, lmtd_heater, U_heater)
            op_cost = q * util_steam_cost * h_year
        elif t_out <= 254 - DTMIN:
            lmtd_heater = lmtd(t_in, t_out, t_hp_steam, t_hp_steam)
            cap_cost = heat_exchanger_cost_bm(q, lmtd_heater, U_heater)
            op_cost = q * util_hpsteam_cost * h_year
        else:
            err_str = "None of the utilities provided can heat stream from {} degC to {} degC.".format(t_in, t_out)
            raise ValueError(err_str)
    else:
        # Cooler can either use cooling water (30C-40C) or refrigeration (5C-15C)
        if t_out >= t_water_in + DTMIN and t_in >= t_water_out + DTMIN:
            # Cooling water
            lmtd_cooler = lmtd(t_in, t_out, t_water_in, t_water_out)
            cap_cost = heat_exchanger_cost_bm(q, lmtd_cooler, U_cooler)
            op_cost = q * util_water_cost * h_year
        elif t_out >= t_refrig_in + DTMIN and t_in >= t_refrig_out + DTMIN:
            # Refrigeration
            lmtd_cooler = lmtd(t_in, t_out, t_refrig_in, t_refrig_out)
            cap_cost = heat_exchanger_cost_bm(q, lmtd_cooler, U_cooler)
            op_cost = q * util_refrig_cost * h_year
        elif t_out >= t_cryo_in + DTMIN and t_in >= t_cryo_out + DTMIN:
            # Cryogenic Refrigeration
            lmtd_cooler = lmtd(t_in, t_out, t_cryo_in, t_cryo_out)
            cap_cost = heat_exchanger_cost_bm(q, lmtd_cooler, U_cooler)
            op_cost = q * util_cryo_cost * h_year
        else:
            err_str = "None of the utilities provided can cool stream from {} degC to {} degC.".format(t_in, t_out)
            raise ValueError(err_str)

    # Discounted annualisation factor based on interest rate and payback period
    discount = discount_factor(n_years, interest_rate)

    total_annualized_cost = (op_cost + cap_cost * discount) * 1e-6
    return total_annualized_cost


















