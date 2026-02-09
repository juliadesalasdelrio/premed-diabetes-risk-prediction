import numpy as np
import pandas as pd
import pickle

# =========================
# LOAD ASSETS
# =========================

with open("modelo8.pkl", "rb") as f:
    modelo8 = pickle.load(f)

with open("encoders.pkl", "rb") as f:
    label_encoders = pickle.load(f)

with open("features.pkl", "rb") as f:
    FEATURES = pickle.load(f)

# =========================
# INPUT PREPARATION
# =========================

def prepare_input(user: dict) -> pd.DataFrame:
    """
    user: dict con inputs del usuario (valores naturales)
    devuelve: DataFrame con FEATURES listas para el modelo
    """

    pl = pd.DataFrame([user])

    # =========================
    # 1. Encoding categóricas
    # =========================
    for col, le in label_encoders.items():
        pl[col] = pl[col].astype(str)

        if "Unknown" not in le.classes_:
            le.classes_ = np.append(le.classes_, "Unknown")

        pl[col] = pl[col].apply(lambda x: x if x in le.classes_ else "Unknown")
        pl[col + "_encoded"] = le.transform(pl[col])

    # =========================
    # 2. Feature engineering
    # =========================

    pl["age_group"] = pd.cut(
        pl["age"],
        bins=[0, 35, 50, 65, 100],
        labels=[1, 2, 3, 4]
    ).astype(int)

    pl["poor_diet"] = (pl["diet_score"] <= 4).astype(int)

    pl["non_optimal_sleep"] = (
        (pl["sleep_hours_per_day"] < 6) |
        (pl["sleep_hours_per_day"] > 8)
    ).astype(int)

    pl["overweight_or_obese"] = (pl["bmi"] >= 25).astype(int)

    pl["high_screen_and_sedentary"] = (
        (pl["screen_time_hours_per_day"] > 6) &
        (pl["physical_activity_minutes_per_week"] < 150)
    ).astype(int)

    
    pl["glucose_group"] = pd.cut(
        pl["glucose_fasting"],
        bins=[0, 100, 126, 300],
        labels=[0, 1, 2]
    ).astype(int)

    # =========================
    # 3. Interacciones
    # =========================
    pl["age_group*family_history_diabetes"] = (
        pl["age_group"] * pl["family_history_diabetes"]
    )

    pl["overweight_or_obese*non_optimal_sleep"] = (
        pl["overweight_or_obese"] * pl["non_optimal_sleep"]
    )

    pl["physical_activity_per_week/screen_time_hours"] = (
        pl["physical_activity_minutes_per_week"] /
        (pl["screen_time_hours_per_day"] + 1e-6)
    )

    pl["alcohol/diet_score"] = (
        pl["alcohol_consumption_per_week"] /
        (pl["diet_score"] + 1e-6)
    )

    # =========================
    # 4. Selección final
    # =========================
    X = pl.reindex(columns=FEATURES)

    return X

# =========================
# PREDICTION + INTERPRETATION
# =========================

def predict_risk_with_explanation_and_action(user_input: dict) -> dict:
    X = prepare_input(user_input)

    prob = modelo8.predict_proba(X)[0, 1]

    if prob < 0.30:
        level = "Low"
    elif prob < 0.60:
        level = "Medium"
    else:
        level = "High"

    # Drivers
    drivers = []

    # Glucose
    if user_input["glucose_fasting"] < 100:
        drivers.append(
            "Your fasting blood sugar is currently within a healthy range, which helps protect you from diabetes."
        )
    elif user_input["glucose_fasting"] < 126:
        drivers.append(
            "Your blood sugar levels are slightly elevated. This is an early signal and a good opportunity to act preventively."
        )
    else:
        drivers.append(
            "Your blood sugar levels are high and are significantly increasing your diabetes risk."
        )
    
    # Physical activity
    if user_input["physical_activity_minutes_per_week"] >= 150:
        drivers.append(
            "Your level of physical activity is a strong protective factor for your metabolic health."
        )
    elif user_input["physical_activity_minutes_per_week"] >= 60:
        drivers.append(
            "You are somewhat active, but increasing your activity could further reduce your risk."
        )
    else:
        drivers.append(
            "Low levels of physical activity are contributing to a higher diabetes risk."
        )

    # BMI
    if user_input["bmi"] < 25:
        drivers.append(
            "Your body weight is within a healthy range, which supports good insulin sensitivity."
        )
    elif user_input["bmi"] < 30:
        drivers.append(
            "Your weight may be putting some strain on your metabolism, slightly increasing your risk."
        )
    else:
        drivers.append(
            "Excess body weight is a major factor increasing your diabetes risk."
        )

    # Family history
    if user_input["family_history_diabetes"] == 1:
        drivers.append(
            "A family history of diabetes increases your baseline risk, even if your lifestyle is healthy."
        )
    else:
        drivers.append(
            "No family history of diabetes reduces your baseline genetic risk."
        )

    # Sleep
    if user_input["sleep_hours_per_day"] < 6:
        drivers.append(
            "Short sleep duration may negatively affect blood sugar regulation."
        )
    elif user_input["sleep_hours_per_day"] > 9:
        drivers.append(
            "Very long sleep duration can sometimes be associated with metabolic imbalance."
        )
    else:
        drivers.append(
            "Your sleep duration supports healthy metabolic function."
        )



    # Action plan simple
    actions = []

    # Physical activity
    if user_input["physical_activity_minutes_per_week"] < 150:
        actions.append({
            "driver": "Physical activity",
            "recommendations": [
                "Gradually work towards at least 150 minutes of moderate activity per week.",
                "Even short daily walks can significantly improve insulin sensitivity."
            ]
        })
    else:
        actions.append({
            "driver": "Physical activity",
            "recommendations": [
                "Maintain your current activity level to protect your long-term metabolic health.",
                "Including strength training can provide additional benefits."
            ]
        })

    # Blood sugar / diet
    if user_input["glucose_fasting"] >= 100:
        actions.append({
            "driver": "Blood sugar & nutrition",
            "recommendations": [
                "Limit refined carbohydrates and sugary foods.",
                "Prioritise fibre-rich meals with vegetables, legumes and whole grains. Protein can help by supporting muscle and keeping you satiated.",
                "Regular monitoring can help track improvements over time."
            ]
        })
    else:
        actions.append({
            "driver": "Nutrition",
            "recommendations": [
                "Continue with balanced meals to maintain healthy blood sugar levels.",
                "Focus on consistency rather than restriction.",
                "Protein can help by supporting muscle and keeping you satiated."
            ]
        })

    # Weight
    if user_input["bmi"] >= 25:
        actions.append({
            "driver": "Weight management",
            "recommendations": [
                "Even modest weight loss can significantly reduce diabetes risk.",
                "Focus on sustainable habits rather than rapid changes."
            ]
        })

    # Sleep
    if user_input["sleep_hours_per_day"] < 6 or user_input["sleep_hours_per_day"] > 9:
        actions.append({
            "driver": "Sleep",
            "recommendations": [
                "Aim for 7–8 hours of sleep per night.",
                "Regular sleep schedules support blood sugar regulation."
            ]
        })

    return {
        "risk_level": level,
        "risk_probability": round(float(prob), 3),
        "key_drivers": drivers,
        "action_plan": actions
    }


    return {
        "risk_level": level,
        "risk_probability": round(float(prob), 3),
        "key_drivers": drivers,
        "action_plan": actions
    }
