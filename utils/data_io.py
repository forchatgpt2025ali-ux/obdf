import numpy as np
import pandas as pd
import os

class ValidationEngine:
    @staticmethod
    def calculate_metrics(y_simulated: np.ndarray, y_experimental: np.ndarray) -> dict:
        """Calculates R², RMSE, and MAE between simulated and experimental data."""
        # Ensure arrays are the same length for direct 1:1 comparison
        min_len = min(len(y_simulated), len(y_experimental))
        y_sim = y_simulated[:min_len]
        y_exp = y_experimental[:min_len]
        
        # Mean Absolute Error (MAE)
        mae = np.mean(np.abs(y_exp - y_sim))
        
        # Root Mean Square Error (RMSE)
        rmse = np.sqrt(np.mean((y_exp - y_sim)**2))
        
        # R-squared (R2)
        ss_res = np.sum((y_exp - y_sim)**2)
        ss_tot = np.sum((y_exp - np.mean(y_exp))**2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        
        return {"R2": r2, "RMSE": rmse, "MAE": mae}

    @staticmethod
    def load_experimental_data(csv_path: str) -> pd.DataFrame:
        """Loads and sanitizes experimental CSV data."""
        try:
            df = pd.read_csv(csv_path)
            # Expected columns: Time, Pressure_MPa, Temp_K, Solubility_Rs, PitGain_m3, BHP_MPa
            df = df.dropna(how='all') # Clean empty rows
            return df
        except Exception as e:
            raise ValueError(f"Failed to load CSV: {str(e)}")

    @staticmethod
    def export_to_excel(save_path: str, wbm_data: list, obdf_data: list, 
                        plot_figure=None, metrics: dict = None):
        """Exports simulation arrays and embeds the Matplotlib plot into an Excel report."""
        df_wbm = pd.DataFrame(wbm_data)
        df_obdf = pd.DataFrame(obdf_data)
        
        # Use xlsxwriter engine to support image insertion
        with pd.ExcelWriter(save_path, engine='xlsxwriter') as writer:
            df_obdf.to_excel(writer, sheet_name='OBDF_Results', index=False)
            df_wbm.to_excel(writer, sheet_name='WBM_Results', index=False)
            
            workbook = writer.book
            
            # --- Metrics Sheet ---
            if metrics:
                worksheet_metrics = workbook.add_worksheet('Validation_Metrics')
                row = 0
                for k, v in metrics.items():
                    worksheet_metrics.write(row, 0, k)
                    worksheet_metrics.write(row, 1, round(v, 4))
                    row += 1
            
            # --- Plot Image Sheet ---
            if plot_figure:
                worksheet_img = workbook.add_worksheet('Simulation_Plots')
                img_path = os.path.join(os.path.dirname(save_path), 'temp_plot.png')
                plot_figure.savefig(img_path, dpi=150, bbox_inches='tight', facecolor='#1e1e2e')
                
                # Insert image and clean up temp file
                worksheet_img.insert_image('B2', img_path)
                
                # We defer deletion of temp file until after writer closes
                writer.custom_image_path = img_path 

        # Cleanup temp plot image
        if hasattr(writer, 'custom_image_path') and os.path.exists(writer.custom_image_path):
            os.remove(writer.custom_image_path)