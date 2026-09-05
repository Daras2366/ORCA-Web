"""Verification script for the ORCA Routing Agent M3_v2 integration."""
import sys
import os
import json
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
from backend.agents.routing_agent.predict import predict_route

df = pd.read_csv(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "routing", "M3_final_routing_dataset.csv"
    )
)

print("=== VERIFICATION AGAINST CSV ===")
for z in ["PFZ0001", "PFZ0319"]:
    row = df[df["zone_id"] == z].iloc[0]
    res = predict_route(row.to_dict())
    print()
    print(f"Zone: {z}")
    csv_score = round(row["final_route_score"], 4)
    api_score = res["route_score"]
    match = "MATCH" if abs(csv_score - api_score) < 0.0001 else "DIFFER"
    print(f"  CSV final_route_score:      {csv_score}")
    print(f"  API route_score:            {api_score}  [{match}]")
    print(f"  CSV confidence:             {round(row['final_route_confidence'], 4)}")
    print(f"  API confidence:             {res['confidence']}")
    print(f"  CSV adjusted:               {round(row['adjusted_final_route_score'], 4)}")
    print(f"  API adjusted_route_score:   {res['adjusted_route_score']}")
    print(f"  CSV route_safety_score:     {round(row['route_safety_score'], 4)}")
    print(f"  API route_safety_score:     {res['route_safety_score']}")

print()
print("=== NaN / Infinity check across ALL 2037 rows ===")
problems = []
for idx, row in df.iterrows():
    res = predict_route(row.to_dict())
    flat = json.dumps(res)
    if "NaN" in flat or "Infinity" in flat or "inf" in flat.lower():
        problems.append(row["zone_id"])

if problems:
    print(f"FAIL - NaN/Infinity found in {len(problems)} zones: {problems[:10]}")
else:
    print(f"PASS - no NaN/Infinity values across all {len(df)} zones")

print()
print("=== Absolute path check ===")
files_to_check = [
    "backend/api/route_api.py",
    "backend/agents/routing_agent/predict.py",
]
bad_found = False
for fpath in files_to_check:
    with open(fpath, encoding="utf-8") as f:
        content = f.read()
    has_abs = "C:\\Users" in content or "/home/" in content or "/Users/" in content
    if has_abs:
        print(f"  FAIL - absolute path found in {fpath}")
        bad_found = True
if not bad_found:
    print("  PASS - no absolute local paths in any checked file")

