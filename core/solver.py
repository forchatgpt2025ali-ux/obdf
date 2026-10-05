import numpy as np
from typing import Dict, List
from core.pvt_thermo import FluidProperties, PVTThermoEngine
from core.hydraulics import WellboreHydraulics

class SimulatorCoordinator:
    def __init__(self, is_obm: bool = True):
        self.is_obm = is_obm
        self.fluid = FluidProperties()
        self.pvt = PVTThermoEngine(self.fluid)
        self.hydraulics = WellboreHydraulics(self.pvt, depth_m=4000.0, n_nodes=200)
        
        self.T_profile = self.hydraulics.get_temperature_profile()
        self.gas_bubble_idx = self.hydraulics.n_nodes - 1
        self.kick_mass_kg = 500.0
        self.P_choke = 1.0 * 1e6 

    def calculate_wellbore_state(self) -> Dict:
        P_prof = np.zeros(self.hydraulics.n_nodes)
        alpha_prof = np.zeros(self.hydraulics.n_nodes)
        Rs_prof = np.zeros(self.hydraulics.n_nodes)
        P_prof[0] = self.P_choke
        
        for i in range(self.hydraulics.n_nodes - 1):
            local_gas_mass = self.kick_mass_kg if i == self.gas_bubble_idx else 0.0
            dp_dz, alpha, rs = self.hydraulics.calc_pressure_gradient(
                P_prof[i], self.T_profile[i], local_gas_mass, self.is_obm
            )
            P_prof[i+1] = P_prof[i] + dp_dz * self.hydraulics.dz
            alpha_prof[i] = alpha
            Rs_prof[i] = rs
            
        return {
            "depth": self.hydraulics.z_grid,
            "pressure_MPa": P_prof / 1e6,
            "alpha": alpha_prof,
            "Rs": Rs_prof,
            "BHP_MPa": P_prof[-1] / 1e6,
            "pit_gain_m3": np.sum(alpha_prof * self.hydraulics.Area_ann * self.hydraulics.dz)
        }