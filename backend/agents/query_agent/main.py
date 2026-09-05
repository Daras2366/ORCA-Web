from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.agents.query_agent.schemas import QueryRequest
from backend.gemini_client import ask_gemini
from backend.agents.query_agent.gemini_planner import plan_query

import requests, pandas as pd, re, os
from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt

app = FastAPI(title="ORCA Query Agent", version="7.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OCEAN_API="http://localhost:8002"
SAFETY_API="http://localhost:8003"
ROUTE_API="http://localhost:8004"
DECISION_API="http://localhost:8000"

def gemini_classify(query: str) -> str:
    prompt = f"""
You are the intent planner for ORCA, a marine intelligence system.

Classify the user's request into ONE of these categories:

- fishing
- ocean
- safety
- route
- general

Return ONLY the category name.

User request:
{query}
"""

    return ask_gemini(prompt).strip().lower()

def get_gemini_plan(query: str) -> dict:
    """
    Get Gemini's interpretation of the user's query.

    Gemini is advisory only. The deterministic parser remains
    the fallback/source for exact ORCA query handling.
    """
    return plan_query(query)

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

OCEAN_DATA = os.path.join(
    BASE_DIR,
    "data",
    "ocean",
    "unified_ocean_current.csv"
)

ROUTING_DATA = os.path.join(
    BASE_DIR,
    "data",
    "routing",
    "M3_final_routing_dataset.csv"
)

def df():
    x=pd.read_csv(OCEAN_DATA)
    x.columns=x.columns.str.strip()
    return x

def routing_df():
    x = pd.read_csv(ROUTING_DATA)
    x.columns = x.columns.str.strip()
    return x

def zones(pfz=True):
    x=df()
    if pfz and "pfz_label" in x:
        y=x[x.pfz_label==1]
        if not y.empty: x=y
    return x.zone_id.dropna().astype(str).unique().tolist()

def coords(z):
    x=df()
    r=x[x.zone_id.astype(str).str.upper()==z.upper()]
    if r.empty:return None
    r=r.iloc[0]
    return float(r.latitude),float(r.longitude)

def hav(a,b,c,d):
    a,b,c,d=map(radians,[a,b,c,d])
    q=sin((c-a)/2)**2+cos(a)*cos(c)*sin((d-b)/2)**2
    return 6371.0088*2*asin(sqrt(q))

def call(url,payload,timeout=5):
    try:
        r=requests.post(url,json=payload,timeout=timeout)
        if r.status_code!=200:return {"status":"error","message":r.text}
        return r.json()
    except Exception as e:return {"status":"error","message":str(e)}

def ocean(z): return call(f"{OCEAN_API}/ocean/analyze",{"zone_id":z})
def safety(z): return call(f"{SAFETY_API}/safety/analyze",{"zone_id":z})
def route(z): return call(f"{ROUTE_API}/route/analyze",{"zone_id":z})
def forecast(z): return call(f"{SAFETY_API}/safety/forecast",{"zone_id":z},60)
def safest_time(z): return call(f"{SAFETY_API}/safety/safest-time",{"zone_id":z},60)

def parse(q):
    t=q.lower().strip()
    intent=[]
     
    if any(w in t for w in ["fish","fishing","pfz","sst","chlorophyll","productivity"]):
        intent.append("fishing")
    if any(w in t for w in ["safe","safety","risk","danger","cyclone","storm","wind","wave","avoid","warning","boat"]):
        intent.append("safety")
    if any(w in t for w in ["route","distance","far","closest","nearest","litre","liter","fuel","travel","harbour","harbor","reach"]):
        intent.append("route")
    if any(w in t for w in ["ocean", "ocean condition", "ocean conditions", "sea condition", "sea conditions", "sst", "chlorophyll", "current"]): 
        intent.append("ocean")

    m=re.search(r"(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)",t)
    lat,lon=(float(m.group(1)),float(m.group(2))) if m else (None,None)
    zm=re.findall(r"\b(?:PFZ|Z)\s*[-_]?\s*(\d+)\b",t,re.I)
    zs=["PFZ"+n.zfill(4) for n in zm]
    z=zs[0] if zs else None
    z2=zs[1] if len(zs)>1 else None
    dm=re.search(r"(\d+(?:\.\d+)?)\s*(?:km|kilometer|kilometers|kilometre|kilometres)",t)
    fm=re.search(r"(\d+(?:\.\d+)?)\s*(?:l|litre|litres|liter|liters)\b",t)
    dist=float(dm.group(1)) if dm else None
    fuel=float(fm.group(1)) if fm else None

    # Specific phrases FIRST to avoid parser collisions.
    qt="general"
    if "cyclone warning" in t: qt="cyclone_scenario"
    elif "lowest travel time" in t: qt="lowest_travel_time"
    elif "safest time" in t or ("what time" in t and "safe" in t): qt="safest_time"
    elif "tomorrow" in t and any(w in t for w in ["safe","safety","risk","wind","wave"]): qt="tomorrow_safety"
    elif "tomorrow" in t and "fishing" in t: qt="tomorrow_fishing"
    elif ("wave" in t and ("safe" in t or "condition" in t or "height" in t or "period" in t)): qt="wave_safety"
    elif ("wind" in t and ("safe" in t or "condition" in t or "speed" in t)): qt="wind_safety"
    elif "cyclone" in t or "storm risk" in t: qt="cyclone_risk"
    elif "safest route" in t or "which route is safest" in t: qt="safest_route"
    elif z and ("safe" in t or "safety" in t or "risk" in t or "danger" in t or "can i go" in t): qt="zone_safety"
    elif any(phrase in t for phrase in [
        "before going fishing", "before fishing", "before i go fishing",
        "what should i know", "what should i check", "any advice",
        "what do i need to know", "what should i consider",
    ]) and any(w in t for w in ["fish", "fishing", "go out", "sea"]): qt="fishing_advice"
    elif "highest fishing potential" in t or "best fishing zone" in t or "highest potential" in t: qt="highest_fishing"
    elif "highest pfz confidence" in t or "highest confidence" in t: qt="highest_confidence"
    elif "favourable sst" in t or "favorable sst" in t: qt="favourable_sst"
    elif "favourable chlorophyll" in t or "favorable chlorophyll" in t: qt="favourable_chlorophyll"
    elif "best combination" in t or ("pfz" in t and "sst" in t and "chlorophyll" in t): qt="best_combination"
    elif z2 and ("better for fishing" in t or "better for" in t or "why" in t): qt="fishing_comparison"
    elif "within" in t and dist is not None: qt="nearby_zones"
    elif "nearby" in t and "rank" in t: qt="nearby_ranking"
    elif "rank" in t and "fishing" in t: qt="nearby_ranking"
    elif z2 and ("safer" in t or "which is safer" in t): qt="safety_comparison"
    elif "safest fishing zone" in t or "which fishing zone is safest" in t: qt="safest"
    elif "current risk" in t or "risk level at my location" in t: qt="current_risk"
    elif "avoid zones" in t or "which zones should i avoid" in t: qt="avoid_zones"
    elif "remain safe" in t or "after 9 am" in t or "after 9am" in t: qt="future_safety"
    elif ("shortest route" in t or "route is the shortest" in t or "shortest" in t or "minimum distance" in t): qt = "shortest_route"
    elif "how far" in t or "distance" in t: qt = "distance"
    elif "how long" in t or "travel time" in t: qt = "travel_time"
    elif "how much fuel" in t or "fuel will i need" in t: qt = "fuel"
    elif ("least fuel" in t or "lowest fuel" in t or "minimum fuel" in t or "least amount of fuel" in t): qt = "least_fuel"
    elif "closest" in t or "nearest" in t: qt="closest"
    elif "can i reach" in t and fuel is not None: qt="fuel_feasibility"
    elif "safest route" in t: qt="safest_route"
    elif "show me the route" in t: qt="route_geometry"
    elif "why" in t: qt="explanation"

    qdate=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d") if "tomorrow" in t else (datetime.now().strftime("%Y-%m-%d") if "today" in t else None)
    req=[]
    if "fishing" in intent:req.append("ocean")
    if "safety" in intent:req.append("safety")
    if "route" in intent:req.append("route")
    return {"query":q,"intents":intent,"query_type":qt,"latitude":lat,"longitude":lon,
            "zone_id":z,"comparison_zone":z2,"zones":zs,"datetime":qdate,
            "distance_km":dist,"fuel_litres":fuel,"required_agents":req}

def nearest(lat, lon):
    x = df().copy()

    # Prefer PFZ rows when available so dashboard queries
    # do not accidentally select empty GRID rows.
    if "pfz_label" in x.columns:
        pfz = x[x["pfz_label"] == 1]
        if not pfz.empty:
            x = pfz

    x["_d"] = [
        hav(lat, lon, float(a), float(b))
        for a, b in zip(x.latitude, x.longitude)
    ]

    return x.sort_values("_d").iloc[0]

def direct_ocean_ranking(qt):
    x=df().copy()
    x=x[x.pfz_label==1] if "pfz_label" in x and not x[x.pfz_label==1].empty else x
    # Use Ocean Agent formula thresholds so ranking remains consistent with the API.
    def norm_chl(v): return max(0,min(1,(v-.05)/(.50-.05)))
    def sst(v): return max(0,1-abs(v-28)/5)
    rows=[]
    for _,r in x.iterrows():
        chl=pd.to_numeric(r.get("chlorophyll_mean"),errors="coerce")
        ss=pd.to_numeric(r.get("sst_c"),errors="coerce")
        cur=pd.to_numeric(r.get("current_speed_ms"),errors="coerce")
        comps=[]
        if pd.notna(chl): comps.append(("chlorophyll",norm_chl(float(chl)),.40))
        if pd.notna(ss): comps.append(("sst",sst(float(ss)),.30))
        if pd.notna(cur): comps.append(("current",max(0,min(1,1-abs(float(cur)-.5)/.5)),.30))
        score=sum(v*w for _,v,w in comps)/sum(w for _,v,w in comps) if comps else 0
        rows.append({"zone_id":str(r.zone_id),"fishing_score":round(score,4),
                     "chlorophyll_hsi":round(norm_chl(float(chl)),4) if pd.notna(chl) else None,
                     "sst_hsi":round(sst(float(ss)),4) if pd.notna(ss) else None,
                     "chlorophyll":float(chl) if pd.notna(chl) else None,
                     "sst_c":float(ss) if pd.notna(ss) else None})
    return rows

def run_multi_agent_plan(p, gemini_plan, target_z=None):
    """
    Execute multiple ORCA specialist agents based on Gemini's plan.

    Gemini decides which agents are needed.
    The specialist agents provide the actual data.
    The Decision Layer makes the final combined decision.

    This function is only for current-data compound requests.
    Future/forecast queries continue through the existing
    deterministic forecast logic.
    """

    required_agents = gemini_plan.get("required_agents", [])

    if not isinstance(required_agents, list):
        required_agents = []

    # ---------------------------------------------------------
    # Determine the target zone
    # ---------------------------------------------------------

    # If the user explicitly supplied a zone, use it.
    zone_id = p.get("zone_id") or target_z

    # For fishing recommendations without an explicit zone,
    # first use the Ocean Agent data to find the strongest zone.
    if "ocean" in required_agents and not zone_id:

        ocean_ranking = direct_ocean_ranking("highest_fishing")

        if not ocean_ranking:
            return {
                "status": "error",
                "mode": "multi_agent",
                "parsed": p,
                "message": "No ocean observations are available."
            }

        ocean_ranking.sort(
            key=lambda x: x.get("fishing_score", 0),
            reverse=True
        )

        zone_id = ocean_ranking[0]["zone_id"]

    # If there is no fishing request but safety/route needs
    # a zone, use the nearest zone to the user's location.
    if not zone_id:
        zone_id = target_z

    if not zone_id:
        return {
            "status": "needs_location",
            "mode": "multi_agent",
            "parsed": p,
            "answer": (
                "Please provide a PFZ zone or your location "
                "so I can determine which zone to analyse."
            )
        }

    # ---------------------------------------------------------
    # Call specialist agents
    # ---------------------------------------------------------

    ocean_result = None
    safety_result = None
    route_result = None

    if "ocean" in required_agents:
        ocean_result = ocean(zone_id)

        if ocean_result.get("status") != "success":
            return {
                "status": "error",
                "mode": "multi_agent",
                "parsed": p,
                "message": ocean_result.get(
                    "message",
                    "Ocean Agent failed."
                )
            }

    if "safety" in required_agents:
        safety_result = safety(zone_id)

        if safety_result.get("status") != "success":
            return {
                "status": "error",
                "mode": "multi_agent",
                "parsed": p,
                "message": safety_result.get(
                    "message",
                    "Safety Agent failed."
                )
            }

    if "route" in required_agents:
        route_result = route(zone_id)

        if route_result.get("status") != "success":
            return {
                "status": "error",
                "mode": "multi_agent",
                "parsed": p,
                "message": route_result.get(
                    "message",
                    "Route Agent failed."
                )
            }

    # ---------------------------------------------------------
    # Decision Layer
    # ---------------------------------------------------------

    # The Decision Layer requires all three agent outputs.
    # If an agent was not requested, we don't manufacture data.
    #
    # Therefore the combined Decision Layer is only called
    # when all three specialist agents are available.
    if (
        ocean_result is not None
        and safety_result is not None
        and route_result is not None
    ):

        decision_payload = {
            "ocean": {
                "zone_id": zone_id,
                "score": float(
                    ocean_result.get("fishing_score", 0)
                ),
                "evidence": ocean_result.get(
                    "evidence",
                    {}
                )
            },
            "safety": {
                "zone_id": zone_id,
                "score": float(
                    safety_result.get("risk_score", 0)
                ),
                "evidence": safety_result.get(
                    "evidence",
                    {}
                )
            },
            "route": {
                "zone_id": zone_id,
                "score": float(
                    route_result.get("route_score", 0)
                ),
                "evidence": route_result.get(
                    "route_metrics",
                    {}
                )
            }
        }

        decision_result = call(
            f"{DECISION_API}/decision/combined",
            decision_payload,
            timeout=10
        )

        if decision_result.get("status") == "error":
            return {
                "status": "error",
                "mode": "multi_agent",
                "parsed": p,
                "zone_id": zone_id,
                "ocean": ocean_result,
                "safety": safety_result,
                "route": route_result,
                "message": decision_result.get(
                    "message",
                    "Decision Layer failed."
                )
            }

    else:
        decision_result = None

    # ---------------------------------------------------------
    # Build grounded answer
    # ---------------------------------------------------------

    answer_parts = [
        f"ORCA analysed {zone_id} using "
        f"{', '.join(required_agents)}."
    ]

    if ocean_result is not None:

        fishing_score = ocean_result.get(
            "fishing_score"
        )

        if fishing_score is not None:
            answer_parts.append(
                f"Fishing potential score: "
                f"{float(fishing_score):.2f}."
            )

    if safety_result is not None:

        risk_score = safety_result.get(
            "risk_score"
        )

        risk_level = safety_result.get(
            "risk_level",
            "UNKNOWN"
        )

        if risk_score is not None:
            safety_score = (
                1 - float(risk_score)
            ) * 100

            answer_parts.append(
                f"Safety: {risk_level}, "
                f"safety score "
                f"{safety_score:.1f}/100."
            )

    if route_result is not None:

        metrics = route_result.get(
            "route_metrics",
            {}
        )

        distance = metrics.get(
            "distance_km"
        )

        travel_time = metrics.get(
            "travel_time_hr"
        )

        if distance is not None:
            route_text = (
                f"Route distance: "
                f"{float(distance):.2f} km"
            )

            if travel_time is not None:
                route_text += (
                    f", estimated travel time: "
                    f"{float(travel_time):.2f} hours"
                )

            answer_parts.append(
                route_text + "."
            )

    if decision_result:

        decision = decision_result.get(
            "decision"
        )

        final_score = decision_result.get(
            "final_score"
        )

        if decision:
            answer_parts.append(
                f"Decision Layer recommendation: "
                f"{decision}."
            )

        if final_score is not None:
            answer_parts.append(
                f"Combined decision score: "
                f"{float(final_score):.2f}."
            )

    return {
        "status": "success",
        "mode": "multi_agent",
        "zone_id": zone_id,
        "parsed": p,
        "gemini_plan": gemini_plan,
        "ocean": ocean_result,
        "safety": safety_result,
        "route": route_result,
        "decision": decision_result,
        "answer": " ".join(answer_parts)
    }

@app.post("/query")
@app.post("/api/query")
def query(req: QueryRequest):
    q = req.query.strip()
    
    if not q:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )

    p = parse(q)

    # ---------------------------------------------------------
    # GEMINI PLANNER
    # ---------------------------------------------------------
    # Gemini understands the user's request, while the existing
    # deterministic parser continues to provide exact query
    # handling and remains the fallback.
    gemini_plan = get_gemini_plan(q)

    p["gemini_plan"] = gemini_plan
    
    gemini_intent = gemini_plan.get("intent")

    if gemini_intent and gemini_intent != "general":
        if gemini_intent not in p["intents"]:
            p["intents"].append(gemini_intent)

    # Merge Gemini's required agents with the deterministic parser.
    # The deterministic parser remains the fallback.
    gemini_agents = gemini_plan.get("required_agents", [])

    if not isinstance(gemini_agents, list):
        gemini_agents = []

    existing_agents = p.get("required_agents", [])

    if not isinstance(existing_agents, list):
        existing_agents = []

    p["required_agents"] = list(
        dict.fromkeys(existing_agents + gemini_agents)
    )

    # If the user did not type coordinates in the question,
    # use the coordinates supplied by the frontend.
    if p["latitude"] is None:
        p["latitude"] = req.latitude

    if p["longitude"] is None:
        p["longitude"] = req.longitude

    qt = p["query_type"]
    z = p["zone_id"]
    z2 = p["comparison_zone"]

    target_z = z

    if not target_z and p["latitude"] is not None and p["longitude"] is not None:
        target_z = str(nearest(p["latitude"], p["longitude"]).zone_id)

    # ---------------------------------------------------------
    # GEMINI MULTI-AGENT ORCHESTRATION
    # ---------------------------------------------------------
    #
    # Only use this for current-data compound requests.
    # Forecast/tomorrow queries continue through the existing
    # deterministic forecast branches.
    #
    # This prevents current observations from being presented
    # as future predictions.

    gemini_agents = gemini_plan.get(
        "required_agents",
        []
    )

    if (
        len(gemini_agents) >= 2
        and "tomorrow" not in q.lower()
    ):
        return run_multi_agent_plan(
            p,
            gemini_plan,
            target_z
        )
            
    # Current location
    if qt=="current_risk" and not z:
        if p["latitude"] is None:return {"status":"needs_location","parsed":p,"answer":"Please provide your current latitude and longitude."}
        r=nearest(p["latitude"],p["longitude"]); z=str(r.zone_id)
        s=safety(z)
        return {"status":"success","mode":"current_risk","zone_id":z,"distance_km":round(float(r._d),2),"safety":s,
                "answer":f"At your nearest ORCA zone {z}, the current risk level is {s.get('risk_level')} (risk score {s.get('risk_score')})."}

    # Fishing potential at the user's current location
    if qt == "general" and "fishing" in p["intents"] and not z:

        if "current location" in q.lower() or "my location" in q.lower():

            if p["latitude"] is None or p["longitude"] is None:
                return {
                    "status": "needs_location",
                    "parsed": p,
                    "answer": (
                        "Please allow location access so I can "
                        "find the nearest fishing zone."
                    )
                }

            nearest_zone = nearest(
                p["latitude"],
                p["longitude"]
            )

            nearest_id = str(nearest_zone.zone_id)

            # Calculate actual distance
            distance = hav(
                p["latitude"],
                p["longitude"],
                float(nearest_zone.latitude),
                float(nearest_zone.longitude)
            )

            ocean_result = ocean(nearest_id)

            if ocean_result.get("status") != "success":
                return {
                    "status": "error",
                    "parsed": p,
                    "message": ocean_result.get(
                        "message",
                        "Ocean Agent error"
                    )
                }

            fishing_score = ocean_result.get(
                "fishing_score"
            )

            potential = (
                "High"
                if fishing_score is not None and fishing_score >= 0.7
                else "Medium"
                if fishing_score is not None and fishing_score >= 0.4
                else "Low"
            )

            return {
                "status": "success",
                "mode": "current_location_fishing",
                "zone_id": nearest_id,
                "distance_km": round(distance, 2),
                "ocean": ocean_result,
                "answer": (
                    f"The nearest fishing zone to your location is "
                    f"{nearest_id}, approximately {distance:.2f} km away. "
                    f"Its current fishing potential is "
                    f"{fishing_score:.2f} ({potential})."
                    if fishing_score is not None
                    else
                    f"The nearest fishing zone to your location is "
                    f"{nearest_id}, approximately {distance:.2f} km away, "
                    f"but its current fishing potential is unavailable."
                )
            }

    if qt=="tomorrow_safety":
        if not z:
            if p["latitude"] is not None:
                z=str(nearest(p["latitude"],p["longitude"]).zone_id)
            else:
                return {"status":"needs_location","parsed":p,"answer":"Please provide a zone or your latitude and longitude."}
        f=forecast(z)
        if f.get("status")!="success":
            return {"status":"error","parsed":p,"message":f.get("message")}
        hs=f.get("hourly",f.get("hourly_forecast",[]))
        levels=[h.get("forecast_safety_level") for h in hs if h.get("forecast_safety_level")]
        safe=sum(x=="SAFE" for x in levels)
        overall="SAFE" if safe==len(levels) and levels else ("MOSTLY SAFE" if safe>=len(levels)*0.75 else "CAUTION")
        return {"status":"success","mode":qt,"zone_id":z,"forecast_date":f.get("date"),
                "hourly":hs,"safe_hours":safe,"total_hours":len(levels),"overall_assessment":overall,
                "answer":f"Tomorrow {z} is {overall}. {safe} of {len(levels)} forecast hours are SAFE."}

    if qt=="tomorrow_fishing":
        return {"status":"unavailable","mode":qt,"parsed":p,
                "answer":"Tomorrow's fishing-potential forecast is not available yet because ORCA does not currently have forecast SST, chlorophyll and current data. I will not present current fishing potential as a tomorrow prediction."}

    if qt=="safest_time":
        if not z:
            if p["latitude"] is not None:
                z=str(nearest(p["latitude"],p["longitude"]).zone_id)
            else:return {"status":"needs_location","parsed":p,"answer":"Please provide a zone or your latitude and longitude."}
        f=safest_time(z)
        if f.get("status")!="success":return {"status":"error","parsed":p,"message":f.get("message")}
        return {"status":"success","mode":qt,"zone_id":z,"date":f["date"],"safest_time":f["safest_time"],
                "forecast_safety_score":f["forecast_safety_score"],"forecast_safety_level":f["forecast_safety_level"],
                "conditions":f["conditions"],"answer":f"Tomorrow the safest time for {z} is {f['safest_time'][-5:]}. Safety score: {f['forecast_safety_score']}/100 ({f['forecast_safety_level']})."}

    # Ocean rankings without 337 HTTP calls
    if qt in [
        "highest_fishing",
        "highest_confidence",
        "favourable_sst",
        "favourable_chlorophyll",
        "best_combination",
    ]:

        rows = direct_ocean_ranking(qt)

        # Highest data completeness
        if qt == "highest_confidence":
            raw = df()
            conf = []

            for _, r in raw[raw.pfz_label == 1].iterrows():
                vals = [
                    pd.notna(r.get("chlorophyll_mean")),
                    pd.notna(r.get("sst_c")),
                    pd.notna(r.get("current_speed_ms")),
                ]

                conf.append({
                    "zone_id": str(r.zone_id),
                    "data_completeness": round(sum(vals) / 3, 3),
                    "available_components": sum(vals),
                    "total_components": 3,
                })

            conf.sort(
                key=lambda x: x["data_completeness"],
                reverse=True
            )

            if not conf:
                return {
                    "status": "success",
                    "mode": qt,
                    "parsed": p,
                    "answer": "No PFZ observations are available."
                }

            top = conf[:10]

            return {
                "status": "success",
                "mode": qt,
                "parsed": p,
                "recommended_zone": top[0]["zone_id"],
                "ranking": top,
                "answer": (
                    f"{top[0]['zone_id']} has the highest ocean-data "
                    f"completeness at "
                    f"{top[0]['data_completeness'] * 100:.0f}%. "
                    f"{top[0]['available_components']} of "
                    f"{top[0]['total_components']} ocean variables "
                    f"(SST, chlorophyll and current) are available."
                )
            }

        # Sort according to the requested ocean property
        if qt == "favourable_sst":
            rows = [
                r for r in rows
                if r["sst_c"] is not None
            ]
            rows.sort(
                key=lambda r: r["sst_hsi"],
                reverse=True
            )

        elif qt == "favourable_chlorophyll":
            rows = [
                r for r in rows
                if r["chlorophyll"] is not None
            ]
            rows.sort(
                key=lambda r: r["chlorophyll_hsi"],
                reverse=True
            )

        else:
            rows.sort(
                key=lambda r: r["fishing_score"],
                reverse=True
            )

        top = rows[:10]

        if not top:
            return {
                "status": "success",
                "mode": qt,
                "parsed": p,
                "answer": "No suitable ocean observations are available."
            }

        # Correct natural-language answers
        if qt == "highest_fishing":
            top5 = top[:5]
            lines = ["Top fishing zones\n"]
            for i, r in enumerate(top5, 1):
                lines.append(f"{i}. {r['zone_id']} — HSI {r['fishing_score']:.2f}")
            answer = "\n".join(lines)

        elif qt == "favourable_sst":
            answer = (
                f"{top[0]['zone_id']} has the most favourable SST "
                f"among the available PFZ observations: "
                f"{top[0]['sst_c']:.2f}°C "
                f"(SST suitability score {top[0]['sst_hsi']:.2f})."
            )

        elif qt == "favourable_chlorophyll":
            answer = (
                f"{top[0]['zone_id']} has the most favourable "
                f"chlorophyll conditions among the available PFZ "
                f"observations: "
                f"{top[0]['chlorophyll']:.3f} mg/m³ "
                f"(chlorophyll suitability score "
                f"{top[0]['chlorophyll_hsi']:.2f})."
            )

        else:
            answer = (
                f"{top[0]['zone_id']} has the strongest overall "
                f"fishing-potential combination with an HSI of "
                f"{top[0]['fishing_score']:.2f}."
            )

        return {
            "status": "success",
            "mode": qt,
            "parsed": p,
            "recommended_zone": top[0]["zone_id"],
            "ranking": top,
            "answer": answer,
        }

    # Fishing advice / pre-trip checklist
    if qt == "fishing_advice":
        lines = [
            "Before going fishing, here are the key things to check:\n",
            "1. Safety & risk — Check current risk levels for your target zone.",
            "2. Wind & waves — Review wind speed and wave height forecasts.",
            "3. Cyclone / storm warnings — Check for any active warnings in the area.",
            "4. Fishing potential — Check SST, chlorophyll and ocean current conditions.",
            "5. Fuel & route — Ensure you have sufficient fuel and a safe planned route.",
        ]
        if target_z:
            s = safety(target_z)
            if s.get("status") == "success":
                risk_level = s.get("risk_level", "UNKNOWN")
                risk_score = s.get("risk_score")
                risk_note = (
                    f"Risk score: {risk_score:.4f}." if risk_score is not None else ""
                )
                lines.append(
                    f"\nYour nearest zone {target_z} is currently "
                    f"{risk_level}. {risk_note}"
                )
        return {
            "status": "success",
            "mode": "fishing_advice",
            "zone_id": target_z,
            "answer": "\n".join(lines),
        }

    # Specific comparisons
    if z2 and qt in ["fishing_comparison","safety_comparison"]:
        a=ocean(z); b=ocean(z2) if qt=="fishing_comparison" else None
        sa=safety(z); sb=safety(z2)
        if qt=="fishing_comparison":
            av=a.get("fishing_score",0); bv=b.get("fishing_score",0)
            winner=z if av>=bv else z2
            return {"status":"success","mode":qt,"zones":[{"zone_id":z,"ocean":a},{"zone_id":z2,"ocean":b}],
                    "winner":winner,"answer":f"{winner} is better for fishing: fishing score {av if winner==z else bv:.4f} versus {bv if winner==z else av:.4f}."}
        ar=sa.get("risk_score",1); br=sb.get("risk_score",1); winner=z if ar<=br else z2
        
        winner_score = ar if winner == z else br
        loser = z2 if winner == z else z
        loser_score = br if winner == z else ar

        return {
            "status": "success",
            "mode": qt,
            "zones": [
                {"zone_id": z, "safety": sa},
                {"zone_id": z2, "safety": sb}
            ],
            "winner": winner,
            "answer": (
                f"🛡️ {winner} is safer.\n\n"
                f"• {winner}: risk score {winner_score:.4f}\n"
                f"• {loser}: risk score {loser_score:.4f}"
            )
        }

    # Specific current zone safety
    if z and qt == "zone_safety":
        s = safety(z)

        if s.get("status") != "success":
            return {
                "status": "error",
                "parsed": p,
                "message": s.get("message", "Unable to retrieve safety information.")
            }

        risk_score = s.get("risk_score")
        risk_level = s.get("risk_level", "UNKNOWN")

        if risk_score is not None:
            safety_score = round((1 - float(risk_score)) * 100, 1)
        else:
            safety_score = None

        if risk_level == "LOW":
            recommendation = "Conditions currently indicate relatively low risk."
        elif risk_level == "MODERATE":
            recommendation = "Proceed with caution and monitor conditions."
        elif risk_level == "HIGH":
            recommendation = "Avoid this zone under the current conditions."
        else:
            recommendation = "Safety could not be determined from the available data."

        return {
            "status": "success",
            "mode": "zone_safety",
            "zone_id": z,
            "safety": s,
            "answer": (
                f"{z} is currently {risk_level}. "
                f"Risk score: {risk_score}. "
                f"Safety score: {safety_score}/100. "
                f"{recommendation}"
            )
        }

    # Specific safety forecast questions
    if qt in ["future_safety", "wave_safety", "wind_safety", "cyclone_risk"]:

        # Use the explicitly mentioned PFZ if provided.
        # Otherwise use the nearest PFZ determined from frontend coordinates.
        safety_zone = z or target_z

        if not safety_zone:
            return {
                "status": "needs_location",
                "mode": qt,
                "parsed": p,
                "answer": (
                    "Please provide a PFZ zone or allow location access "
                    "so I can check the current conditions."
                )
            }

        f = (
            forecast(safety_zone)
            if qt in ["future_safety", "wave_safety", "wind_safety"]
            else safety(safety_zone)
        )
        
        if f.get("status")!="success":return {"status":"error","parsed":p,"message":f.get("message")}
        if qt=="future_safety":
            hs=f.get("hourly",f.get("hourly_forecast",[]))
            after=[h for h in hs if int(str(h.get("time",""))[-5:-3] or 0)>=9]
            safe = [h for h in after if str(h.get("safety_level","")).upper()=="SAFE"]
            moderate = [h for h in after if str(h.get("safety_level","")).upper()=="MODERATE"]
            unsafe = [h for h in after if str(h.get("safety_level","")).upper()=="UNSAFE"]
            assessment = "NOT CONTINUOUSLY SAFE" if unsafe else ("MOSTLY SAFE" if moderate else "SAFE")
            times = ", ".join(str(h.get("time",""))[-5:] for h in moderate[:5])
            answer = (
                f"{safety_zone} is {assessment} after 9 AM: "
                f"{len(safe)} of {len(after)} forecast hours are SAFE"
            )
            if moderate:
                answer += f"; {len(moderate)} hour(s) are MODERATE"
                if times: answer += f" ({times})"
            if unsafe: answer += f"; {len(unsafe)} hour(s) are UNSAFE"
            answer += "."
            return {
                "status": "success",
                "mode": qt,
                "zone_id": safety_zone,
                "forecast_date": f.get("date"),
                "after_9_am": after,
                "safe_hours": len(safe),
                "moderate_hours": len(moderate),
                "unsafe_hours": len(unsafe),
                "answer": answer.replace(z, safety_zone) if z else (
                    f"{safety_zone} is {assessment} after 9 AM: "
                    f"{len(safe)} of {len(after)} forecast hours are SAFE"
                    + (
                        f"; {len(moderate)} hour(s) are MODERATE"
                        + (f" ({times})" if times else "")
                        if moderate else ""
                    )
                    + (f"; {len(unsafe)} hour(s) are UNSAFE" if unsafe else "")
                    + "."
                )
            }
            
        if qt == "wave_safety":
            hs = f.get("hourly", f.get("hourly_forecast", []))

            if not hs:
                return {
                    "status": "success",
                    "mode": qt,
                    "zone_id": z,
                    "forecast": f,
                    "answer": f"No wave forecast is currently available for {z}."
                }

            h = hs[0]

            wave_height = h.get("wave_height_m")
            wave_period = h.get("wave_period_s")
            wave_score = h.get("wave_safety")

            if wave_score is not None:
                if wave_score >= 80:
                    level = "SAFE"
                elif wave_score >= 60:
                    level = "MODERATE"
                elif wave_score >= 40:
                    level = "CAUTION"
                else:
                    level = "UNSAFE"
            else:
                level = "UNKNOWN"

            return {
                "status": "success",
                "mode": qt,
                "zone_id": safety_zone,
                "forecast": f,
                "answer": (
                    f"🌊 Wave conditions at {safety_zone}: "
                    f"{wave_height if wave_height is not None else 'N/A'} m height, "
                    f"{wave_period if wave_period is not None else 'N/A'} s period. "
                    f"Wave safety: "
                    f"{wave_score if wave_score is not None else 'N/A'}/100 "
                    f"({level})."
                )
            }
            
        if qt == "wind_safety":
            hs = f.get("hourly", f.get("hourly_forecast", []))

            if not hs:
                return {
                    "status": "success",
                    "mode": qt,
                    "zone_id": safety_zone,
                    "forecast": f,
                    "answer": f"No wind forecast is currently available for {safety_zone}."
                }

            h = hs[0]

            wind_speed = h.get("wind_speed_ms")
            wind_score = h.get("wind_safety")

            if wind_score is not None:
                if wind_score >= 80:
                    level = "SAFE"
                elif wind_score >= 60:
                    level = "MODERATE"
                elif wind_score >= 40:
                    level = "CAUTION"
                else:
                    level = "UNSAFE"
            else:
                level = "UNKNOWN"

            return {
                "status": "success",
                "mode": qt,
                "zone_id": z,
                "forecast": f,
                "answer": (
                    f"💨 Wind conditions at {safety_zone}: "
                    f"{wind_speed if wind_speed is not None else 'N/A'} m/s. "
                    f"Wind safety: "
                    f"{wind_score if wind_score is not None else 'N/A'}/100 "
                    f"({level})."
                )
            }

    if qt in ["safest", "avoid_zones"]:

        # Get all current safety results in ONE request
        ranking_response = requests.get(
            f"{SAFETY_API}/safety/ranking",
            timeout=10
        )

        if ranking_response.status_code != 200:
            return {
                "status": "error",
                "mode": qt,
                "answer": "I couldn't retrieve the current safety ranking."
            }

        ranking_response = ranking_response.json()

        if ranking_response.get("status") != "success":
            return {
                "status": "error",
                "mode": qt,
                "message": ranking_response.get(
                    "message",
                    "Unable to retrieve safety ranking."
                )
            }

        rows = ranking_response.get("zones", [])

        # Fishing-zone safety questions must only use PFZ zones.
        rows = [
            row for row in rows
            if str(row.get("zone_id", "")).upper().startswith("PFZ")
        ]

        if not rows:
            return {
                "status": "success",
                "mode": qt,
                "zones": [],
                "answer": "No current PFZ safety results are available."
            }

        if qt == "avoid_zones":

            # Avoid HIGH-risk PFZ zones only
            dangerous = [
                row for row in rows
                if row.get("risk_score") is not None
                and row["risk_score"] > 0.70
            ]

            dangerous = dangerous[:10]

            if not dangerous:
                return {
                    "status": "success",
                    "mode": qt,
                    "zones": [],
                    "answer": (
                        "No fishing zones are currently classified "
                        "as high risk."
                    )
                }

            answer_lines = [
                "⚠️ High-risk fishing zones to avoid:"
            ]

            for i, row in enumerate(dangerous, 1):
                answer_lines.append(
                    f"{i}. {row['zone_id']} — "
                    f"{row.get('risk_level', 'HIGH')} risk "
                    f"(risk score {row['risk_score']:.2f})"
                )

            answer_lines.append(
                "Conditions can change as new marine and weather "
                "observations become available."
            )

            return {
                "status": "success",
                "mode": qt,
                "zones": dangerous,
                "answer": "\n".join(answer_lines)
            }

        # SAFEST PFZ
        safest_zone = min(
            rows,
            key=lambda x: (
                x["risk_score"]
                if x.get("risk_score") is not None
                else float("inf")
            )
        )

        return {
            "status": "success",
            "mode": qt,
            "recommended_zone": safest_zone["zone_id"],
            "zones": rows[:10],
            "answer": (
                f"🛟 The safest current fishing zone is "
                f"{safest_zone['zone_id']} with a "
                f"{safest_zone.get('risk_level', 'UNKNOWN')} risk level "
                f"(risk score {safest_zone['risk_score']:.2f}). "
                f"This ranking considers current PFZ safety conditions."
            )
        }

    if qt in ["nearby_zones", "nearby_ranking", "closest"]:
        if p["latitude"] is None or p["longitude"] is None:
            return {
                "status": "needs_location",
                "parsed": p,
                "answer": "Please allow location access so I can find the nearest fishing zone."
            }

        x = df().copy()

        # Prefer actual PFZ observations when the label is available
        if "pfz_label" in x.columns:
            pfz = x[x["pfz_label"] == 1]
            if not pfz.empty:
                x = pfz

        # Calculate distance from user's location
        x["distance_km"] = [
            hav(
                p["latitude"],
                p["longitude"],
                float(lat),
                float(lon)
            )
            for lat, lon in zip(x.latitude, x.longitude)
        ]

        if qt == "nearby_zones":
            x = x[x["distance_km"] <= (p["distance_km"] or 30)]
        else:
            x = x.sort_values("distance_km").head(20)

        out = [
            {
                "zone_id": str(row["zone_id"]),
                "distance_km": round(float(row["distance_km"]), 2)
            }
            for _, row in x.iterrows()
        ]

        if qt == "nearby_ranking":
            for r in out:
                r["fishing_score"] = ocean(r["zone_id"]).get("fishing_score")

            out.sort(
                key=lambda r: r["fishing_score"] or 0,
                reverse=True
            )
            
        if qt == "nearby_ranking":

            if not out:
                return {
                    "status": "success",
                    "mode": qt,
                    "zones": [],
                    "answer": (
                        "I couldn't find any fishing zones "
                        "near your current location."
                    )
                }

            zone_list = []

            for i, r in enumerate(out[:10], start=1):

                score = r.get("fishing_score")

                if score is None:
                    zone_list.append(
                        f"{i}. {r['zone_id']} — "
                        f"{r['distance_km']:.1f} km "
                        f"(fishing score unavailable)"
                    )
                else:
                    zone_list.append(
                        f"{i}. {r['zone_id']} — "
                        f"HSI {score:.2f}, "
                        f"{r['distance_km']:.1f} km away"
                    )

            answer = (
                "Here are the nearby fishing zones ranked by "
                "current fishing potential:\n"
                + "\n".join(zone_list)
            )

            return {
                "status": "success",
                "mode": qt,
                "zones": out,
                "answer": answer
            }

        if qt == "closest":
            if out:
                return {
                    "status": "success",
                    "mode": "closest",
                    "recommended_zone": out[0]["zone_id"],
                    "distance_km": out[0]["distance_km"],
                    "zones": out,
                    "answer": (
                        f"The closest fishing zone to your location is "
                        f"{out[0]['zone_id']}, approximately "
                        f"{out[0]['distance_km']} km away."
                    )
                }

            return {
                "status": "success",
                "mode": "closest",
                "zones": [],
                "answer": "I couldn't find any nearby fishing zones."
            }

        if qt == "nearby_zones":

            if out:
                zone_list = ", ".join(
                    f"{r['zone_id']} ({r['distance_km']:.1f} km)"
                    for r in out[:10]
                )

                answer = (
                    f"Found {len(out)} fishing zones within "
                    f"{p['distance_km'] or 30:g} km of your location: "
                    f"{zone_list}."
                )
            else:
                # Find the actual nearest zone to provide a useful fallback
                nearest_row = nearest(
                    p["latitude"],
                    p["longitude"]
                )

                nearest_id = str(nearest_row.zone_id)

                nearest_distance = hav(
                    p["latitude"],
                    p["longitude"],
                    float(nearest_row.latitude),
                    float(nearest_row.longitude)
                )

                answer = (
                    f"There are no PFZ observations within "
                    f"{p['distance_km'] or 30:g} km of your location. "
                    f"The nearest fishing zone is {nearest_id}, "
                    f"approximately {nearest_distance:.2f} km away."
                )

            return {
                "status": "success",
                "mode": qt,
                "zones": out,
                "answer": answer
            }

    # ---------------------------------------------------------
    # ROUTE-SPECIFIC RANKINGS
    # ---------------------------------------------------------
    if qt in [
        "least_fuel",
        "lowest_travel_time",
        "shortest_route",
        "safest_route"
    ] and not z:

        try:
            x = routing_df().copy()

            x = x[x["zone_id"].notna()].copy()
            x["zone_id"] = x["zone_id"].astype(str)

            if qt == "least_fuel":
                sort_column = "fuel_l_proxy"
                ascending = True

            elif qt == "lowest_travel_time":
                sort_column = "travel_time_hr"
                ascending = True

            elif qt == "shortest_route":
                sort_column = "distance_km"
                ascending = True

            else:
                sort_column = "adjusted_final_route_score"
                ascending = False

            x[sort_column] = pd.to_numeric(
                x[sort_column],
                errors="coerce"
            )

            x = x[x[sort_column].notna()]
            x = x.sort_values(
                sort_column,
                ascending=ascending
            )

            top = x.head(10)

            ranking = []

            for _, row in top.iterrows():
                ranking.append({
                    "zone_id": str(row["zone_id"]),
                    "distance_km": round(float(row["distance_km"]), 1),
                    "travel_time_hr": round(float(row["travel_time_hr"]), 2),
                    "fuel_l": round(float(row["fuel_l_proxy"]), 1),
                    "route_score": (
                        round(float(row["adjusted_final_route_score"]), 4)
                        if pd.notna(row.get("adjusted_final_route_score"))
                        else None
                    )
                })

            if not ranking:
                return {
                    "status": "success",
                    "mode": qt,
                    "ranking": [],
                    "answer": "No route results are available."
                }

            best = ranking[0]

            if qt == "lowest_travel_time":

                minutes = best["travel_time_hr"] * 60

                answer = (
                    f"Fastest route\n\n"
                    f"{best['zone_id']} has the lowest estimated "
                    f"travel time at {minutes:.0f} minutes "
                    f"({best['travel_time_hr']:.2f} hours).\n\n"
                    f"• Distance: {best['distance_km']:.1f} km\n"
                    f"• Fuel required: {best['fuel_l']:.1f} L"
                )

            elif qt == "least_fuel":

                answer = (
                    f"Most fuel-efficient route\n\n"
                    f"{best['zone_id']} requires the least estimated "
                    f"fuel: {best['fuel_l']:.1f} L.\n\n"
                    f"• Distance: {best['distance_km']:.1f} km\n"
                    f"• Travel time: "
                    f"{best['travel_time_hr']:.2f} hours"
                )

            elif qt == "shortest_route":

                minutes = best["travel_time_hr"] * 60

                answer = (
                    f"Shortest route\n\n"
                    f"{best['zone_id']} has the shortest route at "
                    f"{best['distance_km']:.1f} km.\n\n"
                    f"• Travel time: {minutes:.0f} minutes\n"
                    f"• Fuel required: {best['fuel_l']:.1f} L"
                )

            else:
                answer = (
                    f"Safest route\n\n"
                    f"{best['zone_id']} has the highest route "
                    f"score: {best['route_score']}.\n\n"
                    f"• Distance: {best['distance_km']:.1f} km\n"
                    f"• Travel time: "
                    f"{best['travel_time_hr']:.2f} hours\n"
                    f"• Fuel required: {best['fuel_l']:.1f} L"
                )

            return {"status": "success", "mode": qt, "recommended_zone": best["zone_id"], "ranking": ranking, "answer": answer}

        except Exception as e:
            return {"status": "error", "mode": qt, "message": str(e), "answer": "I couldn't calculate the route ranking."}

    if z and qt in [
        "distance",
        "travel_time",
        "fuel",
        "fuel_feasibility",
        "shortest_route",
        "safest_route",
    ]:

        # Harbour-to-zone distance requires the user's harbour coordinates.
        if qt == "distance" and (
            "harbour" in q.lower() or "harbor" in q.lower()
        ):
            return {
                "status": "needs_location",
                "mode": qt,
                "parsed": p,
                "answer": (
                    "I need your harbour latitude and longitude "
                    "to calculate the harbour-to-zone distance. "
                    "The routing dataset currently provides the "
                    "PFZ route distance, not your harbour distance."
                ),
            }

        # Get routing information for the requested zone.
        r = route(z)

        if r.get("status") != "success":
            return {
                "status": "error",
                "parsed": p,
                "message": r.get("message", "Routing Agent failed."),
            }

        metrics = r.get("route_metrics", {})

        distance_km = metrics.get("distance_km")
        travel_time_hr = metrics.get("travel_time_hr")
        fuel_l = metrics.get("fuel_l")

        # Make sure required routing values exist.
        if (
            distance_km is None
            or travel_time_hr is None
            or fuel_l is None
        ):
            return {
                "status": "error",
                "mode": qt,
                "zone_id": z,
                "route": r,
                "answer": (
                    f"⚠️ Routing data for {z} is incomplete. "
                    "Distance, travel time, or fuel information "
                    "is unavailable."
                ),
            }

        # ---------------------------------------------------------
        # DISTANCE
        # ---------------------------------------------------------
        if qt == "distance":

            ans = (
                f"Distance to {z}\n\n"
                f"• Route distance: {float(distance_km):.1f} km"
            )

        # ---------------------------------------------------------
        # TRAVEL TIME
        # ---------------------------------------------------------
        elif qt == "travel_time":

            minutes = float(travel_time_hr) * 60

            ans = (
                f"Estimated travel time to {z}\n\n"
                f"• Distance: {float(distance_km):.1f} km\n"
                f"• Travel time: {minutes:.0f} minutes "
                f"({float(travel_time_hr):.1f} hours)"
            )

        # ---------------------------------------------------------
        # FUEL
        # ---------------------------------------------------------
        elif qt == "fuel":

            ans = (
                f"Fuel required to reach {z}\n\n"
                f"• Distance: {float(distance_km):.1f} km\n"
                f"• Estimated fuel: {float(fuel_l):.1f} L"
            )

        # ---------------------------------------------------------
        # FUEL FEASIBILITY
        # ---------------------------------------------------------
        elif qt == "fuel_feasibility":

            have = p.get("fuel_litres")

            if have is None:
                ans = (
                    f"{z} requires approximately "
                    f"{float(fuel_l):.1f} L of fuel.\n\n"
                    f"Tell me how much fuel you have onboard "
                    f"and I can check whether it is sufficient."
                )

            elif float(fuel_l) <= float(have):

                remaining = float(have) - float(fuel_l)

                ans = (
                    f"Fuel check for {z}\n\n"
                    f"• Required: {float(fuel_l):.1f} L\n"
                    f"• Available: {float(have):.1f} L\n"
                    f"• Remaining: {remaining:.1f} L\n\n"
                    f"✅ You have enough fuel for the estimated route."
                )

            else:

                shortage = float(fuel_l) - float(have)

                ans = (
                    f"Fuel check for {z}\n\n"
                    f"• Required: {float(fuel_l):.1f} L\n"
                    f"• Available: {float(have):.1f} L\n"
                    f"• Shortage: {shortage:.1f} L\n\n"
                    f"⚠️ You do not have enough fuel for the "
                    f"estimated route."
                )

        # ---------------------------------------------------------
        # SHORTEST ROUTE
        # ---------------------------------------------------------
        elif qt == "shortest_route":

            minutes = float(travel_time_hr) * 60

            ans = (
                f"Route to {z}\n\n"
                f"• Distance: {float(distance_km):.1f} km\n"
                f"• Travel time: {minutes:.0f} minutes\n"
                f"• Fuel required: {float(fuel_l):.1f} L"
            )

        # ---------------------------------------------------------
        # SAFEST ROUTE
        # ---------------------------------------------------------
        elif qt == "safest_route":

            route_score = r.get("route_score")
            geofence = r.get("geofence_caution", False)
            route_safety = r.get("route_safety_score")

            ans = f"Route safety for {z}\n\n"

            if route_score is not None:
                ans += (
                    f"• Route score: "
                    f"{float(route_score):.2f}\n"
                )

            if route_safety is not None:
                ans += (
                    f"• Route safety score: "
                    f"{float(route_safety):.2f}\n"
                )

            ans += (
                f"• Distance: {float(distance_km):.1f} km\n"
                f"• Travel time: "
                f"{float(travel_time_hr) * 60:.0f} minutes\n"
                f"• Fuel required: {float(fuel_l):.1f} L\n"
                f"• Geofence caution: "
                f"{'Yes ⚠️' if geofence else 'No ✅'}"
            )

        # ---------------------------------------------------------
        # FALLBACK
        # ---------------------------------------------------------
        else:

            ans = (
                f"Route information for {z}\n\n"
                f"• Distance: {float(distance_km):.1f} km\n"
                f"• Travel time: "
                f"{float(travel_time_hr) * 60:.0f} minutes\n"
                f"• Fuel required: {float(fuel_l):.1f} L"
            )

        return {
            "status": "success",
            "mode": qt,
            "zone_id": z,
            "route": r,
            "answer": ans,
        }

    # cyclone_risk or general safety/ocean with no zone — use nearest zone if location available
    if (qt in ["cyclone_risk", "cyclone_scenario"] or (qt == "general" and ("safety" in p["intents"] or "fishing" in p["intents"] or "ocean" in p["intents"]))):
        # General ocean conditions
        if "ocean" in p["intents"] and target_z:
            o = ocean(target_z)

            return {
                "status": "success",
                "mode": "general_ocean",
                "zone_id": target_z,
                "ocean": o,
                "answer": (
                    f"Ocean conditions near your location, using nearest zone {target_z}: "
                    f"SST {o.get('sst_c', 'N/A')}°C, "
                    f"chlorophyll {o.get('chlorophyll_mg_m3', 'N/A')} mg/m³, "
                    f"and current speed {o.get('current_speed_ms', 'N/A')} m/s."
                )
            }

        if qt == "cyclone_scenario":
            return {"status":"success","mode":qt,"parsed":p,
                    "answer":"A cyclone warning would increase wind, wave and cyclone risk and can move the safety assessment toward CAUTION or UNSAFE. ORCA requires the warning’s forecast inputs to calculate the new numerical score; it will not invent those values."}

        if qt == "cyclone_risk" and target_z:
            s = safety(target_z)

            evidence = s.get("evidence", {})

            risk_level = s.get("risk_level", "UNKNOWN")
            risk_score = s.get("risk_score", "N/A")

            cyclone_distance = evidence.get("cyclone_distance_km")
            cyclone_wind = evidence.get("cyclone_wind_kt")
            wind_speed = evidence.get("wind_speed_ms")
            wave_height = evidence.get("wave_height_m")

            answer = (
                f"Cyclone / Storm Risk near {target_z}\n\n"
                f"Risk level: {risk_level}\n"
                f"Risk score: {risk_score}\n\n"
                f"• Cyclone distance: "
                f"{round(cyclone_distance, 1) if cyclone_distance is not None else 'N/A'} km\n"
                f"• Cyclone wind: "
                f"{round(cyclone_wind, 1) if cyclone_wind is not None else 'N/A'} kt\n"
                f"• Wind speed: "
                f"{round(wind_speed, 2) if wind_speed is not None else 'N/A'} m/s\n"
                f"• Wave height: "
                f"{round(wave_height, 2) if wave_height is not None else 'N/A'} m"
            )

            return {"status": "success", "mode": qt, "zone_id": target_z, "safety": s, "answer": answer}

        # General fishing query — return top fishing zones
        if "fishing" in p["intents"]:
            rows = direct_ocean_ranking("highest_fishing")
            rows.sort(key=lambda r: r["fishing_score"], reverse=True)
            top = rows[:5]
            if top:
                zone_list = ", ".join(f"{r['zone_id']} (score {r['fishing_score']:.2f})" for r in top)
                zone_list = "\n".join(
                    f"{i}. {r['zone_id']} — HSI {r['fishing_score']:.2f}"
                    for i, r in enumerate(top, 1)
                )

                return {
                    "status": "success",
                    "mode": "highest_fishing",
                    "ranking": top,
                    "answer": (
                        "**Top fishing zones**\n\n"
                        + zone_list
                    )
                }

        # General safety query
        if "safety" in p["intents"] and target_z:
            s = safety(target_z)
            return {"status":"success","mode":"general_safety","zone_id":target_z,"safety":s,
                    "answer":f"Safety at nearest zone {target_z}: {s.get('risk_level','UNKNOWN')} risk (score {s.get('risk_score','N/A')}). {s.get('message','')}"}

    if qt == "route_geometry":
        return {"status":"needs_location","mode":qt,"parsed":p,
                "answer":"Harbour-to-zone geometry requires the harbour latitude and longitude. Provide the harbour coordinates to generate the route."}

    # Catch-all: return a helpful fallback
    return {"status":"success","mode":"general","parsed":p,
            "answer":"I can help with fishing zones, ocean conditions, safety reports and route estimates. Try asking: 'Where are the best fishing zones?', 'Is it safe near PFZ0319?', 'How far is PFZ0001?', or 'Is there any cyclone risk?'"}

