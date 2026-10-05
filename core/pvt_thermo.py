import numpy as np
from dataclasses import dataclass

@dataclass
class FluidProperties:
    rho_base_oil: float = 820.0
    rho_water: float = 1000.0
    rho_solid: float = 4200.0
    vol_frac_oil: float = 0.60
    vol_frac_water: float = 0.15
    vol_frac_solid: float = 0.25
    gas_sg: float = 0.6

class PVTThermoEngine:
    def __init__(self, fluid: FluidProperties):
        self.fluid = fluid
        self.Tc = 190.6  # K (Methane)
        self.Pc = 4.60   # MPa
        self.R = 8.314
        self.M_gas = 0.01604
        
    def calc_z_factor(self, P_MPa: np.ndarray, T_K: np.ndarray) -> np.ndarray:
        Pr = P_MPa / self.Pc
        Tr = T_K / self.Tc
        Z = 1 - (3.52 * Pr / Tr) * np.exp(-2.26 / Tr) + 0.274 * (Pr**2) / Tr
        return np.clip(Z, 0.3, 2.5)
        
    def calc_gas_density(self, P_MPa: np.ndarray, T_K: np.ndarray) -> np.ndarray:
        Z = self.calc_z_factor(P_MPa, T_K)
        return (P_MPa * 1e6 * self.M_gas) / (Z * self.R * T_K)

    def calc_solubility(self, P_MPa: np.ndarray, T_K: np.ndarray, is_obm: bool = True) -> np.ndarray:
        if not is_obm: return np.zeros_like(P_MPa)
        R_oil = 2.5 * P_MPa * np.exp(850.0 / T_K) 
        R_water = 0.05 * R_oil 
        return (self.fluid.vol_frac_oil * R_oil + self.fluid.vol_frac_water * R_water)

    def calc_swelling_factor(self, Rs: np.ndarray) -> np.ndarray:
        return 1.0 + 0.0015 * Rs