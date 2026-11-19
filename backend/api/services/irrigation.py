import math


# FAO crop coefficients (Kc) by growth stage.
# Source: FAO Irrigation and Drainage Paper 56 — Crop Evapotranspiration,
# https://www.fao.org/3/x0490e/x0490e00.htm, adapted for Uganda conditions.
STAGE_COEFFICIENTS = {
    "initial": 0.4,
    "development": 0.8,
    "mid": 1.15,
    "late": 0.75,
}

CROP_COEFFICIENTS = {
    # Cereals
    "maize":         {"initial": 0.3,  "development": 0.7,  "mid": 1.2,  "late": 0.6},
    "sorghum":       {"initial": 0.3,  "development": 0.75, "mid": 1.0,  "late": 0.65},
    "millet":        {"initial": 0.3,  "development": 0.75, "mid": 1.0,  "late": 0.65},
    "rice":          {"initial": 1.05, "development": 1.15, "mid": 1.2,  "late": 0.9},
    "wheat":         {"initial": 0.3,  "development": 0.75, "mid": 1.15, "late": 0.4},
    # Legumes
    "beans":         {"initial": 0.4,  "development": 0.75, "mid": 1.15, "late": 0.35},
    "cowpeas":       {"initial": 0.4,  "development": 0.75, "mid": 1.05, "late": 0.5},
    "groundnuts":    {"initial": 0.45, "development": 0.75, "mid": 1.05, "late": 0.7},
    "soybeans":      {"initial": 0.4,  "development": 0.8,  "mid": 1.15, "late": 0.5},
    "peas":          {"initial": 0.5,  "development": 0.75, "mid": 1.15, "late": 1.1},
    # Root and tuber crops
    "cassava":       {"initial": 0.3,  "development": 0.8,  "mid": 0.8,  "late": 0.5},
    "sweet potato":  {"initial": 0.5,  "development": 0.8,  "mid": 1.15, "late": 0.65},
    "potato":        {"initial": 0.5,  "development": 0.75, "mid": 1.15, "late": 0.75},
    "yam":           {"initial": 0.5,  "development": 0.75, "mid": 1.0,  "late": 0.75},
    # Fruit crops
    "banana":        {"initial": 0.5,  "development": 1.0,  "mid": 1.1,  "late": 0.9},
    "tomato":        {"initial": 0.6,  "development": 1.15, "mid": 1.15, "late": 0.8},
    "watermelon":    {"initial": 0.4,  "development": 0.75, "mid": 1.0,  "late": 0.75},
    "pineapple":     {"initial": 0.5,  "development": 0.5,  "mid": 0.5,  "late": 0.5},
    "mango":         {"initial": 1.0,  "development": 1.0,  "mid": 0.85, "late": 0.85},
    "passion fruit": {"initial": 0.9,  "development": 1.0,  "mid": 1.0,  "late": 0.85},
    # Vegetables
    "cabbage":       {"initial": 0.7,  "development": 0.75, "mid": 1.05, "late": 0.9},
    "onion":         {"initial": 0.7,  "development": 0.75, "mid": 1.05, "late": 0.75},
    "eggplant":      {"initial": 0.6,  "development": 0.75, "mid": 1.15, "late": 0.8},
    "pepper":        {"initial": 0.6,  "development": 0.75, "mid": 1.15, "late": 0.8},
    "spinach":       {"initial": 0.7,  "development": 0.75, "mid": 1.0,  "late": 0.95},
    # Cash crops
    "coffee":        {"initial": 0.9,  "development": 1.0,  "mid": 1.0,  "late": 0.95},
    "tea":           {"initial": 1.0,  "development": 1.1,  "mid": 1.1,  "late": 1.1},
    "sugarcane":     {"initial": 0.4,  "development": 1.0,  "mid": 1.25, "late": 0.75},
    "sunflower":     {"initial": 0.35, "development": 0.75, "mid": 1.15, "late": 0.35},
    "cotton":        {"initial": 0.45, "development": 0.75, "mid": 1.15, "late": 0.7},
}

# Irrigation trigger depth (mm accumulated net need) before scheduling an event.
# Coarser soils need more frequent watering; finer soils hold more water.
SOIL_TRIGGER_MM = {
    "sandy":    8,
    "loam":     12,
    "clay":     15,
    "volcanic": 12,
    "unknown":  12,
}


