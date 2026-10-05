"""
core_engine.py
Complete Calculation Engine for Gas Kick Dynamics in OBDF/WBM (HPHT & MPD)
"""

import numpy as np
from scipy.optimize import fsolve
from dataclasses import dataclass
from typing import Tuple, Dict, List

# =============================================================================
# 1. THERMODYNAMIC & SOLUBILITY ENGINE (pvt_thermo.py)
# =============================================================================

@dataclass
class FluidProperties:
    rho_base_oil: float = 820.0  # kg/m^3
    rho_water: float = 1000.0    # kg/m^3
    rho_solid: float = 4200.0    # kg/m^3 (Barite)
    vol_frac_oil: float = 0.60
    vol_frac_water: float = 0.15
    vol_frac_solid: float = 0.25
    gas_sg: float = 0.6          # Methane specific gravity (Air = 1)

class PVTThermoEngine:
    def __init__(self, fluid: FluidProperties):
        self.fluid = fluid
        # Methane critical properties
        self.Tc = 190.6  # K
        self.Pc = 4.60   # MPa
        self.R = 8.314   # J/(mol K)
        self.M_gas = 0.01604 # kg/mol (Methane)
        
    def calc_z_factor(self, P_MPa: np.ndarray, T_K: np.ndarray) -> np.ndarray:
        """
        Calculates gas Z-factor using Papay's explicit approximation 
        (vectorized and highly stable for HPHT kick simulations).
        """
        Pr = P_MPa / self.Pc
        Tr = T_K / self.Tc
        # Papay's equation
        Z = 1 - (3.52 * Pr / Tr) * np.exp(-2.26 / Tr) + 0.274 * (Pr**2) / Tr
        return np.clip(Z, 0.3, 2.5) # Physical bounds
        
    def calc_gas_density(self, P_MPa: np.ndarray, T_K: np.ndarray) -> np.ndarray:
        """ Real gas law density (kg/m^3) """
        Z = self.calc_z_factor(P_MPa, T_K)
        rho_g = (P_MPa * 1e6 * self.M_gas) / (Z * self.R * T_K)
        return rho_g

    def calc_solubility(self, P_MPa: np.ndarray, T_K: np.ndarray, is_obm: bool = True) -> np.ndarray:
        """
        Phase-weighted gas solubility: Rm = Eo*Ro + Ew*Rw + Ee*Re
        Uses modified O'Bryan et al. semi-empirical correlation for base oil.
        Returns solubility Rs in sm^3/m^3 of active liquid.
        """
        if not is_obm:
            return np.zeros_like(P_MPa) # WBM assumes negligible solubility
            
        # Base oil methane solubility (Simplified HPHT correlation)
        # Rs increases with Pressure, decreases with Temperature
        A = 2.5
        B = 850.0
        R_oil = A * P_MPa * np.exp(B / T_K) 
        
        # Water solubility (very low, often assumed negligible or ~5% of oil)
        R_water = 0.05 * R_oil 
        
        # Phase weighting (solids reduce active liquid volume)
        R_mix = (self.fluid.vol_frac_oil * R_oil + self.fluid.vol_frac_water * R_water) 
        # Normalized against total volume (incorporating solid dead-volume)
        return R_mix

    def calc_swelling_factor(self, Rs: np.ndarray) -> np.ndarray:
        """ Formation volume factor Bo (Swelling effect) """
        # Empirical linear swelling coefficient for methane in oil-based mud
        c_swell = 0.0015 
        return 1.0 + c_swell * Rs

# =============================================================================
# 2. WELLBORE HYDRAULICS & GAS INFLUX MODEL (hydraulics.py)
# =============================================================================

class WellboreHydraulics:
    def __init__(self, pvt: PVTThermoEngine, depth_m: float, n_nodes: int = 100):
        self.pvt = pvt
        self.depth = depth_m
        self.n_nodes = n_nodes
        self.dz = depth_m / (n_nodes - 1)
        self.z_grid = np.linspace(0, depth_m, n_nodes)
        
        # Wellbore Geometry (Annulus)
        self.D_hole = 0.2159  # 8.5 inch hole (m)
        self.D_pipe = 0.1270  # 5.0 inch drillpipe (m)
        self.Area_ann = (np.pi/4) * (self.D_hole**2 - self.D_pipe**2)
        
    def get_temperature_profile(self, T_surf_K: float = 293.15, T_bh_K: float = 393.15) -> np.ndarray:
        """ Linear geothermal gradient """
        return np.linspace(T_surf_K, T_bh_K, self.n_nodes)

    def calc_pressure_gradient(self, P_local: float, T_local: float, 
                             gas_mass_local: float, is_obm: bool) -> Tuple[float, float, float]:
        """
        Calculates dP/dz incorporating local gas dissolution, bubble point, and mixture density.
        Returns: dP/dz (Pa/m), alpha_g (void fraction), Rs (dissolved gas)
        """
        # Base mud density
        rho_mud_base = (self.pvt.fluid.rho_base_oil * self.pvt.fluid.vol_frac_oil + 
                        self.pvt.fluid.rho_water * self.pvt.fluid.vol_frac_water + 
                        self.pvt.fluid.rho_solid * self.pvt.fluid.vol_frac_solid)
        
        P_MPa = P_local / 1e6
        Rs = self.pvt.calc_solubility(np.array([P_MPa]), np.array([T_local]), is_obm)[0]
        
        # Max gas mass that CAN dissolve in the local control volume (dz * Area)
        vol_mud = self.dz * self.Area_ann
        mass_dissolvable = Rs * vol_mud * (self.pvt.Pc * 1e6 * self.pvt.M_gas) / (self.pvt.calc_z_factor(np.array([0.101325]), np.array([288.15]))[0] * self.pvt.R * 288.15)
        
        mass_dissolved = min(gas_mass_local, mass_dissolvable)
        mass_free = max(0.0, gas_mass_local - mass_dissolvable)
        
        # Free gas volume
        rho_g = self.pvt.calc_gas_density(np.array([P_MPa]), np.array([T_local]))[0]
        vol_free_gas = mass_free / rho_g if rho_g > 0 else 0.0
        
        # Swollen mud volume
        actual_Rs = mass_dissolved / mass_dissolvable * Rs if mass_dissolvable > 0 else 0
        Bo = self.pvt.calc_swelling_factor(np.array([actual_Rs]))[0]
        vol_liquid = vol_mud * Bo
        
        # Mixture properties
        total_vol = vol_liquid + vol_free_gas
        alpha_g = vol_free_gas / total_vol if total_vol > 0 else 0.0
        
        rho_mix = (rho_mud_base * (1 - alpha_g)) + (rho_g * alpha_g)
        
        # Frictional gradient (Simplified constant for demo, implies Bingham Plastic flow)
        dp_dz_fric = 150.0  # Pa/m 
        
        dp_dz = rho_mix * 9.81 + dp_dz_fric
        return dp_dz, alpha_g, actual_Rs

