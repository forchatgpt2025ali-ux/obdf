"""
gui/main_window.py
Native PySide6 Desktop GUI for Wellbore Gas Influx & Solubility Simulator.
Fully integrated with Matplotlib, QThread, and Data IO.
"""

import sys
import random
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QLabel, QDoubleSpinBox, QComboBox, QPushButton,
    QProgressBar, QGroupBox, QLineEdit, QFileDialog, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Slot, Signal


from gui.plot_canvas import ResultsPlotCanvas
from gui.worker import SimulationWorker
from utils.data_io import ValidationEngine

# =============================================================================
# QSS THEME DEFINITION
# =============================================================================
DARK_THEME = """
QMainWindow { background-color: #1e1e2e; color: #cdd6f4; }
QWidget { font-family: 'Segoe UI', Helvetica, sans-serif; font-size: 10pt; color: #cdd6f4; }
QTabWidget::pane { border: 1px solid #313244; background-color: #252836; border-radius: 6px; }
QTabBar::tab { background-color: #181825; border: 1px solid #313244; padding: 8px 20px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: bold; }
QTabBar::tab:selected { background-color: #3b82f6; color: #ffffff; border-color: #3b82f6; }
QTabBar::tab:hover:!selected { background-color: #313244; }
QPushButton { background-color: #3b82f6; border: none; padding: 8px 16px; border-radius: 4px; color: white; font-weight: bold; }
QPushButton:hover { background-color: #2563eb; }
QPushButton:pressed { background-color: #1d4ed8; }
QPushButton:disabled { background-color: #45475a; color: #a6adc8; }
QPushButton#btn_run { background-color: #10b981; }
QPushButton#btn_run:hover { background-color: #059669; }
QPushButton#btn_reset { background-color: #ef4444; }
QPushButton#btn_reset:hover { background-color: #dc2626; }

QDoubleSpinBox, QComboBox, QLineEdit { background-color: #11111b; border: 1px solid #313244; padding: 5px; border-radius: 4px; color: #cdd6f4; min-width: 100px; }
QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus { border: 1px solid #00d2ff; }
QGroupBox { border: 1px solid #313244; border-radius: 6px; margin-top: 1.5ex; padding: 15px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #00d2ff; font-weight: bold; }
QProgressBar { border: 1px solid #313244; border-radius: 4px; text-align: center; background-color: #11111b; font-weight: bold; color: white; }
QProgressBar::chunk { background-color: #00d2ff; width: 20px; }
QStatusBar { background-color: #11111b; color: #a6adc8; border-top: 1px solid #313244; }
"""

