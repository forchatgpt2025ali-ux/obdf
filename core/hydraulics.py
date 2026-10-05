import numpy as np
from typing import Tuple
from core.pvt_thermo import PVTThermoEngine

class WellboreHydraulics:
    def __init__(self, pvt: PVTThermoEngine, depth_m: float, n_nodes: int = 100):
        self.pvt = pvt
        self.depth = depth_m
        self.n_nodes = n_nodes
        self.dz = depth_m / (n_nodes - 1)
        self.z_grid = np.linspace(0, depth_m, n_nodes)
        
        self.D_hole = 0.2159  # 8.5 in
        self.D_pipe = 0.1270  # 5.0 in
        self.Area_ann = (np.pi/4) * (self.D_hole**2 - self.D_pipe**2)
        
    def get_temperature_profile(self, T_surf_K: float = 293.15, T_bh_K: float = 393.15) -> np.ndarray:
        return np.linspace(T_surf_K, T_bh_K, self.n_nodes)

    def calc_pressure_gradient(self, P_local: float, T_local: float, 
                             gas_mass_local: float, is_obm: bool) -> Tuple[float, float, float]:
        
        f = self.pvt.fluid
        rho_mud_base = (f.rho_base_oil * f.vol_frac_oil + f.rho_water * f.vol_frac_water + f.rho_solid * f.vol_frac_solid)
        
        P_MPa = P_local / 1e6
        Rs = self.pvt.calc_solubility(np.array([P_MPa]), np.array([T_local]), is_obm)[0]
        
        vol_mud = self.dz * self.Area_ann
        mass_dissolvable = Rs * vol_mud * (self.pvt.Pc * 1e6 * self.pvt.M_gas) / (self.pvt.calc_z_factor(np.array([0.101325]), np.array([288.15]))[0] * self.pvt.R * 288.15)
        
        mass_dissolved = min(gas_mass_local, mass_dissolvable)
        mass_free = max(0.0, gas_mass_local - mass_dissolvable)
        
        rho_g = self.pvt.calc_gas_density(np.array([P_MPa]), np.array([T_local]))[0]
        vol_free_gas = mass_free / rho_g if rho_g > 0 else 0.0
        
        actual_Rs = mass_dissolved / mass_dissolvable * Rs if mass_dissolvable > 0 else 0
        Bo = self.pvt.calc_swelling_factor(np.array([actual_Rs]))[0]
        
        total_vol = (vol_mud * Bo) + vol_free_gas
        alpha_g = vol_free_gas / total_vol if total_vol > 0 else 0.0
        
        rho_mix = (rho_mud_base * (1 - alpha_g)) + (rho_g * alpha_g)
        dp_dz_fric = 150.0  # Friction assumption
        
        return (rho_mix * 9.81 + dp_dz_fric), alpha_g, actual_Rs