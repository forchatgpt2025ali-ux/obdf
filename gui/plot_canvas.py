import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

class ResultsPlotCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Initialize Figure with dark theme background
        self.fig = Figure(facecolor='#1e1e2e', figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
        # Setup 2x2 Subplots
        self.ax1 = self.fig.add_subplot(221) # BHP vs Time
        self.ax2 = self.fig.add_subplot(222) # Pit Gain vs Time (WBM vs OBDF)
        self.ax3 = self.fig.add_subplot(223) # Depth Profile (P and Alpha)
        self.ax4 = self.fig.add_subplot(224) # Solubility Curve
        
        self.axes = [self.ax1, self.ax2, self.ax3, self.ax4]
        self._apply_dark_theme()
        
    def _apply_dark_theme(self):
        """Applies petroleum-software dark theme to Matplotlib axes"""
        text_color = '#cdd6f4'
        grid_color = '#313244'
        
        for ax in self.axes:
            ax.set_facecolor('#11111b')
            ax.tick_params(colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            ax.title.set_color(text_color)
            ax.spines['bottom'].set_color(grid_color)
            ax.spines['top'].set_color(grid_color)
            ax.spines['right'].set_color(grid_color)
            ax.spines['left'].set_color(grid_color)
            ax.grid(True, color=grid_color, linestyle='--', alpha=0.7)
            
        self.fig.tight_layout()

    def update_plots(self, wbm_data: list, obdf_data: list):
        """Redraws all 4 subplots based on simulation output data"""
        for ax in self.axes:
            ax.clear()
        self._apply_dark_theme()
        
        # Extract Time (simulated via step index) and variables
        time_steps = np.arange(len(wbm_data))
        
        bhp_wbm = [d['BHP_MPa'] for d in wbm_data]
        bhp_obdf = [d['BHP_MPa'] for d in obdf_data]
        gain_wbm = [d['pit_gain_m3'] for d in wbm_data]
        gain_obdf = [d['pit_gain_m3'] for d in obdf_data]
        
        # Plot 1: Transient BHP
        self.ax1.plot(time_steps, bhp_wbm, label='WBM', color='#00d2ff', linestyle='--')
        self.ax1.plot(time_steps, bhp_obdf, label='OBDF', color='#f38ba8', linewidth=2)
        self.ax1.set_title("Bottomhole Pressure Transient")
        self.ax1.set_xlabel("Time Step (Bubble Migration)")
        self.ax1.set_ylabel("BHP (MPa)")
        self.ax1.legend(facecolor='#181825', edgecolor='#313244', labelcolor='#cdd6f4')

        # Plot 2: Pit Gain (The Hidden Kick Effect)
        self.ax2.plot(time_steps, gain_wbm, label='WBM (Linear Expansion)', color='#00d2ff')
        self.ax2.plot(time_steps, gain_obdf, label='OBDF (Flash Liberation)', color='#f38ba8', linewidth=2)
        self.ax2.set_title("Surface Pit Gain (Kick Detection)")
        self.ax2.set_xlabel("Time Step")
        self.ax2.set_ylabel("Pit Gain (m³)")
        self.ax2.legend(facecolor='#181825', edgecolor='#313244', labelcolor='#cdd6f4')

        # Plot 3: Depth Profile (Snapshot at final step)
        final_obdf = obdf_data[-1]
        depths = final_obdf['depth']
        pressure = final_obdf['pressure_MPa']
        alpha_g = final_obdf['alpha']
        
        self.ax3.plot(pressure, depths, color='#a6e3a1', label='Pressure (MPa)')
        self.ax3.set_ylabel("Depth (m)")
        self.ax3.set_xlabel("Pressure (MPa)", color='#a6e3a1')
        self.ax3.invert_yaxis()  # Depth goes down
        
        # Dual axis for Void Fraction
        ax3_twin = self.ax3.twiny()
        ax3_twin.plot(alpha_g, depths, color='#f9e2af', linestyle=':', linewidth=2, label='Void Frac ($\\alpha_g$)')
        ax3_twin.set_xlabel("Gas Void Fraction", color='#f9e2af')
        ax3_twin.tick_params(axis='x', colors='#f9e2af')
        self.ax3.set_title("Final Depth Profile (OBDF)")

        # Plot 4: Solubility Isotherms (Rs vs P)
        # Using theoretical curves from the engine
        P_range = np.linspace(0.1, 70.0, 50)
        self.ax4.plot(P_range, 2.5 * P_range * np.exp(850.0 / 293.15), label='20 °C (Surface)', color='#89b4fa')
        self.ax4.plot(P_range, 2.5 * P_range * np.exp(850.0 / 393.15), label='120 °C (Bottomhole)', color='#f38ba8')
        self.ax4.set_title("Methane Solubility (OBDF Base)")
        self.ax4.set_xlabel("Pressure (MPa)")
        self.ax4.set_ylabel("Rs (sm³/m³)")
        self.ax4.legend(facecolor='#181825', edgecolor='#313244', labelcolor='#cdd6f4')

        self.fig.tight_layout()
        self.canvas.draw()