# =============================================================================
# MAIN WINDOW CLASS
# =============================================================================
class SimulatorMainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OBDF Gas Kick Dynamics Simulator v1.0")
        self.resize(1280, 850)
        self.setStyleSheet(DARK_THEME)

        self.worker = None

        # Central Widget & Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Tab Widget
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Initialize Tabs
        self.init_tab_fluid()
        self.init_tab_wellbore()
        self.init_tab_simulation()
        self.init_tab_validation()

        # Status Bar Setup
        self.init_status_bar()

    # -------------------------------------------------------------------------
    # TAB 1: FLUID & PVT PROPERTIES
    # -------------------------------------------------------------------------
    def init_tab_fluid(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group_base = QGroupBox("Drilling Fluid Composition")
        form_base = QFormLayout(group_base)
        
        self.cb_oil_type = QComboBox()
        self.cb_oil_type.addItems(["Mineral Oil (Escaid 110)", "Linear Paraffin", "Synthetic Olefin", "Diesel"])
        
        self.sb_owr = QDoubleSpinBox(); self.sb_owr.setRange(50.0, 100.0); self.sb_owr.setValue(80.0); self.sb_owr.setSuffix(" / 20 (Oil/Water)")
        self.sb_solid_frac = QDoubleSpinBox(); self.sb_solid_frac.setRange(0.0, 50.0); self.sb_solid_frac.setValue(25.0); self.sb_solid_frac.setSuffix(" wt%")
        
        form_base.addRow("Base Oil Type:", self.cb_oil_type)
        form_base.addRow("Oil-Water Ratio (OWR):", self.sb_owr)
        form_base.addRow("Barite Solids Fraction:", self.sb_solid_frac)
        layout.addWidget(group_base)

        group_gas = QGroupBox("Influx Gas Composition (Mole %)")
        form_gas = QFormLayout(group_gas)
        
        self.sb_ch4 = QDoubleSpinBox(); self.sb_ch4.setRange(0, 100); self.sb_ch4.setValue(85.0); self.sb_ch4.setSuffix(" %")
        self.sb_c2h6 = QDoubleSpinBox(); self.sb_c2h6.setRange(0, 100); self.sb_c2h6.setValue(10.0); self.sb_c2h6.setSuffix(" %")
        self.sb_co2 = QDoubleSpinBox(); self.sb_co2.setRange(0, 100); self.sb_co2.setValue(5.0); self.sb_co2.setSuffix(" %")
        
        form_gas.addRow("Methane (CH4):", self.sb_ch4)
        form_gas.addRow("Ethane (C2H6):", self.sb_c2h6)
        form_gas.addRow("Carbon Dioxide (CO2):", self.sb_co2)
        
        layout.addWidget(group_gas)
        layout.addStretch()
        self.tabs.addTab(tab, "Fluid & PVT Properties")

    # -------------------------------------------------------------------------
    # TAB 2: WELLBORE & MPD OPERATIONS
    # -------------------------------------------------------------------------
    def init_tab_wellbore(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group_geo = QGroupBox("Wellbore Geometry & Thermal")
        form_geo = QFormLayout(group_geo)
        
        self.sb_depth = QDoubleSpinBox(); self.sb_depth.setRange(1000, 10000); self.sb_depth.setValue(4000.0); self.sb_depth.setSuffix(" m")
        self.sb_hole_d = QDoubleSpinBox(); self.sb_hole_d.setRange(4, 26); self.sb_hole_d.setValue(8.5); self.sb_hole_d.setSuffix(" in")
        self.sb_pipe_d = QDoubleSpinBox(); self.sb_pipe_d.setRange(2, 6.625); self.sb_pipe_d.setValue(5.0); self.sb_pipe_d.setSuffix(" in")
        self.sb_grad = QDoubleSpinBox(); self.sb_grad.setRange(1.0, 5.0); self.sb_grad.setValue(3.0); self.sb_grad.setSuffix(" °C/100m")
        
        form_geo.addRow("Total Depth (TVD):", self.sb_depth)
        form_geo.addRow("Open Hole / Casing ID:", self.sb_hole_d)
        form_geo.addRow("Drillpipe OD:", self.sb_pipe_d)
        form_geo.addRow("Geothermal Gradient:", self.sb_grad)
        layout.addWidget(group_geo)

        group_ops = QGroupBox("MPD Operations & Influx Parameters")
        form_ops = QFormLayout(group_ops)
        
        self.sb_influx = QDoubleSpinBox(); self.sb_influx.setRange(0.1, 50.0); self.sb_influx.setValue(2.0); self.sb_influx.setSuffix(" m³")
        self.sb_form_p = QDoubleSpinBox(); self.sb_form_p.setRange(10, 150); self.sb_form_p.setValue(65.0); self.sb_form_p.setSuffix(" MPa")
        self.sb_flow = QDoubleSpinBox(); self.sb_flow.setRange(100, 3000); self.sb_flow.setValue(1200.0); self.sb_flow.setSuffix(" L/min")
        self.sb_mpd_choke = QDoubleSpinBox(); self.sb_mpd_choke.setRange(0, 20); self.sb_mpd_choke.setValue(1.5); self.sb_mpd_choke.setSuffix(" MPa")
        
        form_ops.addRow("Initial Gas Influx Volume:", self.sb_influx)
        form_ops.addRow("Formation Pore Pressure:", self.sb_form_p)
        form_ops.addRow("Mud Pump Rate:", self.sb_flow)
        form_ops.addRow("MPD Surface Backpressure:", self.sb_mpd_choke)
        layout.addWidget(group_ops)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Wellbore & MPD Ops")

    # -------------------------------------------------------------------------
    # TAB 3: DYNAMIC SIMULATION & CONTROLS
    # -------------------------------------------------------------------------
    def init_tab_simulation(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        toolbar = QHBoxLayout()
        self.btn_run = QPushButton("▶ Run Simulation")
        self.btn_run.setObjectName("btn_run")
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_reset = QPushButton("⏹ Reset")
        self.btn_reset.setObjectName("btn_reset")
        
        toolbar.addWidget(self.btn_run)
        toolbar.addWidget(self.btn_pause)
        toolbar.addWidget(self.btn_reset)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("Simulation Progress: %p%")
        layout.addWidget(self.progress)

        self.plot_container = QGroupBox("Real-Time Wellbore Profiles (Pressure, Void Fraction, Solubility)")
        plot_layout = QVBoxLayout(self.plot_container)
        
        
        self.plot_canvas = ResultsPlotCanvas(self.plot_container)
        plot_layout.addWidget(self.plot_canvas)
        
        layout.addWidget(self.plot_container)
        self.tabs.addTab(tab, "Dynamic Simulation")
        
        self.btn_run.clicked.connect(self.on_run_clicked)
        self.btn_pause.clicked.connect(self.on_pause_clicked)
        self.btn_reset.clicked.connect(self.on_reset_clicked)

    # -------------------------------------------------------------------------
    # TAB 4: EXPERIMENTAL VALIDATION & EXPORT
    # -------------------------------------------------------------------------
    def init_tab_validation(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group_data = QGroupBox("Load Experimental PVT Data")
        vbox = QVBoxLayout(group_data)
        
        hbox = QHBoxLayout()
        self.txt_filepath = QLineEdit()
        self.txt_filepath.setPlaceholderText("Select CSV dataset (e.g., Sun et al. solubility data)...")
        self.txt_filepath.setReadOnly(True)
        btn_browse = QPushButton("Browse CSV...")
        btn_browse.clicked.connect(self.browse_file)
        
        hbox.addWidget(self.txt_filepath)
        hbox.addWidget(btn_browse)
        vbox.addLayout(hbox)
        layout.addWidget(group_data)

        
        self.lbl_metrics = QLabel("Validation Metrics: Load data and run simulation to compute.")
        self.lbl_metrics.setStyleSheet("color: #f9e2af; font-weight: bold; font-size: 11pt; margin-top: 10px;")
        layout.addWidget(self.lbl_metrics)

      
        self.btn_export = QPushButton("💾 Export Report to Excel")
        self.btn_export.setStyleSheet("background-color: #a6e3a1; color: #11111b; margin-top: 20px;")
        self.btn_export.clicked.connect(self.export_results)
        layout.addWidget(self.btn_export)

        layout.addStretch()
        self.tabs.addTab(tab, "Validation & Report")

    # -------------------------------------------------------------------------
    # STATUS BAR & UTILS
    # -------------------------------------------------------------------------
    def init_status_bar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_engine = QLabel("Engine: IDLE")
        self.lbl_memory = QLabel("RAM: 45 MB")
        
        self.lbl_engine.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        self.lbl_memory.setStyleSheet("color: #f9e2af;")
        
        self.statusbar.addWidget(self.lbl_status, 1)
        self.statusbar.addPermanentWidget(self.lbl_engine)
        self.statusbar.addPermanentWidget(QLabel(" | "))
        self.statusbar.addPermanentWidget(self.lbl_memory)
        
        self.mem_timer = QTimer(self)
        self.mem_timer.timeout.connect(self.update_memory_mock)
        self.mem_timer.start(2000)

    @Slot()
    def update_memory_mock(self):
        mock_mem = 45.0 + random.uniform(-0.5, 1.2)
        self.lbl_memory.setText(f"RAM: {mock_mem:.1f} MB")

    # -------------------------------------------------------------------------
    # SIGNAL HANDLERS & LOGIC
    # -------------------------------------------------------------------------
    @Slot()
    def on_run_clicked(self):
        if self.worker is not None and self.worker.isRunning():
            return
            
        self.lbl_status.setText("Simulation Running...")
        self.lbl_engine.setText("Engine: CALCULATING")
        self.lbl_engine.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self.progress.setValue(0)
        
        config = {
            "depth": self.sb_depth.value(),
            "owr": self.sb_owr.value(),
            "influx_m3": self.sb_influx.value(),
            "mpd_pressure": self.sb_mpd_choke.value()
        }
        
        self.worker = SimulationWorker(config)
        self.worker.progress_updated.connect(self.progress.setValue)
        self.worker.step_computed.connect(self.on_step_computed)
        self.worker.simulation_finished.connect(self.on_simulation_finished)
        self.worker.error_occurred.connect(self.on_simulation_error)
        
        self.btn_run.setEnabled(False)
        self.worker.start()

    @Slot(dict)
    def on_step_computed(self, data: dict):
        self.lbl_status.setText(
            f"Bubble Depth: {data['depth']:.1f}m | "
            f"BHP: {data['bhp_obdf']:.2f} MPa | "
            f"Pit Gain: {data['gain_obdf']:.2f} m³"
        )

    @Slot()
    def on_pause_clicked(self):
        if self.worker:
            self.worker.pause()
            if self.worker._is_paused:
                self.btn_pause.setText("▶ Resume")
                self.lbl_engine.setText("Engine: PAUSED")
                self.lbl_engine.setStyleSheet("color: #f9e2af; font-weight: bold;")
            else:
                self.btn_pause.setText("⏸ Pause")
                self.lbl_engine.setText("Engine: CALCULATING")
                self.lbl_engine.setStyleSheet("color: #f38ba8; font-weight: bold;")

    @Slot()
    def on_reset_clicked(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            
        self.progress.setValue(0)
        self.lbl_status.setText("Ready")
        self.lbl_engine.setText("Engine: IDLE")
        self.lbl_engine.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        self.btn_run.setEnabled(True)
        self.btn_pause.setText("⏸ Pause")

    @Slot(list, list)
    def on_simulation_finished(self, wbm_results: list, obdf_results: list):
        self.lbl_status.setText("Simulation Complete.")
        self.lbl_engine.setText("Engine: IDLE")
        self.lbl_engine.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        self.btn_run.setEnabled(True)
        
        
        self.last_wbm_results = wbm_results
        self.last_obdf_results = obdf_results

       
        self.plot_canvas.update_plots(wbm_results, obdf_results)
        
       
        if hasattr(self, 'exp_df'):
            self.run_validation()

    @Slot(str)
    def on_simulation_error(self, err: str):
        QMessageBox.critical(self, "Engine Error", f"Simulation failed:\n{err}")
        self.on_reset_clicked()

    @Slot()
    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Experimental Data", "", "CSV Files (*.csv)")
        if file_name:
            self.txt_filepath.setText(file_name)
            try:
                self.exp_df = ValidationEngine.load_experimental_data(file_name)
                self.lbl_status.setText(f"Loaded {len(self.exp_df)} rows from {file_name}")
                if hasattr(self, 'last_obdf_results'):
                    self.run_validation()
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))

    def run_validation(self):
        try:
            sim_bhp = np.array([d['BHP_MPa'] for d in self.last_obdf_results])
            exp_bhp = self.exp_df['BHP_MPa'].values 
            
            self.last_metrics = ValidationEngine.calculate_metrics(sim_bhp, exp_bhp)
            self.lbl_metrics.setText(
                f"Model Fit: R² = {self.last_metrics['R2']:.3f} | RMSE = {self.last_metrics['RMSE']:.2f} MPa | MAE = {self.last_metrics['MAE']:.2f} MPa"
            )
            
           
            self.plot_canvas.ax1.scatter(range(len(exp_bhp)), exp_bhp, color='#f9e2af', marker='x', label='Exp Data')
            self.plot_canvas.ax1.legend(facecolor='#181825', edgecolor='#313244', labelcolor='#cdd6f4')
            self.plot_canvas.canvas.draw()
        except KeyError:
            QMessageBox.warning(self, "Validation Error", "CSV file must contain a 'BHP_MPa' column for validation.")

    @Slot()
    def export_results(self):
        if not hasattr(self, 'last_obdf_results'):
            QMessageBox.warning(self, "Warning", "Run a simulation first before exporting!")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Report", "Simulation_Report.xlsx", "Excel (*.xlsx)")
        if save_path:
            ValidationEngine.export_to_excel(
                save_path, 
                self.last_wbm_results, 
                self.last_obdf_results, 
                plot_figure=self.plot_canvas.fig,
                metrics=getattr(self, 'last_metrics', None)
            )
            self.lbl_status.setText(f"Report successfully saved to {save_path}")

# =============================================================================
# EXECUTION
# =============================================================================
if __name__ == "__main__":
    app = QApplication(sys.eventDispatcher())
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    window = SimulatorMainWindow()
    window.show()
    sys.exit(app.exec())