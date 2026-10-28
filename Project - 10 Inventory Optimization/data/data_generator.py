"""
Walmart Enterprise - Realistic Retail Inventory Dataset Synthesizer
Project - 10: Inventory Optimization

Synthesizes high-fidelity, empirically grounded retail inventory observations across
Walmart Supercenters and Regional Distribution Centers. Ingests multi-echelon dynamics:
- Fast-moving high-velocity SKUs vs Slow-moving seasonal/erratic SKUs
- Dual-crisis phenomena: Stockout events & Excess inventory holding accumulation
- Seasonal demand surges, promotion lifts, and supplier lead-time uncertainties
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Fix random seed for reproducibility
np.random.seed(42)

CATEGORIES = {
    "Grocery & Fresh Essentials": {
        "skus": [
            ("WM-GROC-101", "Great Value Whole Milk 1 Gallon", 2.20, 3.48, 85, 12, 3, 0.8, 0.22),
            ("WM-GROC-102", "Kellogg's Frosted Flakes Cereal 24oz", 3.10, 4.98, 48, 9, 5, 1.2, 0.20),
            ("WM-GROC-103", "Great Value Large White Eggs 18ct", 2.40, 3.82, 95, 15, 2, 0.6, 0.24),
            ("WM-GROC-104", "Tyson Fresh Boneless Chicken Breast 3lb", 7.50, 11.88, 62, 14, 3, 0.9, 0.25),
            ("WM-GROC-105", "Wonder Classic White Bread 20oz", 1.25, 2.18, 70, 11, 2, 0.5, 0.22),
            ("WM-GROC-106", "Great Value Peanut Butter Creamy 40oz", 2.80, 4.42, 35, 6, 7, 1.5, 0.18),
            ("WM-GROC-107", "Coca-Cola Original Soda 12pk Cans", 4.60, 7.28, 110, 22, 4, 1.1, 0.20),
            ("WM-GROC-108", "Chobani Greek Yogurt Variety 4pk", 2.90, 4.74, 52, 10, 4, 1.0, 0.25),
        ],
        "turnover_tier": "Fast",
        "holding_rate": 0.22,
        "stockout_penalty_mult": 1.4,
    },
    "Consumer Electronics": {
        "skus": [
            ("WM-ELEC-201", "onn. 50-Inch 4K UHD LED Roku Smart TV", 165.00, 248.00, 16, 6, 12, 3.2, 0.18),
            ("WM-ELEC-202", "Apple AirPods Pro (2nd Generation)", 175.00, 239.00, 24, 8, 14, 3.8, 0.15),
            ("WM-ELEC-203", "Sony PlayStation 5 Slim Digital Console", 360.00, 449.00, 14, 7, 18, 5.0, 0.16),
            ("WM-ELEC-204", "Samsung 65-Inch Crystal UHD 4K Smart TV", 340.00, 498.00, 10, 4, 16, 4.2, 0.18),
            ("WM-ELEC-205", "onn. True Wireless Bluetooth Earbuds", 11.50, 19.88, 42, 12, 10, 2.5, 0.20),
            ("WM-ELEC-206", "Anker Power Bank 20000mAh Portable Charger", 28.00, 45.99, 28, 7, 12, 2.8, 0.18),
            ("WM-ELEC-207", "HP 15.6-Inch Core i3 Laptop 8GB/256GB", 280.00, 399.00, 8, 3, 21, 5.5, 0.18),
        ],
        "turnover_tier": "Medium-High",
        "holding_rate": 0.18,
        "stockout_penalty_mult": 1.6,
    },
    "Health & Personal Care": {
        "skus": [
            ("WM-HLTH-301", "Equate Extra Strength Acetaminophen 500ct", 4.10, 7.98, 58, 10, 6, 1.4, 0.18),
            ("WM-HLTH-302", "Colgate Total Whitening Toothpaste 4pk", 5.80, 9.96, 44, 8, 5, 1.1, 0.18),
            ("WM-HLTH-303", "Dove Deep Moisture Body Wash 34oz", 6.20, 10.47, 40, 7, 7, 1.6, 0.19),
            ("WM-HLTH-304", "Pampers Baby Dry Diapers Size 4 128ct", 24.50, 37.94, 36, 9, 8, 2.0, 0.22),
            ("WM-HLTH-305", "Crest 3D Whitestrips Professional 20pk", 28.00, 44.97, 18, 5, 9, 2.2, 0.18),
            ("WM-HLTH-306", "Neutrogena Hydro Boost Water Gel 1.7oz", 12.40, 19.97, 22, 6, 8, 2.1, 0.19),
        ],
        "turnover_tier": "Medium",
        "holding_rate": 0.18,
        "stockout_penalty_mult": 1.5,
    },
    "Home & Kitchen Essentials": {
        "skus": [
            ("WM-HOME-401", "Bounty Quick-Size Paper Towels 12 Family", 18.20, 27.98, 65, 14, 5, 1.2, 0.20),
            ("WM-HOME-402", "Mainstays 8-Piece Nonstick Cookware Set", 22.00, 39.97, 12, 4, 15, 3.5, 0.22),
            ("WM-HOME-403", "Ninja Professional Plus Blender 1400W", 65.00, 99.00, 9, 3, 16, 4.0, 0.20),
            ("WM-HOME-404", "Mainstays 5-Tier Wire Storage Shelf", 28.50, 49.88, 7, 2.5, 18, 4.5, 0.25),
            ("WM-HOME-405", "Keurig K-Express Single Serve Coffee Maker", 42.00, 69.00, 15, 5, 12, 3.0, 0.20),
            ("WM-HOME-406", "Brita Standard Water Filter Pitcher 6-Cup", 14.20, 22.98, 20, 5, 8, 2.0, 0.20),
        ],
        "turnover_tier": "Medium",
        "holding_rate": 0.22,
        "stockout_penalty_mult": 1.3,
    },
    "Apparel & Seasonal Fashion": {
        "skus": [
            ("WM-APPR-501", "George Men's Regular Fit Jeans Medium Wash", 9.80, 16.98, 18, 6, 20, 5.2, 0.26),
            ("WM-APPR-502", "Time and Tru Women's Crewneck T-Shirt 3pk", 7.20, 13.44, 25, 8, 18, 4.8, 0.25),
            ("WM-APPR-503", "Athletic Works Men's Fleece Pullover Hoodie", 8.90, 15.98, 14, 5, 22, 5.8, 0.28),
            ("WM-APPR-504", "Wonder Nation Girls' Denim Shortalls Niche", 6.50, 14.88, 4, 2.2, 25, 7.0, 0.30),
            ("WM-APPR-505", "George Men's Classic Oxford Dress Shoes", 18.50, 34.98, 5, 2.0, 28, 8.0, 0.30),
            ("WM-APPR-506", "Time and Tru High-Rise Jeggings Coral Rose", 7.80, 16.87, 3, 1.8, 26, 7.5, 0.32),
        ],
        "turnover_tier": "Slow-Fashion",
        "holding_rate": 0.28,
        "stockout_penalty_mult": 1.1,
    },
    "Toys & Holiday Entertainment": {
        "skus": [
            ("WM-TOYS-601", "LEGO Classic Large Creative Brick Box 10698", 34.00, 49.99, 22, 9, 14, 3.5, 0.22),
            ("WM-TOYS-602", "Barbie Dreamhouse 75+ Pieces Playset", 115.00, 179.00, 6, 3.5, 24, 6.2, 0.25),
            ("WM-TOYS-603", "Hot Wheels 20-Car Gift Pack Variety", 14.50, 22.97, 32, 10, 10, 2.5, 0.20),
            ("WM-TOYS-604", "Hasbro Monopoly Classic Board Game", 11.20, 19.82, 18, 6, 12, 3.0, 0.22),
            ("WM-TOYS-605", "Nerf Elite 2.0 Commander RD-6 Blaster", 8.90, 14.99, 15, 5, 15, 3.8, 0.24),
            ("WM-TOYS-606", "Fisher-Price Laugh & Learn Smart Stages", 12.80, 21.99, 12, 4, 16, 4.0, 0.23),
        ],
        "turnover_tier": "Seasonal-Heavy",
        "holding_rate": 0.25,
        "stockout_penalty_mult": 1.25,
    },
    "Automotive & Hardware": {
        "skus": [
            ("WM-AUTO-701", "Mobil 1 Advanced Full Synthetic Motor Oil 5qt", 19.80, 29.97, 38, 8, 9, 2.1, 0.18),
            ("WM-AUTO-702", "EverStart Maxx Lead Acid Car Battery Group 24", 78.00, 119.84, 11, 3.5, 16, 4.5, 0.22),
            ("WM-AUTO-703", "Slime Tire Sealant Emergency Inflator 16oz", 5.20, 8.97, 16, 4, 14, 3.2, 0.19),
            ("WM-AUTO-704", "Hyper Tough 20V Max Cordless Drill Driver", 19.50, 34.88, 14, 4.5, 18, 4.8, 0.20),
            ("WM-AUTO-705", "Rain-X All-Season Windshield Wiper Blade 22in", 7.40, 12.97, 28, 7, 8, 1.9, 0.18),
        ],
        "turnover_tier": "Medium-Slow",
        "holding_rate": 0.20,
        "stockout_penalty_mult": 1.35,
    },
    "Patio & Garden Essentials": {
        "skus": [
            ("WM-PATI-801", "Kingsford Original Charcoal Briquettes 2x20lb", 14.80, 21.98, 45, 14, 7, 1.8, 0.22),
            ("WM-PATI-802", "Miracle-Gro All Purpose Potting Mix 25qt", 6.80, 10.97, 34, 11, 8, 2.0, 0.24),
            ("WM-PATI-803", "Mainstays Albany 3-Piece Outdoor Bistro Set", 85.00, 148.00, 4, 1.8, 28, 7.5, 0.30),
            ("WM-PATI-804", "Expert Grill 3-Burner Propane Gas Grill", 68.00, 107.00, 6, 2.5, 22, 6.0, 0.28),
            ("WM-PATI-805", "Roundup Dual Action Weed & Grass Killer 1Gal", 13.50, 21.48, 22, 7, 10, 2.4, 0.20),
        ],
        "turnover_tier": "Highly-Seasonal",
        "holding_rate": 0.26,
        "stockout_penalty_mult": 1.2,
    }
}

LOCATIONS = [
    {"id": "SC-1001", "name": "Walmart Supercenter #1001 - Bentonville, AR", "type": "Supercenter", "region": "South-Central", "demand_multiplier": 1.25},
    {"id": "SC-2045", "name": "Walmart Supercenter #2045 - Dallas/Ft Worth, TX", "type": "Supercenter", "region": "South", "demand_multiplier": 1.45},
    {"id": "SC-3180", "name": "Walmart Supercenter #3180 - Atlanta, GA", "type": "Supercenter", "region": "Southeast", "demand_multiplier": 1.30},
    {"id": "SC-4422", "name": "Walmart Supercenter #4422 - Chicago/Naperville, IL", "type": "Supercenter", "region": "Midwest", "demand_multiplier": 1.20},
    {"id": "SC-5510", "name": "Walmart Supercenter #5510 - Phoenix Metro, AZ", "type": "Supercenter", "region": "Southwest", "demand_multiplier": 1.15},
    {"id": "SC-6630", "name": "Walmart Supercenter #6630 - Orlando/Kissimmee, FL", "type": "Supercenter", "region": "Southeast", "demand_multiplier": 1.35},
    {"id": "DC-6021", "name": "Regional DC #6021 - Fort Worth Logistics Hub", "type": "Distribution Center", "region": "South", "demand_multiplier": 3.80},
    {"id": "DC-7014", "name": "Regional DC #7014 - Grove City Fulfillment Hub", "type": "Distribution Center", "region": "Midwest", "demand_multiplier": 3.40},
    {"id": "DC-8055", "name": "Regional DC #8055 - Greencastle Distribution Hub", "type": "Distribution Center", "region": "Northeast", "demand_multiplier": 3.20},
    {"id": "DC-9012", "name": "Regional DC #9012 - Colton Western Super-Hub", "type": "Distribution Center", "region": "West", "demand_multiplier": 4.10},
]

SUPPLIERS = [
    {"id": "SUP-101", "name": "Procter & Gamble Direct Supply", "lead_time_mean": 5.2, "lead_time_std": 1.1, "fill_rate": 0.98, "reliability_score": 98.2, "region": "Domestic"},
    {"id": "SUP-102", "name": "Unilever Global Consumer Logistics", "lead_time_mean": 6.0, "lead_time_std": 1.3, "fill_rate": 0.97, "reliability_score": 96.5, "region": "Domestic"},
    {"id": "SUP-103", "name": "Kraft Heinz Foodservice Distribution", "lead_time_mean": 4.5, "lead_time_std": 0.9, "fill_rate": 0.985, "reliability_score": 98.8, "region": "Domestic"},
    {"id": "SUP-104", "name": "Coca-Cola Consolidated Bottling", "lead_time_mean": 3.2, "lead_time_std": 0.7, "fill_rate": 0.992, "reliability_score": 99.4, "region": "Local DSD"},
    {"id": "SUP-105", "name": "Tyson Foods Fresh Poultry Group", "lead_time_mean": 2.8, "lead_time_std": 0.5, "fill_rate": 0.988, "reliability_score": 99.1, "region": "Cold Chain"},
    {"id": "SUP-106", "name": "Apple Logistics Americas (Americas Hub)", "lead_time_mean": 14.5, "lead_time_std": 3.8, "fill_rate": 0.92, "reliability_score": 91.5, "region": "Global/Air"},
    {"id": "SUP-107", "name": "Samsung Electronics North America", "lead_time_mean": 16.0, "lead_time_std": 4.2, "fill_rate": 0.91, "reliability_score": 89.8, "region": "Pacific Import"},
    {"id": "SUP-108", "name": "Sony Interactive Entertainment Supply", "lead_time_mean": 18.2, "lead_time_std": 5.1, "fill_rate": 0.88, "reliability_score": 86.4, "region": "Pacific Import"},
    {"id": "SUP-109", "name": "onn. Electronics OEM Contracting (Shenzhen)", "lead_time_mean": 24.0, "lead_time_std": 6.5, "fill_rate": 0.84, "reliability_score": 82.0, "region": "Trans-Pacific Ocean"},
    {"id": "SUP-110", "name": "Anker Innovations Global Supply", "lead_time_mean": 12.0, "lead_time_std": 2.8, "fill_rate": 0.94, "reliability_score": 93.2, "region": "Global"},
    {"id": "SUP-111", "name": "Colgate-Palmolive Distribution", "lead_time_mean": 5.0, "lead_time_std": 1.0, "fill_rate": 0.98, "reliability_score": 97.8, "region": "Domestic"},
    {"id": "SUP-112", "name": "LEGO Americas Distribution Center", "lead_time_mean": 14.0, "lead_time_std": 3.4, "fill_rate": 0.93, "reliability_score": 92.5, "region": "Mexico Overland"},
    {"id": "SUP-113", "name": "Mattel Toy Logistics", "lead_time_mean": 21.0, "lead_time_std": 5.8, "fill_rate": 0.86, "reliability_score": 84.7, "region": "Pacific Ocean"},
    {"id": "SUP-114", "name": "Mobil 1 Lubricants (ExxonMobil Supply)", "lead_time_mean": 8.5, "lead_time_std": 1.9, "fill_rate": 0.96, "reliability_score": 95.8, "region": "Domestic Rail/Tanker"},
    {"id": "SUP-115", "name": "Great Value Private Label Food Group", "lead_time_mean": 4.0, "lead_time_std": 0.8, "fill_rate": 0.99, "reliability_score": 99.2, "region": "Dedicated DC Network"},
    {"id": "SUP-116", "name": "George / Time and Tru Textile Mills (Vietnam)", "lead_time_mean": 27.5, "lead_time_std": 7.2, "fill_rate": 0.79, "reliability_score": 76.5, "region": "Asia-Pacific Marine"},
    {"id": "SUP-117", "name": "Kingsford BBQ & Grilling Distribution", "lead_time_mean": 7.0, "lead_time_std": 1.6, "fill_rate": 0.965, "reliability_score": 96.0, "region": "Domestic Bulk"},
    {"id": "SUP-118", "name": "East Penn Manufacturing (EverStart Batteries)", "lead_time_mean": 15.5, "lead_time_std": 4.1, "fill_rate": 0.90, "reliability_score": 88.5, "region": "Domestic Heavy Freight"},
    {"id": "SUP-119", "name": "Keurig Dr Pepper Commercial Systems", "lead_time_mean": 11.5, "lead_time_std": 2.7, "fill_rate": 0.95, "reliability_score": 94.0, "region": "Domestic Truckload"},
    {"id": "SUP-120", "name": "Mainstays Overseas Home Goods Consortium", "lead_time_mean": 28.0, "lead_time_std": 7.8, "fill_rate": 0.77, "reliability_score": 74.2, "region": "East Asia Container"},
]

def generate_walmart_inventory_dataset(num_records=16000, output_dir=None):
    """
    Synthesizes a rich, multi-layered retail inventory dataset capturing:
    1. Fast-moving high demand grocery/essentials that suffer stockouts when lead times slip.
    2. Slow-moving apparel/seasonal items that accumulate excess holding costs and dead stock.
    3. Realistic promotional surges, day-of-week shopping cycles, holiday seasonality.
    4. Lead-time delays and supplier reliability variance.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__))
    os.makedirs(output_dir, exist_ok=True)

    print(f"[Synthesizer] Generating {num_records:,} Walmart inventory observation records...")

    # Flatten SKU catalogue
    sku_catalog = []
    for cat_name, cat_data in CATEGORIES.items():
        for sku_tuple in cat_data["skus"]:
            sku_id, sku_name, cost, price, base_d, base_std, supp_lt, supp_lt_std, holding_rate = sku_tuple
            # Map to an appropriate supplier
            matching_suppliers = [s for s in SUPPLIERS if (cat_name.split()[0] in s["name"] or "Global" in s["name"] or "Direct" in s["name"])]
            if not matching_suppliers:
                supp = SUPPLIERS[np.random.randint(len(SUPPLIERS))]
            else:
                supp = matching_suppliers[np.random.randint(len(matching_suppliers))]

            sku_catalog.append({
                "sku_id": sku_id,
                "sku_name": sku_name,
                "category": cat_name,
                "turnover_tier": cat_data["turnover_tier"],
                "unit_cost": cost,
                "unit_price": price,
                "base_daily_demand": base_d,
                "demand_std": base_std,
                "holding_cost_rate": holding_rate,
                "stockout_penalty_mult": cat_data["stockout_penalty_mult"],
                "supplier_id": supp["id"],
                "supplier_name": supp["name"],
                "supplier_lt_mean": supp["lead_time_mean"],
                "supplier_lt_std": supp["lead_time_std"],
                "supplier_fill_rate": supp["fill_rate"],
                "ordering_cost_fixed": float(np.random.choice([65.0, 85.0, 110.0, 140.0, 175.0])),
            })

    # Generate daily records over 180 days across locations and SKUs
    start_date = datetime(2026, 4, 1)
    records = []

    # Calculate combinations to reach ~num_records
    num_skus = len(sku_catalog)
    num_locs = len(LOCATIONS)
    target_days = int(np.ceil(num_records / (num_skus * 4)))  # Sample across 4 locations per SKU per day

    current_date = start_date
    rec_count = 0

    # Stateful inventory simulation tracking per (sku_id, location_id)
    inventory_state = {}
    for sku in sku_catalog:
        for loc in LOCATIONS:
            key = (sku["sku_id"], loc["id"])
            loc_mult = loc["demand_multiplier"]
            daily_mu = sku["base_daily_demand"] * loc_mult
            
            # Initial inventory: intentionally induce either high risk of stockout or high excess
            if sku["turnover_tier"] in ["Fast", "Medium-High"]:
                # 35% chance to start understocked (stockout prone)
                if np.random.rand() < 0.35:
                    init_inv = np.random.uniform(0.5, 2.5) * daily_mu
                else:
                    init_inv = np.random.uniform(5.0, 14.0) * daily_mu
            elif sku["turnover_tier"] in ["Slow-Fashion", "Seasonal-Heavy", "Highly-Seasonal"]:
                # 45% chance to be heavily overstocked (excess inventory)
                if np.random.rand() < 0.45:
                    init_inv = np.random.uniform(45.0, 110.0) * daily_mu
                else:
                    init_inv = np.random.uniform(10.0, 25.0) * daily_mu
            else:
                init_inv = np.random.uniform(12.0, 28.0) * daily_mu

            inventory_state[key] = {
                "on_hand": float(max(5.0, init_inv)),
                "on_order": 0.0,
                "order_due_days": 0,
                "cumulative_stockouts": 0,
                "cumulative_lost_sales": 0.0,
                "cumulative_holding_cost": 0.0,
            }

    day_idx = 0
    while rec_count < num_records:
        current_date = start_date + timedelta(days=day_idx)
        day_of_week = current_date.weekday() # 0 = Mon, 5=Sat, 6=Sun
        month = current_date.month
        
        # Seasonality & promotion modeling
        # Weekend shopping surge: Friday/Saturday/Sunday has 1.25 - 1.45 multiplier
        dow_mult = 1.35 if day_of_week in [4, 5, 6] else 0.92
        # Summer / Back-to-school / Holiday multiplier
        month_mult = 1.15 if month in [7, 8, 11, 12] else 1.00
        is_promo_day = (day_idx % 14 in [0, 1, 2]) # Bi-weekly promotional cycle
        promo_mult = 1.35 if is_promo_day else 1.00

        # Iterate through SKUs and subset of locations to synthesize rich realistic operational telemetry
        for sku in sku_catalog:
            # Pick 4-6 locations randomly each day to get variety
            selected_locs = np.random.choice(LOCATIONS, size=min(4, len(LOCATIONS)), replace=False)
            
            for loc in selected_locs:
                if rec_count >= num_records:
                    break

                key = (sku["sku_id"], loc["id"])
                state = inventory_state[key]

                # Process pending orders arriving
                if state["order_due_days"] > 0:
                    state["order_due_days"] -= 1
                    if state["order_due_days"] == 0:
                        state["on_hand"] += state["on_order"]
                        state["on_order"] = 0.0

                # Calculate actual demand today with stochastic noise, promo lift, seasonality
                loc_mult = loc["demand_multiplier"]
                mean_d = sku["base_daily_demand"] * loc_mult * dow_mult * month_mult * promo_mult
                std_d = sku["demand_std"] * np.sqrt(loc_mult)
                actual_demand = max(0.0, float(np.random.normal(mean_d, std_d)))

                # Sales vs Stockout resolution
                if state["on_hand"] >= actual_demand:
                    units_sold = actual_demand
                    lost_sales = 0.0
                    state["on_hand"] -= units_sold
                    stockout_flag = 0
                else:
                    units_sold = state["on_hand"]
                    lost_sales = actual_demand - state["on_hand"]
                    state["on_hand"] = 0.0
                    stockout_flag = 1
                    state["cumulative_stockouts"] += 1
                    state["cumulative_lost_sales"] += lost_sales

                # Supplier dynamic lead time realization
                supp_lt_noise = float(np.random.normal(sku["supplier_lt_mean"], sku["supplier_lt_std"]))
                realized_lead_time = max(1.5, supp_lt_noise)

                # Classical static ROP policy calculation (legacy benchmark)
                static_safety_stock = 1.645 * (sku["demand_std"] * np.sqrt(sku["supplier_lt_mean"]))
                static_rop = (sku["base_daily_demand"] * loc_mult * sku["supplier_lt_mean"]) + static_safety_stock
                annual_demand = (sku["base_daily_demand"] * loc_mult) * 365.0
                annual_holding_cost_unit = sku["unit_cost"] * sku["holding_cost_rate"]
                static_eoq = np.sqrt((2.0 * annual_demand * sku["ordering_cost_fixed"]) / max(0.1, annual_holding_cost_unit))

                # Check if reorder triggered in legacy system
                inventory_position = state["on_hand"] + state["on_order"]
                reorder_triggered = 0
                if inventory_position <= static_rop and state["on_order"] == 0:
                    # Place order
                    order_qty = static_eoq
                    # Supplier fill rate disruption check
                    if np.random.rand() > sku["supplier_fill_rate"]:
                        # Delayed by 5-10 extra days
                        delivery_days = int(np.ceil(realized_lead_time + np.random.uniform(4.0, 9.0)))
                    else:
                        delivery_days = int(np.ceil(realized_lead_time))
                    
                    state["on_order"] = order_qty
                    state["order_due_days"] = delivery_days
                    reorder_triggered = 1

                # Daily holding cost accrual
                daily_holding_cost = (state["on_hand"] * annual_holding_cost_unit) / 365.0
                state["cumulative_holding_cost"] += daily_holding_cost

                # Stockout revenue loss
                stockout_revenue_loss = lost_sales * sku["unit_price"]

                # Days of Supply (DOS)
                daily_burn_rate = max(0.5, mean_d)
                days_of_supply = round(state["on_hand"] / daily_burn_rate, 1)

                # Inventory health status
                if state["on_hand"] == 0 or (state["on_hand"] < 0.25 * static_rop):
                    inventory_health = "Critical Stockout Risk"
                elif state["on_hand"] <= static_rop:
                    inventory_health = "Under-Stocked (Reorder Point)"
                elif days_of_supply > 65.0:
                    inventory_health = "Severe Excess Inventory"
                elif days_of_supply > 40.0:
                    inventory_health = "Mild Excess Inventory"
                else:
                    inventory_health = "Optimal Inventory Range"

                # Append enriched record
                records.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "sku_id": sku["sku_id"],
                    "sku_name": sku["sku_name"],
                    "category": sku["category"],
                    "turnover_tier": sku["turnover_tier"],
                    "location_id": loc["id"],
                    "location_name": loc["name"],
                    "location_type": loc["type"],
                    "region": loc["region"],
                    "daily_demand": round(actual_demand, 1),
                    "units_sold": round(units_sold, 1),
                    "lost_sales_units": round(lost_sales, 1),
                    "stockout_flag": stockout_flag,
                    "on_hand_inventory": round(state["on_hand"], 1),
                    "on_order_inventory": round(state["on_order"], 1),
                    "inventory_position": round(inventory_position, 1),
                    "days_of_supply": days_of_supply,
                    "unit_cost": sku["unit_cost"],
                    "unit_price": sku["unit_price"],
                    "gross_margin_pct": round(((sku["unit_price"] - sku["unit_cost"]) / sku["unit_price"]) * 100.0, 1),
                    "holding_cost_daily": round(daily_holding_cost, 2),
                    "stockout_revenue_loss": round(stockout_revenue_loss, 2),
                    "supplier_id": sku["supplier_id"],
                    "supplier_name": sku["supplier_name"],
                    "supplier_lead_time_days": round(realized_lead_time, 1),
                    "supplier_lead_time_std": sku["supplier_lt_std"],
                    "supplier_fill_rate": sku["supplier_fill_rate"],
                    "promotion_active": 1 if is_promo_day else 0,
                    "day_of_week": day_of_week,
                    "month": month,
                    "seasonality_factor": round(dow_mult * month_mult * promo_mult, 3),
                    "static_rop": round(static_rop, 1),
                    "static_safety_stock": round(static_safety_stock, 1),
                    "static_eoq": round(static_eoq, 1),
                    "inventory_health": inventory_health,
                })
                rec_count += 1

        day_idx += 1

    df = pd.DataFrame(records)
    csv_file = os.path.join(output_dir, "walmart_inventory_data.csv")
    df.to_csv(csv_file, index=False)
    print(f"[Synthesizer] Successfully saved {len(df):,} telemetry records to {csv_file}")

    # Generate Suppliers Directory
    supp_df = pd.DataFrame(SUPPLIERS)
    supp_csv = os.path.join(output_dir, "walmart_suppliers_directory.csv")
    supp_df.to_csv(supp_csv, index=False)
    print(f"[Synthesizer] Successfully saved {len(supp_df)} supplier profiles to {supp_csv}")

    return df, supp_df

if __name__ == "__main__":
    generate_walmart_inventory_dataset(num_records=16000)