def _lookup_coefficients(crop_name: str) -> tuple[dict, bool]:
    """Return (coefficients_dict, used_fallback).

    Tries an exact case-fold match first, then a substring match so that
    e.g. 'sweet potatoes' resolves to 'sweet potato'.
    """
    key = crop_name.strip().casefold()
    if key in CROP_COEFFICIENTS:
        return CROP_COEFFICIENTS[key], False
    # Substring match — longest key wins to avoid false positives
    candidates = [(k, v) for k, v in CROP_COEFFICIENTS.items() if k in key or key in k]
    if candidates:
        best_key, best_val = max(candidates, key=lambda item: len(item[0]))
        return best_val, False
    return STAGE_COEFFICIENTS, True


def build_irrigation_plan(weather, farm, crop, stage, soil_moisture_pct=None):
    observations = weather.get("daily_forecast", [])
    if not observations:
        raise ValueError("The weather provider returned no daily forecast.")

    crop_name = crop.strip()
    coefficients, used_fallback = _lookup_coefficients(crop_name)
    coefficient = coefficients[stage]

    daily = []
    for observation in observations:
        et0 = observation.get("et0_mm")
        rainfall = observation.get("precipitation_sum_mm")
        if (
            not isinstance(et0, (int, float))
            or not math.isfinite(et0)
            or et0 < 0
            or not isinstance(rainfall, (int, float))
            or not math.isfinite(rainfall)
            or rainfall < 0
        ):
            raise ValueError("Reference evapotranspiration and rainfall are required for every forecast day.")
        crop_water_need = et0 * coefficient
        effective_rainfall = rainfall * 0.8
        net_need = max(0, crop_water_need - effective_rainfall)
        daily.append({
            "date": observation["date"],
            "et0_mm": round(et0, 1),
            "crop_water_need_mm": round(crop_water_need, 1),
            "rainfall_mm": round(rainfall, 1),
            "effective_rainfall_mm": round(effective_rainfall, 1),
            "net_irrigation_need_mm": round(net_need, 1),
        })

    trigger = SOIL_TRIGGER_MM.get(farm.soil_type, SOIL_TRIGGER_MM["unknown"])
    if soil_moisture_pct is not None and soil_moisture_pct < 30:
        trigger = min(trigger, 5)

    schedule = []
    accumulated = 0
    for day in daily:
        accumulated += day["net_irrigation_need_mm"]
        if accumulated >= trigger:
            depth = round(accumulated, 1)
            schedule.append({
                "date": day["date"],
                "depth_mm": depth,
                "volume_liters": round(depth * float(farm.size_hectares) * 10000),
            })
            accumulated = 0
    if accumulated >= 5 and daily:
        depth = round(accumulated, 1)
        schedule.append({
            "date": daily[-1]["date"],
            "depth_mm": depth,
            "volume_liters": round(depth * float(farm.size_hectares) * 10000),
        })

    total_crop_need = sum(day["crop_water_need_mm"] for day in daily)
    total_effective_rainfall = sum(day["effective_rainfall_mm"] for day in daily)
    total_net_need = sum(day["net_irrigation_need_mm"] for day in daily)

    coefficient_note = (
        f"FAO Kc={coefficient} (stage: {stage})"
        if not used_fallback
        else f"Generic FAO Kc={coefficient} (stage: {stage}) — no specific coefficient found for '{crop_name}'; consult an extension worker for a crop-specific value"
    )

    result = {
        "crop": crop_name,
        "stage": stage,
        "crop_coefficient": coefficient,
        "coefficient_note": coefficient_note,
        "used_generic_coefficient": used_fallback,
        "farm_area_hectares": float(farm.size_hectares),
        "soil_type": farm.soil_type,
        "source": weather.get("source", "Open-Meteo"),
        "daily": daily,
        "schedule": schedule,
        "totals": {
            "crop_water_need_mm": round(total_crop_need, 1),
            "effective_rainfall_mm": round(total_effective_rainfall, 1),
            "net_irrigation_need_mm": round(total_net_need, 1),
            "net_irrigation_volume_liters": round(total_net_need * float(farm.size_hectares) * 10000),
        },
        "methodology": (
            "Seven-day estimate using Open-Meteo modelled FAO reference evapotranspiration (ET₀), "
            f"{coefficient_note}, and 80% effective rainfall factor. "
            "Scheduling triggers are soil-texture guides (FAO Paper 56); local field measurements "
            "and extension advice should take precedence over these estimates."
        ),
    }

    if soil_moisture_pct is not None:
        result["soil_moisture_pct"] = soil_moisture_pct
        result["soil_moisture_status"] = (
            "low" if soil_moisture_pct < 30 else "moderate" if soil_moisture_pct < 60 else "adequate"
        )
        result["soil_moisture_note"] = (
            "Farmer-entered estimate, not a sensor reading. A low estimate lowers the schedule "
            "trigger for closer field checks; it does not change calculated water volumes."
        )
    return result