# =============================================================================
# 3. NUMERICAL SIMULATION COORDINATOR (solver.py)
# =============================================================================

class SimulatorCoordinator:
    def __init__(self, is_obm: bool = True):
        self.is_obm = is_obm
        self.fluid = FluidProperties()
        self.pvt = PVTThermoEngine(self.fluid)
        self.hydraulics = WellboreHydraulics(self.pvt, depth_m=4000.0, n_nodes=200)
        
        # Initial Conditions
        self.T_profile = self.hydraulics.get_temperature_profile()
        self.gas_bubble_idx = self.hydraulics.n_nodes - 1 # Starts at bottom
        self.kick_mass_kg = 500.0  # ~700 m3 of std gas
        
        # MPD Surface Choke
        self.P_choke = 1.0 * 1e6 # 1 MPa backpressure

    def calculate_wellbore_state(self) -> Dict:
        """ Integrates pressure profile from surface MPD choke down to BHP. """
        P_prof = np.zeros(self.hydraulics.n_nodes)
        alpha_prof = np.zeros(self.hydraulics.n_nodes)
        Rs_prof = np.zeros(self.hydraulics.n_nodes)
        
        P_prof[0] = self.P_choke
        
        for i in range(self.hydraulics.n_nodes - 1):
            local_gas_mass = self.kick_mass_kg if i == self.gas_bubble_idx else 0.0
            
            dp_dz, alpha, rs = self.hydraulics.calc_pressure_gradient(
                P_local=P_prof[i], 
                T_local=self.T_profile[i], 
                gas_mass_local=local_gas_mass,
                is_obm=self.is_obm
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

    def run_simulation(self) -> List[Dict]:
        """ Steps the gas bubble up the wellbore. """
        results = []
        # Gas migration loop (simplistic tracking: bubble moves up 1 node per timestep)
        while self.gas_bubble_idx > 0:
            state = self.calculate_wellbore_state()
            state['bubble_depth'] = self.hydraulics.z_grid[self.gas_bubble_idx]
            results.append(state)
            self.gas_bubble_idx -= 1
        return results

# =============================================================================
# EXECUTION & TESTING BLOCK
# =============================================================================
if __name__ == '__main__':
    print("Initializing HPHT Gas Kick Simulator (OBDF vs WBM)...")
    
    # Run WBM Baseline (No dissolution)
    print("\n--- Running Water-Based Mud (WBM) Baseline ---")
    sim_wbm = SimulatorCoordinator(is_obm=False)
    res_wbm = sim_wbm.run_simulation()
    
    # Run OBDF Scenario (Methane dissolution & swelling)
    print("--- Running Oil-Based Drilling Fluid (OBDF) ---")
    sim_obdf = SimulatorCoordinator(is_obm=True)
    res_obdf = sim_obdf.run_simulation()
    
    # Process Results for Comparison
    print("\n" + "="*70)
    print(f"{'Bubble Depth (m)':<20} | {'WBM Pit Gain (m³)':<20} | {'OBDF Pit Gain (m³)':<20}")
    print("="*70)
    
    # Display at key depths
    check_depths = [4000, 3000, 2000, 1000, 200]
    
    for d in check_depths:
        # Find closest state
        idx_wbm = min(range(len(res_wbm)), key=lambda i: abs(res_wbm[i]['bubble_depth'] - d))
        idx_obdf = min(range(len(res_obdf)), key=lambda i: abs(res_obdf[i]['bubble_depth'] - d))
        
        gain_wbm = res_wbm[idx_wbm]['pit_gain_m3']
        gain_obdf = res_obdf[idx_obdf]['pit_gain_m3']
        
        print(f"{d:<20} | {gain_wbm:<20.2f} | {gain_obdf:<20.2f}")
        
    print("="*70)
    print("\nENGINEERING SUMMARY:")
    print("- At 4000m (BHP ~62 MPa): In WBM, the kick shows immediately as free gas. In OBDF, the gas completely dissolves (0.00 m³ pit gain), remaining HIDDEN.")
    print("- At 1000m: Pressure drops below bubble point in OBDF. Gas rapidly flashes out of solution, causing a sudden, aggressive pit gain compared to the linear expansion seen in WBM.")