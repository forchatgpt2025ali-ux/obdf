import time
from PySide6.QtCore import QThread, Signal
from core.core_engine import SimulatorCoordinator, FluidProperties

class SimulationWorker(QThread):
    # Signals to communicate safely with the main GUI thread
    progress_updated = Signal(int)
    step_computed = Signal(dict)
    simulation_finished = Signal(list, list) # wbm_results, obdf_results
    error_occurred = Signal(str)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self._is_running = True
        self._is_paused = False

    def run(self):
        try:
            # 1. Initialize Engines
            sim_wbm = SimulatorCoordinator(is_obm=False)
            sim_obdf = SimulatorCoordinator(is_obm=True)
            
            # Apply UI Configs
            sim_obdf.P_choke = self.config['mpd_pressure'] * 1e6
            sim_wbm.P_choke = self.config['mpd_pressure'] * 1e6
            sim_obdf.kick_mass_kg = self.config['influx_m3'] * 100 # Approx conversion
            sim_wbm.kick_mass_kg = self.config['influx_m3'] * 100

            total_nodes = sim_obdf.hydraulics.n_nodes
            wbm_results = []
            obdf_results = []

            # 2. Stepping loop (Bubble migrates bottom to top)
            for step in range(total_nodes):
                if not self._is_running:
                    break  # Cancelled

                # Pause execution lock
                while self._is_paused:
                    time.sleep(0.1)
                    if not self._is_running: return

                # Compute step for both fluids
                sim_wbm.gas_bubble_idx = total_nodes - step - 1
                sim_obdf.gas_bubble_idx = total_nodes - step - 1
                
                state_wbm = sim_wbm.calculate_wellbore_state()
                state_obdf = sim_obdf.calculate_wellbore_state()
                
                wbm_results.append(state_wbm)
                obdf_results.append(state_obdf)

                # Emit progress (simulate calculation time for visual effect)
                progress_pct = int((step / total_nodes) * 100)
                self.progress_updated.emit(progress_pct)
                self.step_computed.emit({
                    'depth': sim_obdf.hydraulics.z_grid[sim_obdf.gas_bubble_idx],
                    'bhp_obdf': state_obdf['BHP_MPa'],
                    'gain_obdf': state_obdf['pit_gain_m3']
                })
                
                time.sleep(0.02) # Throttling for UI responsiveness

            if self._is_running:
                self.progress_updated.emit(100)
                self.simulation_finished.emit(wbm_results, obdf_results)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def pause(self):
        self._is_paused = not self._is_paused

    def cancel(self):
        self._is_running = False
        self._is_paused = False # Release lock if paused