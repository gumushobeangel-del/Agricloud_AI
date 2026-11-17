from datetime import date


def build_planting_advice(crop, soil_type, observations, expected_days=30):
    crop_name = crop.strip()
    basis = [
        "Crop and soil details supplied by the farmer; soil suitability has not been laboratory verified.",
        "Advice is general, rules-based guidance and should be checked with a local extension worker.",
    ]
    risks = []
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
    if rainfall:
        total = sum(rainfall)
        basis.append(f"NASA POWER reported {total:.1f} mm precipitation across {len(rainfall)} observed days out of {expected_days} in the retrieved period.")
        if len(rainfall) < expected_days:
            risks.append("Precipitation coverage is incomplete; rainfall thresholds were not applied to avoid interpreting missing days as dry conditions.")
        elif total < 15:
            risks.append("Low observed rainfall in the selected period; verify local rainfall and water availability before planting.")
        elif total > 250:
            risks.append("High observed rainfall in the selected period; check drainage and local flood conditions.")
    else:
        basis.append(f"No usable precipitation observations were returned for the {expected_days}-day period; climate suitability cannot be assessed.")
        risks.append("Climate data is unavailable for this period. Consult a local extension worker before making a planting decision.")
    if temperatures:
        mean_temp = sum(temperatures) / len(temperatures)
        basis.append(f"NASA POWER mean air temperature across {len(temperatures)} observed days was {mean_temp:.1f} °C.")
        if max(temperatures) >= 35:
            risks.append("High-temperature observations occurred in the selected period; consider heat and moisture stress.")
    if soil_type == "unknown":
        risks.append("Soil type is not recorded; confirm soil drainage and fertility before selecting a planting method.")
    guidance = (
        f"For {crop_name}, use current local seasonal forecasts and district extension guidance to choose a planting window. "
        "Prepare seed and land only when moisture is adequate and expected rainfall is established. "
        "The historical NASA observations below are context, not a forecast or a guarantee of crop performance."
    )
    return {"crop": crop_name, "planting_date": date.today().isoformat(), "guidance": guidance, "basis": basis, "risks": risks}
