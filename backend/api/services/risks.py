def identify_climate_risks(observations, expected_days=30):
    rainfall = [
        row["values"]["PRECTOTCORR"]["value"]
        for row in observations
        if "PRECTOTCORR" in row.get("values", {})
    ]
    temperatures = [
        row["values"]["T2M"]["value"]
        for row in observations
        if "T2M" in row.get("values", {})
    ]
    risks = []
    rainfall_complete = len(rainfall) >= expected_days
    if rainfall_complete:
        total = sum(rainfall)
        if total < 15:
            risks.append({
                "type": "low_rainfall",
                "level": "high" if total < 5 else "watch",
                "observed": round(total, 1),
                "unit": "mm",
                "threshold": "30-day total below 15 mm (high below 5 mm)",
                "action": "Check soil moisture and local rainfall. Consider water availability and ask a local extension worker before changing planting plans.",
            })
        elif total > 250:
            risks.append({
                "type": "high_rainfall",
                "level": "high" if total > 350 else "watch",
                "observed": round(total, 1),
                "unit": "mm",
                "threshold": "30-day total above 250 mm (high above 350 mm)",
                "action": "Check field drainage and local flood conditions. Inspect crops after heavy rainfall.",
            })
    temperature_complete = len(temperatures) >= expected_days
    if temperatures:
        peak = max(temperatures)
        if peak >= 35:
            risks.append({
                "type": "high_temperature",
                "level": "high" if peak >= 38 else "watch",
                "observed": round(peak, 1),
                "unit": "°C",
                "threshold": "Observed daily temperature at or above 35 °C (high at or above 38 °C)",
                "action": "Check crops for heat and moisture stress and confirm local conditions with an extension worker.",
            })
    return {
        "risks": risks,
        "screening_available": rainfall_complete or temperature_complete,
        "coverage": {
            "expected_days": expected_days,
            "rainfall_observations": len(rainfall),
            "temperature_observations": len(temperatures),
        },
    }
