import numpy as np
import pandas as pd
import pickle
import shap

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
# SHAP EXPLAINER (global)
# =========================

explainer = shap.TreeExplainer(modelo8)

# =========================
# INPUT PREPARATION
# =========================

def explain_prediction(X: pd.DataFrame) -> pd.DataFrame:
    shap_values = explainer.shap_values(X)

    # Caso binario
    if isinstance(shap_values, list):
        impacts = shap_values[1][0]
    else:
        impacts = shap_values[0]

    shap_df = pd.DataFrame({
        "feature": X.columns,
        "impact": impacts
    })

    shap_df["abs_impact"] = shap_df["impact"].abs()
    shap_df = shap_df.sort_values("abs_impact", ascending=False)

    return shap_df

FEATURE_TO_DRIVER = {
    # Glucosa
    "glucose_fasting": "Blood sugar",
    "glucose_group": "Blood sugar",

    # Actividad física / sedentarismo
    "physical_activity_minutes_per_week": "Physical activity",
    "high_screen_and_sedentary": "Physical activity",
    "physical_activity_per_week/screen_time_hours": "Physical activity",

    # Sueño
    "non_optimal_sleep": "Sleep",

    # Peso
    "overweight_or_obese": "Body weight",
    "overweight_or_obese*non_optimal_sleep": "Body weight",
    "central_obesity": "Body weight",

    # Alimentación
    "poor_diet": "Diet",
    "healthy_diet": "Diet",
    "alcohol_consumption_per_week": "Diet",
    "alcohol/diet_score": "Diet",

    # Factores no modificables
    "family_history_diabetes": "Family history",
    "age_group*family_history_diabetes": "Family history",

    # Cardiovascular
    "hypertension_history": "Blood pressure",
    "ldl_cholesterol": "Cholesterol",
    "heart_rate": "Cardiovascular health",

    # Estilo de vida
    "smoking_status_encoded": "Smoking"
}

def aggregate_shap_by_driver(shap_df):
    shap_df = shap_df.copy()

    shap_df["driver"] = shap_df["feature"].map(FEATURE_TO_DRIVER)
    shap_df = shap_df.dropna(subset=["driver"])

    driver_df = (
        shap_df
        .groupby("driver", as_index=False)["impact"]
        .sum()
        .sort_values(by="impact", key=abs, ascending=False)
    )

    return driver_df

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
    pl["healthy_diet"] = pl['diet_score'].apply(lambda x: 1 if x>6 else 0)

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

    # =========================
    # 4. Selección final
    # =========================
    X = pl.reindex(columns=FEATURES)

    return X

# =========================
# PREDICTION + INTERPRETATION
# =========================

def driver_to_user_message(driver, impact):
    direction = "increasing" if impact > 0 else "reducing"

    MESSAGES = {
        "Blood sugar": "Your blood sugar levels are {} your diabetes risk.",
        "Physical activity": "Your level of physical activity is {} your diabetes risk.",
        "Sleep": "Your sleep patterns are {} your diabetes risk.",
        "Body weight": "Your body weight is {} your diabetes risk.",
        "Diet": "Your diet is {} your diabetes risk.",
        "Family history": "Your family history is {} your diabetes risk.",
        "Blood pressure": "Your blood pressure is {} your diabetes risk.",
        "Cholesterol": "Your cholesterol levels are {} your diabetes risk.",
        "Smoking": "Smoking habits are {} your diabetes risk."
    }

    template = MESSAGES.get(driver, f"{driver} is {{}} your diabetes risk.")
    return template.format(direction)