@app.get("/api/fishing-zones")
def get_fishing_zones(
    latitude: float | None = None,
    longitude: float | None = None
):
    """Return PFZ zone data for the frontend map, including safety scores."""

    try:
        x = df().copy()

        if "pfz_label" in x.columns and not x[x.pfz_label == 1].empty:
            x = x[x.pfz_label == 1]

        # ---------------------------------------------------------
        # GET SAFETY FOR ALL PFZ ZONES IN ONE REQUEST
        # ---------------------------------------------------------
        try:
            safety_request = requests.get(
                f"{SAFETY_API}/safety/ranking",
                timeout=15
            )

            if safety_request.status_code == 200:
                safety_response = safety_request.json()
            else:
                safety_response = {
                    "status": "error",
                    "message": safety_request.text
                }

        except Exception as e:
            safety_response = {
                "status": "error",
                "message": str(e)
            }

        safety_by_zone = {}

        if safety_response.get("status") == "success":
            for item in safety_response.get("zones", []):
                zone_id = str(item.get("zone_id", "")).upper()

                safety_score = item.get("safety_score")

                if safety_score is not None:
                    safety_score = round(
                        float(safety_score) * 100,
                        1
                    )

                safety_by_zone[zone_id] = safety_score

        # ---------------------------------------------------------
        # FISHING SCORE HELPERS
        # ---------------------------------------------------------
        def norm_chl(v):
            return max(
                0,
                min(
                    1,
                    (v - 0.05) / (0.50 - 0.05)
                )
            )

        def sst_score(v):
            return max(
                0,
                1 - abs(v - 28) / 5
            )

        # ---------------------------------------------------------
        # BUILD ZONE RESPONSE
        # ---------------------------------------------------------
        zones_response = []

        for _, r in x.iterrows():

            chl = pd.to_numeric(
                r.get("chlorophyll_mean"),
                errors="coerce"
            )

            ss = pd.to_numeric(
                r.get("sst_c"),
                errors="coerce"
            )

            cur = pd.to_numeric(
                r.get("current_speed_ms"),
                errors="coerce"
            )

            components = []

            if pd.notna(chl):
                components.append(
                    (
                        "chlorophyll",
                        norm_chl(float(chl)),
                        0.40
                    )
                )

            if pd.notna(ss):
                components.append(
                    (
                        "sst",
                        sst_score(float(ss)),
                        0.30
                    )
                )

            if pd.notna(cur):
                components.append(
                    (
                        "current",
                        max(
                            0,
                            min(
                                1,
                                1 - abs(float(cur) - 0.5) / 0.5
                            )
                        ),
                        0.30
                    )
                )

            fishing_score = (
                sum(
                    value * weight
                    for _, value, weight in components
                )
                / sum(
                    weight
                    for _, value, weight in components
                )
                if components
                else 0
            )

            if fishing_score >= 0.7:
                potential = "High"
            elif fishing_score >= 0.4:
                potential = "Medium"
            else:
                potential = "Low"

            confidence = (
                len(components) / 3
                if components
                else 0
            )

            zone_id = str(r.zone_id)

            safety_score = safety_by_zone.get(
                zone_id.upper()
            )

            zones_response.append({
                "zone_id": zone_id,
                "latitude": float(r.latitude),
                "longitude": float(r.longitude),
                "hsi": round(fishing_score, 2),
                "potential": potential,
                "recommended": False,
                "sst_c": (
                    float(ss)
                    if pd.notna(ss)
                    else None
                ),
                "chlorophyll_mg_m3": (
                    float(chl)
                    if pd.notna(chl)
                    else None
                ),
                "safety_score": safety_by_zone.get(str(r.zone_id).upper()),
                "confidence": round(confidence, 2),
                "fishing_score": round(fishing_score, 4)
            })

        # ---------------------------------------------------------
        # RECOMMEND BEST FISHING ZONE
        # ---------------------------------------------------------
        if zones_response:
            zones_response.sort(
                key=lambda z: z["fishing_score"],
                reverse=True
            )

            zones_response[0]["recommended"] = True

            recommended_zone_id = (
                zones_response[0]["zone_id"]
            )

        else:
            recommended_zone_id = None

        return {
            "status": "success",
            "zones": zones_response,
            "recommended_zone_id": recommended_zone_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/ocean")
def get_ocean_conditions(latitude: float | None = None, longitude: float | None = None):
    """Get ocean conditions for the frontend dashboard."""
    try:
        # Find nearest zone if coordinates provided
        if latitude is not None and longitude is not None:
            nearest_zone = nearest(latitude, longitude)
            zone_id = str(nearest_zone.zone_id)
        else:
            # Get first available zone as fallback
            zone_id = zones(True)[0] if zones(True) else None
        
        if not zone_id:
            raise HTTPException(status_code=404, detail="No zones available")
        
        # Call Ocean Agent
        ocean_response = ocean(zone_id)
        
        if ocean_response.get("status") != "success":
            raise HTTPException(status_code=500, detail=ocean_response.get("message", "Ocean API error"))
        
        return ocean_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/safety")
def get_safety_conditions(latitude: float | None = None, longitude: float | None = None):
    """Get safety conditions for the frontend dashboard."""
    try:
        # Find nearest zone if coordinates provided
        if latitude is not None and longitude is not None:
            nearest_zone = nearest(latitude, longitude)
            zone_id = str(nearest_zone.zone_id)
        else:
            # Get first available zone as fallback
            zone_id = zones(True)[0] if zones(True) else None
        
        if not zone_id:
            raise HTTPException(status_code=404, detail="No zones available")
        
        # Call Safety Agent
        safety_response = safety(zone_id)
        
        if safety_response.get("status") != "success":
            raise HTTPException(status_code=500, detail=safety_response.get("message", "Safety API error"))
        
        return safety_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/route")
def get_route_info(zone_id: str):
    """Get route information for the frontend dashboard."""
    try:
        # Call Route Agent
        route_response = route(zone_id)
        
        if route_response.get("status") != "success":
            raise HTTPException(status_code=500, detail=route_response.get("message", "Route API error"))
        
        return route_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def evaluate(z):
    """Evaluate a zone by calling all three specialized agents."""
    return ocean(z),safety(z),route(z)

@app.get("/")
def home():
    return {"agent":"Query Agent","status":"running","version":"7.0.0",
            "connected_agents":{"ocean":OCEAN_API,"safety":SAFETY_API,"route":ROUTE_API,"decision":DECISION_API}}
