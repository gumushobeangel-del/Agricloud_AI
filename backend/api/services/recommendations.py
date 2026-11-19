from datetime import date


# Crop-specific planting guidance for Uganda.
# Sources: FAO Uganda Crop Guides, MAAIF Uganda, NARO Uganda.
CROP_GUIDANCE = {
    "maize": {
        "varieties": "LONGE 10H, LONGE 5, NARO 614, or locally certified seed",
        "spacing": "75 cm between rows, 25 cm within rows, 2 seeds per hole thinned to 1",
        "fertilizer": "Apply DAP at planting; top-dress with CAN or urea 4–6 weeks after emergence",
        "rainfall_min_mm": 500,
        "growing_days": "90–120 days to harvest",
        "harvest_signal": "Husk is dry and grain moisture is below 14%",
        "key_pests": "Fall Armyworm, Stalk Borer — scout weekly and report to extension worker",
        "key_diseases": "Grey Leaf Spot, Maize Streak Virus — use certified resistant seed",
    },
    "beans": {
        "varieties": "K132, NABE 4, NABE 15, NABE 16",
        "spacing": "40 cm between rows, 10 cm within rows, 2 seeds per hole",
        "fertilizer": "Apply phosphorus (SSP or TSP) at planting; avoid excess nitrogen",
        "rainfall_min_mm": 300,
        "growing_days": "60–90 days to harvest",
        "harvest_signal": "90% of pods are yellow-brown and dry",
        "key_pests": "Bean Aphids, Bean Fly — use certified seed and practice crop rotation",
        "key_diseases": "Bean Common Mosaic Virus, Angular Leaf Spot — plant certified disease-free seed",
    },
    "cassava": {
        "varieties": "NASE 14 (CMD resistant), NASE 19, Migyera",
        "spacing": "1 m x 1 m using stem cuttings of 25–30 cm",
        "fertilizer": "Apply NPK at planting on low-fertility soils; mulch heavily",
        "rainfall_min_mm": 250,
        "growing_days": "9–18 months to harvest",
        "harvest_signal": "Leaves yellow and start dropping; roots are firm and starchy",
        "key_pests": "Cassava Mealybug, Green Mite — use certified clean planting material",
        "key_diseases": "Cassava Mosaic Disease (CMD), Cassava Brown Streak Disease (CBSD) — always use CMD-resistant certified cuttings",
    },
    "groundnuts": {
        "varieties": "Serenut 2, Serenut 4R, ICGV 97045",
        "spacing": "45 cm between rows, 15 cm within rows",
        "fertilizer": "Apply gypsum (calcium sulphate) at pegging stage; inoculate seed with Rhizobium",
        "rainfall_min_mm": 400,
        "growing_days": "90–120 days to harvest",
        "harvest_signal": "Inner shell has dark veins; leaves begin to yellow",
        "key_pests": "Groundnut Aphids — monitor and use neem-based biopesticide",
        "key_diseases": "Groundnut Rosette Virus, Early and Late Leaf Spot — plant resistant varieties, use crop rotation",
    },
    "sweet potato": {
        "varieties": "NASPOT 1, NASPOT 10 (orange-fleshed, high vitamin A), Kabode",
        "spacing": "1 m between ridges, 30 cm within rows using vine cuttings of 30 cm",
        "fertilizer": "Apply potassium-rich fertilizer (MOP); organic matter improves yield",
        "rainfall_min_mm": 300,
        "growing_days": "3–5 months to harvest",
        "harvest_signal": "Vines start yellowing; roots are well-formed",
        "key_pests": "Sweet Potato Weevil — use certified clean vines; harvest on time",
        "key_diseases": "Sweet Potato Virus Disease — use certified virus-free planting material",
    },
    "sorghum": {
        "varieties": "Serere 1, NAROSORG 1",
        "spacing": "75 cm between rows, 10 cm within rows",
        "fertilizer": "Apply DAP at planting; sorghum tolerates low-fertility soils better than maize",
        "rainfall_min_mm": 300,
        "growing_days": "90–130 days to harvest",
        "harvest_signal": "Grain is hard and dry; head colour changes from green to straw",
        "key_pests": "Stalk Borer, Shoot Fly — scout early; treat with approved insecticide",
        "key_diseases": "Downy Mildew, Grain Mold — use resistant varieties and ensure good spacing",
    },
    "millet": {
        "varieties": "NAROM 1, SEREMI 2 (finger millet); local pearl millet varieties",
        "spacing": "30–45 cm between rows, 10 cm within rows",
        "fertilizer": "Low fertilizer requirement; apply DAP at planting on poor soils",
        "rainfall_min_mm": 250,
        "growing_days": "75–100 days to harvest",
        "harvest_signal": "Heads turn golden-brown and grain is hard",
        "key_pests": "Quelea birds — use bird scaring; Stalk Borer — scout and treat",
        "key_diseases": "Blast, Downy Mildew — plant resistant varieties",
    },
    "banana": {
        "varieties": "Mbwazirume, Nakitembe, Nfuuka (matooke); Kayinja (beer banana)",
        "spacing": "3 m x 3 m using healthy suckers; plant in 60x60x60 cm pits with topsoil and manure",
        "fertilizer": "Heavy mulching with crop residues; apply potassium-rich fertilizer annually",
        "rainfall_min_mm": 1000,
        "growing_days": "9–14 months to first bunch; plant continuously thereafter",
        "harvest_signal": "Fingers are plump and roundish; bunch stalk begins to bend",
        "key_pests": "Banana Weevil, Nematodes — use clean suckers; remove old mats regularly",
        "key_diseases": "Banana Xanthomonas Wilt (BXW) — immediately remove and bury infected mats; Black Sigatoka — apply approved fungicide",
    },
    "tomato": {
        "varieties": "Rodade, Tengeru 97, Nuru F1",
        "spacing": "60–75 cm between rows, 45–60 cm within rows; transplant at 4–5 weeks from nursery",
        "fertilizer": "Apply NPK at transplanting; use calcium nitrate to prevent blossom end rot",
        "rainfall_min_mm": 400,
        "growing_days": "70–90 days to first harvest from transplanting",
        "harvest_signal": "Fruit turns from green to red; harvest at red-ripe or pink stage for market",
        "key_pests": "Whitefly, Tomato Leafminer — use yellow sticky traps; spray approved insecticide",
        "key_diseases": "Early Blight, Late Blight, Bacterial Wilt — use certified seed, avoid overhead irrigation",
    },
    "coffee": {
        "varieties": "Robusta (Coffea canephora) for lowlands; Arabica (Coffea arabica) for highlands above 1,500 m",
        "spacing": "3 m x 3 m; plant in 45x45x45 cm holes with topsoil and compost",
        "fertilizer": "Apply NPK fertilizer (CAN + phosphorus) annually; mulch heavily",
        "rainfall_min_mm": 1000,
        "growing_days": "2–3 years to first production; harvest at peak red cherry stage",
        "harvest_signal": "Cherries turn bright red; selective picking recommended for quality",
        "key_pests": "Coffee Berry Borer, Antestia Bug — use certified traps and approved sprays",
        "key_diseases": "Coffee Wilt Disease (tracheomycosis) — remove and destroy infected trees; use resistant varieties",
    },
    "rice": {
        "varieties": "NARICA L-19, NARICA L-5, Komboka",
        "spacing": "20 cm between rows, 15 cm within rows; transplant at 21 days from nursery",
        "fertilizer": "Apply DAP at transplanting; top-dress with urea at tillering and panicle initiation",
        "rainfall_min_mm": 1000,
        "growing_days": "100–130 days to harvest",
        "harvest_signal": "80% of panicle is golden-brown; moisture around 20–25%",
        "key_pests": "Stem Borer, Rice Gall Midge — scout and use approved insecticide",
        "key_diseases": "Blast, Bacterial Leaf Blight — use certified resistant varieties",
    },
    "cowpeas": {
        "varieties": "Nakonde, IT97K-499-35, local improved varieties",
        "spacing": "60 cm between rows, 20 cm within rows, 2 seeds per hole",
        "fertilizer": "Low fertilizer need; inoculate with Rhizobium; apply phosphorus at planting",
        "rainfall_min_mm": 300,
        "growing_days": "60–70 days to first harvest (green pods); 90 days for dry grain",
        "harvest_signal": "Pods dry and brown for grain; still green and firm for vegetable use",
        "key_pests": "Pod Borer, Aphids — scout and treat with approved products",
        "key_diseases": "Cowpea Mosaic Virus — plant certified virus-free seed",
    },
}