ACTIONABLE_RECOMMENDATIONS = {
    "Blood sugar": {
        "increase": [
            "Reduce intake of sugary drinks and refined carbohydrates.",
            "Try spacing meals evenly throughout the day to avoid glucose spikes.",
            "Prioritise fibre-rich meals with vegetables, legumes and whole grains. Protein can help by supporting muscle and keeping you satiated.",
            "Consider checking fasting glucose regularly if advised by a professional."
        ],
        "reduce": [
            "Your blood sugar levels are currently well managed. Keep maintaining balanced meals.",
            "Focus on consistency rather than restriction.",
            "Protein can help by supporting muscle and keeping you satiated."
        ]
    },

    "Physical activity": {
        "increase": [
            "Aim for at least 150 minutes of moderate physical activity per week.",
            "Include short walks after meals to improve glucose control.",
            "Try strength training 2 times per week to improve insulin sensitivity."
        ],
        "reduce": [
            "Your activity level is helping protect your long-term metabolic health.. Try to keep this routine consistent.",
            "If you have not yet, remember that including strength training can provide additional benefits."
        ]
    },

    "Sleep": {
        "increase": [
            "Try to maintain a consistent sleep schedule, even on weekends, as this supports blood sugar regulation.",
            "Aim for 7–9 hours of sleep per night.",
            "Avoid screens at least 1 hour before bedtime."
        ],
        "reduce": [
            "Your sleep habits are supporting your metabolic health."
        ]
    },

    "Body weight": {
        "increase": [
            "Even a 5–7% reduction in body weight can significantly reduce diabetes risk.",
            "Focus on gradual changes rather than rapid weight loss.",
            "Pair nutrition changes with regular physical activity."
        ],
        "reduce": [
            "Your current weight is helping you lower your diabetes risk."
        ]
    },

    "Diet": {
        "increase": [
            "Increase intake of vegetables, whole grains, and lean protein.",
            "Limit alcohol consumption to moderate levels.",
            "Try to reduce ultra-processed foods during the week."
        ],
        "reduce": [
            "Your dietary habits are helping lower your risk. Keep this pattern."
        ]
    },

    "Smoking": {
        "increase": [
            "Smoking is a known risk factor for diabetes and cardiovascular disease.",
            "If you smoke, consider seeking support to reduce or quit."
        ],
        "reduce": [
            "Not smoking is helping reduce your diabetes risk."
        ]
    },

    "Blood pressure": {
        "increase": [
            "Monitor blood pressure regularly if possible.",
            "Reduce salt intake and prioritize whole foods.",
            "Regular physical activity can help lower blood pressure."
        ],
        "reduce": [
            "Your blood pressure is not contributing significantly to your risk."
        ]
    },

    "Cholesterol": {
        "increase": [
            "Limit saturated fats and prioritize healthy fats like olive oil or nuts.",
            "Regular exercise can help improve cholesterol levels."
        ],
        "reduce": [
            "Your cholesterol levels are currently protective."
        ]
    },
    "Family history": {
    "increase": [
        "Family history is not something you can change, but healthy habits have an even greater protective effect in your case.",
        "Staying active and maintaining a balanced diet is especially important given your family background.",
        "Regular check-ups can help detect changes early."
    ],
    "reduce": [
        "Your family history plays on your side regarding to this matter! Do not forget that staying active and maintaining a balanced diet is still a key component of a healthy lifestyle."
    ]
}

}


def generate_actionable_recommendations(driver_df, top_n=5):
    recommendations = []

    for _, row in driver_df.head(top_n).iterrows():
        driver = row["driver"]
        impact = row["impact"]
        direction = "increase" if impact > 0 else "reduce"

        recs = ACTIONABLE_RECOMMENDATIONS.get(driver, {}).get(direction, [])

        recommendations.append({
            "driver": driver,
            "impact_direction": direction,
            "recommendations": recs
        })

    return recommendations

def predict_risk_with_explanation_and_action(user_input: dict) -> dict:
    X = prepare_input(user_input)

    prob = modelo8.predict_proba(X)[0, 1]

    if prob < 0.30:
        level = "Low"
    elif prob < 0.60:
        level = "Medium"
    else:
        level = "High"

    shap_df = explain_prediction(X)
    driver_df = aggregate_shap_by_driver(shap_df)

    explanations = [
        driver_to_user_message(row["driver"], row["impact"])
        for _, row in driver_df.head(5).iterrows()
    ]

    actions = generate_actionable_recommendations(driver_df)

    return {
        "risk_level": level,
        "risk_probability": round(float(prob), 3),
        "key_drivers": explanations,
        "action_plan": actions
    }
