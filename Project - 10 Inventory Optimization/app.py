"""
Walmart Enterprise - AI Inventory Optimization Web Server & REST API
Project - 10: Inventory Optimization

Serves:
- Executive Glassmorphic Inventory Intelligence Dashboard
- Multi-Echelon SKU Inventory Directory & Stochastic ROP Explorer
- SKU Deep-Dive Diagnostics & 30-Day Predictive Demand Forecaster
- Autonomous Prescriptive Operations Protocol Dispatcher
- Real-Time What-If Scenario Stress Simulator
- One-Click Executive PDF Report Download
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template, jsonify, request, send_file

# Add project root to path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

os.environ["LOKY_MAX_CPU_COUNT"] = "4"

from data.data_generator import generate_walmart_inventory_dataset
from models.demand_forecaster import DemandForecaster
from models.inventory_optimizer import InventoryOptimizer
from models.prescriptive_engine import PrescriptiveEngine
from models.simulation_engine import SimulationEngine
from report.generate_pdf_report import build_pdf_report

app = Flask(__name__, static_folder="static", template_folder="templates")

DATA_DIR = os.path.join(base_dir, "data")
CSV_PATH = os.path.join(DATA_DIR, "walmart_inventory_data.csv")
SUPP_CSV_PATH = os.path.join(DATA_DIR, "walmart_suppliers_directory.csv")
REPORT_PATH = os.path.join(base_dir, "report", "Walmart_Inventory_Optimization_Executive_Report.pdf")
MODELS_DIR = os.path.join(base_dir, "models")

# Step 1: Ensure dataset exists
if not os.path.exists(CSV_PATH) or not os.path.exists(SUPP_CSV_PATH):
    print("[Flask-Init] Synthesizing 16,000 Walmart inventory records...")
    generate_walmart_inventory_dataset(num_records=16000, output_dir=DATA_DIR)

# Step 2: Initialize models
print("[Flask-Init] Loading demand forecaster and stochastic optimizer...")
forecaster = DemandForecaster(models_dir=MODELS_DIR)
forecaster.train_or_load(CSV_PATH)

optimizer = InventoryOptimizer(models_dir=MODELS_DIR)
optimizer.analyze_dataset(CSV_PATH)

prescriptive_engine = PrescriptiveEngine()
simulation_engine = SimulationEngine(optimizer, prescriptive_engine)

# Step 3: Ensure PDF Report exists
if not os.path.exists(REPORT_PATH):
    print("[Flask-Init] Compiling publication-grade executive PDF report...")
    build_pdf_report(optimizer, forecaster, simulation_engine, prescriptive_engine, REPORT_PATH)

@app.route("/")
def index():
    """Serves the main interactive dashboard."""
    return render_template("index.html")

@app.route("/api/summary", methods=["GET"])
def api_summary():
    """Returns high-level KPI totals and segmentations."""
    return jsonify(optimizer.summary_stats)

@app.route("/api/skus", methods=["GET"])
def api_skus():
    """Returns the full master catalog of SKUs with stochastic inventory metrics."""
    if optimizer.sku_master_table is None:
        return jsonify([])
    # Convert dataframe to records
    records = optimizer.sku_master_table.to_dict(orient="records")
    return jsonify(records)

@app.route("/api/sku_detail/<sku_id>", methods=["GET"])
def api_sku_detail(sku_id):
    """Returns deep-dive diagnostics, 30-day forward demand forecast, and recommendations."""
    sku_row = optimizer.get_sku_details(sku_id)
    if not sku_row:
        return jsonify({"error": f"SKU {sku_id} not found"}), 404

    # 30-day forecast
    forecast = forecaster.forecast_sku_demand(sku_row, horizon_days=30, promo_boost=False)

    # Autonomous protocol recommendations
    recommendations = prescriptive_engine.generate_recommendations(sku_row)

    return jsonify({
        "sku": sku_row,
        "forecast": forecast,
        "recommendations": recommendations
    })

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Executes What-If scenario simulations with custom user parameters."""
    req = request.get_json() or {}
    demand_mult = float(req.get("demand_multiplier", 1.0))
    delay_days = float(req.get("lead_time_delay_days", 0.0))
    service_lvl = float(req.get("service_level", 0.95))
    markdown_pct = float(req.get("markdown_discount_pct", 0.20))

    sim_result = simulation_engine.run_scenario(
        demand_multiplier=demand_mult,
        lead_time_delay_days=delay_days,
        service_level=service_lvl,
        markdown_discount_pct=markdown_pct
    )
    return jsonify(sim_result)

@app.route("/api/suppliers", methods=["GET"])
def api_suppliers():
    """Returns the directory of 20 suppliers and their reliability metrics."""
    if os.path.exists(SUPP_CSV_PATH):
        df_supp = pd.read_csv(SUPP_CSV_PATH)
        return jsonify(df_supp.to_dict(orient="records"))
    return jsonify([])

@app.route("/download_report", methods=["GET"])
def download_report():
    """Downloads the publication-grade 8-page PDF executive report."""
    if not os.path.exists(REPORT_PATH):
        build_pdf_report(optimizer, forecaster, simulation_engine, prescriptive_engine, REPORT_PATH)
    return send_file(
        REPORT_PATH,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="Walmart_Inventory_Optimization_Executive_Report.pdf"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5010))
    print(f" * Walmart AI Inventory Intelligence Platform starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

