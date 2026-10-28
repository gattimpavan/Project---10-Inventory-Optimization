"""
Walmart Enterprise - Stochastic Multi-Echelon Inventory Optimizer
Project - 10: Inventory Optimization

Implements rigorous inventory mathematics:
1. Dynamic Safety Stock (Demand & Lead Time Variance Coupling)
2. Dynamic Reorder Point (ROP) & Economic Order Quantity (EOQ)
3. 9-Quadrant ABC-XYZ Pareto & Predictability Matrix Segmentation
4. Dual-Crisis Stockout Risk vs Excess Inventory Diagnostic Engine
5. Financial Working Capital & Holding Cost Quantifier
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm
import pickle

class InventoryOptimizer:
    def __init__(self, models_dir=None):
        self.models_dir = models_dir or os.path.dirname(__file__)
        os.makedirs(self.models_dir, exist_ok=True)
        self.sku_master_table = None
        self.summary_stats = {}

    def compute_safety_stock(self, mean_d, std_d, mean_lt, std_lt, service_level=0.95):
        """
        Calculates dynamic safety stock incorporating both demand and supplier lead-time uncertainty:
        SS = Z * sqrt( (mean_lt * std_d^2) + (mean_d^2 * std_lt^2) )
        """
        z_score = norm.ppf(service_level)
        variance_lead_demand = (mean_lt * (std_d ** 2)) + ((mean_d ** 2) * (std_lt ** 2))
        ss = z_score * np.sqrt(max(0.1, variance_lead_demand))
        return round(float(ss), 1)

    def compute_rop(self, mean_d, mean_lt, safety_stock):
        """
        Calculates dynamic Reorder Point:
        ROP = (mean_d * mean_lt) + Safety Stock
        """
        lead_time_demand = mean_d * mean_lt
        rop = lead_time_demand + safety_stock
        return round(float(rop), 1)

    def compute_eoq(self, annual_demand, ordering_cost, unit_cost, holding_rate):
        """
        Calculates Wilson Economic Order Quantity:
        EOQ = sqrt( (2 * D * S) / H )
        """
        h = max(0.1, unit_cost * holding_rate)
        eoq = np.sqrt((2.0 * annual_demand * ordering_cost) / h)
        return round(float(eoq), 1)

    def analyze_dataset(self, csv_path):
        """
        Ingests the telemetry records and compiles SKU-level and location-level
        stochastic metrics, ABC-XYZ classification, and inventory health states.
        """
        print(f"[InventoryOptimizer] Analyzing telemetry dataset from {csv_path}...")
        df = pd.read_csv(csv_path)

        # Aggregate SKU-level performance across the dataset
        sku_groups = df.groupby(["sku_id", "sku_name", "category", "turnover_tier", "unit_cost", "unit_price", "supplier_name"]).agg(
            mean_demand=("daily_demand", "mean"),
            std_demand=("daily_demand", "std"),
            total_sales_units=("units_sold", "sum"),
            total_lost_sales_units=("lost_sales_units", "sum"),
            mean_on_hand=("on_hand_inventory", "mean"),
            current_on_hand=("on_hand_inventory", "last"),
            current_on_order=("on_order_inventory", "last"),
            mean_lead_time=("supplier_lead_time_days", "mean"),
            std_lead_time=("supplier_lead_time_std", "mean"),
            mean_fill_rate=("supplier_fill_rate", "mean"),
            stockout_days=("stockout_flag", "sum"),
            total_observations=("stockout_flag", "count"),
            gross_margin_pct=("gross_margin_pct", "mean"),
            holding_cost_rate=("category", lambda c: 0.28 if "Apparel" in c.iloc[0] or "Patio" in c.iloc[0] else 0.20)
        ).reset_index()

        sku_groups["std_demand"] = sku_groups["std_demand"].fillna(sku_groups["mean_demand"] * 0.25)
        sku_groups["total_revenue"] = sku_groups["total_sales_units"] * sku_groups["unit_price"]
        sku_groups["total_lost_revenue"] = sku_groups["total_lost_sales_units"] * sku_groups["unit_price"]
        sku_groups["cv_demand"] = sku_groups["std_demand"] / np.maximum(0.1, sku_groups["mean_demand"])

        # 1. ABC Segmentation (Revenue Pareto)
        sku_groups = sku_groups.sort_values(by="total_revenue", ascending=False)
        sku_groups["cum_revenue"] = sku_groups["total_revenue"].cumsum()
        total_rev = sku_groups["total_revenue"].sum()
        sku_groups["cum_rev_pct"] = sku_groups["cum_revenue"] / total_rev

        def assign_abc(pct):
            if pct <= 0.80:
                return "A"
            elif pct <= 0.95:
                return "B"
            else:
                return "C"

        sku_groups["abc_class"] = sku_groups["cum_rev_pct"].apply(assign_abc)

        # 2. XYZ Segmentation (Demand Volatility / CV)
        def assign_xyz(cv):
            if cv <= 0.25:
                return "X"  # Steady, high predictability
            elif cv <= 0.65:
                return "Y"  # Seasonal, moderate volatility
            else:
                return "Z"  # Erratic, lumpy, unpredictable

        sku_groups["xyz_class"] = sku_groups["cv_demand"].apply(assign_xyz)
        sku_groups["abc_xyz_matrix"] = sku_groups["abc_class"] + sku_groups["xyz_class"]

        # Target Service Levels based on ABC classification
        service_levels = {"A": 0.98, "B": 0.95, "C": 0.90}
        sku_groups["target_service_level"] = sku_groups["abc_class"].map(service_levels)

        # Compute Dynamic Safety Stock, ROP, EOQ
        calc_rows = []
        for _, row in sku_groups.iterrows():
            ss = self.compute_safety_stock(
                mean_d=row["mean_demand"],
                std_d=row["std_demand"],
                mean_lt=row["mean_lead_time"],
                std_lt=row["std_lead_time"],
                service_level=row["target_service_level"]
            )
            rop = self.compute_rop(row["mean_demand"], row["mean_lead_time"], ss)
            ann_demand = row["mean_demand"] * 365.0
            eoq = self.compute_eoq(
                annual_demand=ann_demand,
                ordering_cost=85.0,
                unit_cost=row["unit_cost"],
                holding_rate=row["holding_cost_rate"]
            )
            calc_rows.append({"dynamic_safety_stock": ss, "dynamic_rop": rop, "dynamic_eoq": eoq})

        calc_df = pd.DataFrame(calc_rows)
        sku_groups["dynamic_safety_stock"] = calc_df["dynamic_safety_stock"]
        sku_groups["dynamic_rop"] = calc_df["dynamic_rop"]
        sku_groups["dynamic_eoq"] = calc_df["dynamic_eoq"]

        # Days of Supply (DOS) and Inventory Health Classification
        sku_groups["days_of_supply"] = (sku_groups["current_on_hand"] / np.maximum(0.2, sku_groups["mean_demand"])).round(1)

        def classify_inventory_health(row):
            inv = row["current_on_hand"]
            rop = row["dynamic_rop"]
            eoq = row["dynamic_eoq"]
            dos = row["days_of_supply"]

            if inv <= 0.25 * rop or dos < 3.0:
                return "Critical Stockout Risk"
            elif inv <= rop:
                return "Reorder Triggered"
            elif dos > 65.0:
                return "Severe Excess / Dead Stock"
            elif dos > 40.0:
                return "Mild Excess Inventory"
            else:
                return "Optimal Inventory Range"

        sku_groups["inventory_health"] = sku_groups.apply(classify_inventory_health, axis=1)

        # Capital Tied Up & Annual Holding Burn
        sku_groups["capital_tied_up"] = (sku_groups["current_on_hand"] * sku_groups["unit_cost"]).round(2)
        sku_groups["annual_holding_cost"] = (sku_groups["capital_tied_up"] * sku_groups["holding_cost_rate"]).round(2)

        # Potential Excess Value (units above ROP + EOQ)
        max_opt = sku_groups["dynamic_rop"] + (1.2 * sku_groups["dynamic_eoq"])
        sku_groups["excess_units"] = np.maximum(0.0, sku_groups["current_on_hand"] - max_opt).round(1)
        sku_groups["excess_capital_trapped"] = (sku_groups["excess_units"] * sku_groups["unit_cost"]).round(2)

        self.sku_master_table = sku_groups

        # Compile System-Wide KPI Summary
        total_skus = len(sku_groups)
        stockout_count = (sku_groups["inventory_health"].isin(["Critical Stockout Risk", "Reorder Triggered"])).sum()
        excess_count = (sku_groups["inventory_health"].isin(["Severe Excess / Dead Stock", "Mild Excess Inventory"])).sum()
        optimal_count = (sku_groups["inventory_health"] == "Optimal Inventory Range").sum()

        total_working_cap = sku_groups["capital_tied_up"].sum()
        total_trapped_excess = sku_groups["excess_capital_trapped"].sum()
        total_lost_sales_val = sku_groups["total_lost_revenue"].sum()
        total_ann_holding = sku_groups["annual_holding_cost"].sum()
        system_fill_rate = ((sku_groups["total_sales_units"].sum() / (sku_groups["total_sales_units"].sum() + sku_groups["total_lost_sales_units"].sum())) * 100.0)

        self.summary_stats = {
            "total_skus": total_skus,
            "stockout_risk_skus": int(stockout_count),
            "stockout_risk_pct": round(float((stockout_count / total_skus) * 100.0), 1),
            "excess_inventory_skus": int(excess_count),
            "excess_inventory_pct": round(float((excess_count / total_skus) * 100.0), 1),
            "optimal_inventory_skus": int(optimal_count),
            "optimal_inventory_pct": round(float((optimal_count / total_skus) * 100.0), 1),
            "total_working_capital_tied": round(float(total_working_cap), 2),
            "excess_capital_trapped": round(float(total_trapped_excess), 2),
            "total_lost_revenue": round(float(total_lost_sales_val), 2),
            "annual_holding_cost_burn": round(float(total_ann_holding), 2),
            "system_fill_rate_pct": round(float(system_fill_rate), 2),
            "abc_breakdown": sku_groups["abc_class"].value_counts().to_dict(),
            "xyz_breakdown": sku_groups["xyz_class"].value_counts().to_dict(),
            "matrix_breakdown": sku_groups["abc_xyz_matrix"].value_counts().to_dict(),
            "health_breakdown": sku_groups["inventory_health"].value_counts().to_dict(),
        }

        # Save model state
        pkl_path = os.path.join(self.models_dir, "inventory_optimizer_state.pkl")
        with open(pkl_path, "wb") as f:
            pickle.dump({
                "sku_master_table": self.sku_master_table,
                "summary_stats": self.summary_stats
            }, f)

        print(f"[InventoryOptimizer] Analysis complete: {total_skus} SKUs analyzed.")
        print(f"  -> Stockout Prone SKUs : {stockout_count} ({self.summary_stats['stockout_risk_pct']}%)")
        print(f"  -> Excess Prone SKUs   : {excess_count} ({self.summary_stats['excess_inventory_pct']}%)")
        print(f"  -> Trapped Excess Cap  : ${total_trapped_excess:,.2f}")
        print(f"  -> Lost Revenue Risk   : ${total_lost_sales_val:,.2f}")

        return self.summary_stats

    def get_sku_details(self, sku_id):
        """Returns deep-dive inventory metrics and recommendation for a specific SKU."""
        if self.sku_master_table is None:
            return None
        match = self.sku_master_table[self.sku_master_table["sku_id"] == sku_id]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