# Rainfall thresholds for general risk flags (mm over 30-day period).
RAINFALL_LOW_WATCH_MM = 15
RAINFALL_LOW_HIGH_MM = 5
RAINFALL_HIGH_WATCH_MM = 250
RAINFALL_HIGH_HIGH_MM = 350
TEMP_HEAT_WATCH_C = 35
TEMP_HEAT_HIGH_C = 38


def _get_crop_guidance(crop_name: str) -> dict | None:
    """Return guidance dict for crop_name, trying exact then substring match."""
    key = crop_name.strip().casefold()
    if key in CROP_GUIDANCE:
        return CROP_GUIDANCE[key]
    # Substring match
    candidates = [(k, v) for k, v in CROP_GUIDANCE.items() if k in key or key in k]
    if candidates:
        best = max(candidates, key=lambda item: len(item[0]))
        return best[1]
    return None


def build_planting_advice(crop, soil_type, observations, expected_days=30):
    crop_name = crop.strip()
    crop_info = _get_crop_guidance(crop_name)

    basis = [
        "Crop and soil details supplied by the farmer; soil suitability has not been laboratory verified.",
        "Sources: FAO Uganda Crop Guides, MAAIF Uganda, NARO Uganda research recommendations.",
        "Always confirm timing with a local district extension worker before planting.",
    ]
    risks = []

    # --- Climate analysis from real NASA POWER data ---
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
        basis.append(
            f"NASA POWER reported {total:.1f} mm precipitation across {len(rainfall)} observed "
            f"days out of {expected_days} in the retrieved period."
        )
        if len(rainfall) < expected_days:
            risks.append(
                "Precipitation coverage is incomplete; rainfall thresholds were not applied "
                "to avoid interpreting missing days as dry conditions."
            )
        elif total < RAINFALL_LOW_WATCH_MM:
            risks.append(
                f"Very low observed rainfall ({total:.1f} mm in 30 days). Verify local water "
                "availability before planting and consider irrigation or waiting for rains."
            )
            if crop_info and total < (crop_info.get("rainfall_min_mm", 300) * 0.1):
                risks.append(
                    f"{crop_name.title()} requires at least {crop_info['rainfall_min_mm']} mm "
                    "during the growing season — current conditions are likely too dry to plant without irrigation."
                )
        elif total > RAINFALL_HIGH_HIGH_MM:
            risks.append(
                f"Very high observed rainfall ({total:.1f} mm in 30 days). Check field drainage "
                "before planting and inspect for waterlogging and fungal disease pressure."
            )
        elif total > RAINFALL_HIGH_WATCH_MM:
            risks.append(
                f"Above-average rainfall ({total:.1f} mm in 30 days). Check drainage, "
                "especially on clay soils. Elevated risk of fungal diseases."
            )
    else:
        basis.append(
            f"No usable precipitation observations were returned for the {expected_days}-day period; "
            "climate suitability cannot be assessed."
        )
        risks.append(
            "Climate data is unavailable for this period. Consult a local extension worker "
            "before making a planting decision."
        )

    if temperatures:
        mean_temp = sum(temperatures) / len(temperatures)
        peak_temp = max(temperatures)
        basis.append(
            f"NASA POWER mean air temperature across {len(temperatures)} observed days was "
            f"{mean_temp:.1f} °C (peak {peak_temp:.1f} °C)."
        )
        if peak_temp >= TEMP_HEAT_HIGH_C:
            risks.append(
                f"Extreme heat observed ({peak_temp:.1f} °C). Consider heat and moisture stress "
                "on seedlings. Water plants in early morning."
            )
        elif peak_temp >= TEMP_HEAT_WATCH_C:
            risks.append(
                f"High temperatures observed ({peak_temp:.1f} °C). Monitor crops for heat stress "
                "and ensure adequate soil moisture during establishment."
            )

    if soil_type == "unknown":
        risks.append(
            "Soil type is not recorded for this farm. Confirm soil drainage and fertility "
            "with an extension worker before selecting a planting method."
        )

    # --- Build crop-specific guidance ---
    if crop_info:
        guidance_parts = [
            f"For {crop_name}, plant at the onset of reliable rains using certified seed of "
            f"recommended varieties: {crop_info['varieties']}.",
            f"Spacing: {crop_info['spacing']}.",
            f"Fertilization: {crop_info['fertilizer']}.",
            f"Expected duration: {crop_info['growing_days']}.",
            f"Harvest when: {crop_info['harvest_signal']}.",
            f"Key pests to watch: {crop_info['key_pests']}.",
            f"Key diseases to watch: {crop_info['key_diseases']}.",
            "Always use the NASA POWER climate observations below as context — they reflect "
            "recent historical conditions, not a forecast or a yield guarantee.",
        ]
        guidance = " ".join(guidance_parts)
    else:
        guidance = (
            f"For {crop_name}, plant at the onset of reliable rains using certified seed from "
            "a reputable local supplier. Use recommended spacing from your district extension "
            "worker and apply fertilizer according to local soil test results. "
            "The NASA POWER observations below reflect recent historical climate context — "
            "they are not a forecast or a guarantee of crop performance."
        )

    return {
        "crop": crop_name,
        "planting_date": date.today().isoformat(),
        "guidance": guidance,
        "basis": basis,
        "risks": risks,
    }
