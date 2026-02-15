import streamlit as st
import pandas as pd
import os
from model_utils import predict_risk_with_explanation_and_action
import os
import uuid
from datetime import datetime
from PIL import Image


#===============
# USE CASES
#===============

def log_case(user_input, result):

    log_entry = {
        "case_id": str(uuid.uuid4()),
        "timestamp": datetime.now(),

        # Inputs
        **user_input,

        # Output
        "risk_probability": result["risk_probability"],
        "risk_level": result["risk_level"],
    }

    #Key drivers
    for i, driver in enumerate(result["key_drivers"], start=1):
        log_entry[f"key_driver_{i}"] = driver
        log_entry[f"key_driver_{i}_impact"] = driver

    df_log = pd.DataFrame([log_entry])

    df_log.to_csv(
        "usage_log.csv",
        mode="a",
        header=not os.path.exists("usage_log.csv"),
        index=False
    )

#===============
# VALIDATION
#===============

def validate_inputs(user_input):
    warnings = []
    errors = []

    # AGE
    if user_input["age"] < 18 or user_input["age"] > 100:
        errors.append("Age must be between 18 and 100 years.")

    # HEIGHT
    if height_cm <= 0:
        st.error("Height must be greater than zero.")
        st.stop()

    # WEIGHT
    if weight <= 0:
        st.error("Weight must be greater than zero.")
        st.stop()

    # GLUCOSE
    if user_input["glucose_fasting"] < 50 or user_input["glucose_fasting"] > 300:
        errors.append("Fasting glucose value seems unusual. Please confirm.")

    # PHYSICAL ACTIVITY
    if user_input["physical_activity_minutes_per_week"] > 1000:
        warnings.append("Very high physical activity reported. Make sure this is correct.")

    # SLEEP
    if user_input["sleep_hours_per_day"] < 3 or user_input["sleep_hours_per_day"] > 12:
        warnings.append("Sleep duration outside normal ranges.")

    return errors, warnings

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="PreMed – Preventive Health",
    page_icon="🩺",
    layout="centered"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BANNER_PATH = os.path.join(BASE_DIR, "banner.jpg")

st.image(BANNER_PATH, use_container_width=True)

#st.image("banner.jpg", 
         #use_container_width=True
#)

st.markdown(
    """
    <style>
    /* App background */
    .stApp {
        background-color: #F4FAF8;
        font-family: "Inter", sans-serif;
    }

    /* Form container styling */
    div[data-testid="stForm"] {
    background-color: #FFFFFF;
    padding: 2.5rem;
    border-radius: 20px;
    box-shadow: 0 12px 32px rgba(31,79,74,0.08);
    margin-bottom: 3rem;
    }

    /* Main container */
    section.main > div {
        padding-top: 2rem;
    }

    /* Headers */
    h1, h2, h3 {
        color: #1F4F4A;
    }

    /* Text */
    p, li, span {
        color: #1F4F4A;
    }

    /* Primary button */
    div.stButton > button {
        background-color: #6BC5B3;
        color: white;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        border: none;
    }

    div.stButton > button:hover {
        background-color: #58B3A3;
    }
    
    h2 {
    margin-bottom: 0.5rem;
    }

    h3 {
        margin-bottom: 1rem;
        margin-top: 0.5rem;
    }

    p {
        line-height: 1.6;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# HEADER
# =========================

st.markdown(
    """
    <h1 style='text-align: center;'>PreMed</h1>
    <p style='text-align: center; font-size: 18px; color: grey;'>
    Understand your risk of developing diabetes and take action early with clear, actionable steps.
    </p>
    <p style='text-align: center; font-size: 14px; color: #9aa0a6;'>
    Preventive awareness tool · Not a medical diagnosis
    </p>
    """,
    unsafe_allow_html=True
)

st.warning(
    "This tool provides preventive educational insights only."
    " It does not replace medical evaluation, diagnosis or treatment."
    " Always consult a qualified healthcare professional for medical advice."
)


# =========================
# FORM
# =========================


with st.form("health_form"):
    st.info(
    "Please enter values as accurately as possible. "
    "If you are unsure about a value, provide your best estimate. "
    "This tool provides preventive insights, not a medical diagnosis."
    )
    # ---------- ABOUT YOU ----------
    st.header("👤 About you")

    age = st.number_input(
        "Age",
        value=30,
        step=1
    )

    gender = st.selectbox("Gender", ["Female", "Male", "Other"])
    ethnicity = st.selectbox(
        "Ethnicity",
        ["European", "Asian", "African", "Hispanic", "Other"]
    )

    income_level = st.selectbox(
        "Income level", 
        ["Low", "Lower-Middle", "Middle", "Upper-Middle", "High"],
         help="""
        This refers to your approximate household income level.
        • Low: Significant financial constraints affecting daily needs.
        • Lower-Middle: Covers basic needs but with limited financial flexibility.
        • Middle: Stable income covering most needs with some discretionary spending.
        • Upper-Middle: Comfortable income allowing savings and healthier lifestyle choices.
        • High: High financial flexibility and easy access to healthcare and wellness resources.
        
        This variable is used as a proxy for access to healthcare and lifestyle factors.
        """
    )


    education_level = st.selectbox("Education level", ['No formal', 'Highschool', 'Graduate', 'Postgraduate'])

    employment_status = st.selectbox("Employment status", ["Employed", "Unemployed", "Retired", "Student"])

    smoking_status = st.selectbox("Smoking status", ["Never", "Former", "Smoker"])

    family_history_diabetes = st.selectbox(
        "Family history of diabetes",
        [0, 1],
        format_func=lambda x: "Yes" if x == 1 else "No"
    )

    hypertension_history = st.selectbox(
        "Hypertension history",
        [0, 1],
        format_func=lambda x: "Yes" if x == 1 else "No"
    )

    cardiovascular_history = st.selectbox(
        "Cardiovascular disease history",
        [0, 1],
        format_func=lambda x: "Yes" if x == 1 else "No"
    )

    # ---------- LIFESTYLE ----------
    st.header("🍎 Lifestyle")

    physical_activity_minutes_per_week = st.number_input(
        "Physical activity (minutes per week)",
        value=150,
        step=1,
            help="""
        Total minutes of moderate physical activity per week.
        
        WHO recommendation: at least 150 minutes/week.
        """
    )

    sleep_hours_per_day = st.slider(
        "Sleep hours per night",
        max_value=14.0,
        min_value=0.0,        
        value=7.0
    )

    diet_score = st.slider(
        "Diet quality (0 = poor, 10 = excellent)",
        max_value=10.0,
        min_value=0.0,
        value=6.0,
        help="""
        Self-assessed diet quality.

        0–3: Mostly ultra-processed foods
        4–6: Mixed diet
        7–10: Mostly whole foods, fruits, vegetables, balanced meals
        """
    )

    screen_time_hours_per_day = st.slider(
        "Screen time (hours/day)",
        max_value=12.0,
        min_value=0.0,
        value=5.0
    )

    alcohol_consumption_per_week = st.number_input(
        "Alcohol (drinks per week)",
        value=2,
        step=1
    )

    # ---------- HEALTH ----------
    st.header("🧪 Health information")

    col1, col2 = st.columns(2)

    with col1:
        weight = st.number_input(
            "Weight (kg)",
            value=70.0,
            step=0.5
        )

    with col2:
        height_cm = st.number_input(
            "Height (cm)",
            value=170.0,
            step=0.5
        )
    
    height_m = height_cm / 100

    if height_m > 0:
        bmi = weight / (height_m ** 2)
    else:
        bmi = 0

    st.markdown(
    f"<p style='font-size:14px; color: #6c757d;'>"
    f"Calculated BMI: <strong>{bmi:.1f}</strong>"
    f"</p>",
    unsafe_allow_html=True
)

    heart_rate = st.number_input(
        "Resting heart rate",
        value=70,
        step=1
    )

    ldl_cholesterol = st.number_input(
        "LDL cholesterol (mg/dL)",
        value=120.0,
        step=1.0
    )

    glucose_fasting = st.number_input(
        "Fasting glucose (mg/dL)",
        value=95.0,
        step=1.0,
        help="""
        Blood glucose measured after at least 8 hours of fasting.
        
        • < 100 mg/dL: Normal.
        • 100–125 mg/dL: Prediabetes range.
        • ≥ 126 mg/dL: Diabetes range (clinical confirmation required).
        """
    )

    submitted = st.form_submit_button("Assess my risk")
    
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# RESULTS
# =========================
if submitted:
    user_input = {
        "age": age,
        "gender": gender,
        "ethnicity": ethnicity,
        "income_level": income_level,
        "education_level": education_level,
        "employment_status": employment_status,
        "smoking_status": smoking_status,
        "family_history_diabetes": family_history_diabetes,
        "hypertension_history": hypertension_history,
        "cardiovascular_history": cardiovascular_history,
        "heart_rate": heart_rate,
        "alcohol_consumption_per_week": alcohol_consumption_per_week,
        "diet_score": diet_score,
        "sleep_hours_per_day": sleep_hours_per_day,
        "bmi": bmi,
        "screen_time_hours_per_day": screen_time_hours_per_day,
        "physical_activity_minutes_per_week": physical_activity_minutes_per_week,
        "ldl_cholesterol": ldl_cholesterol,
        "glucose_fasting": glucose_fasting
    }

    errors, warnings = validate_inputs(user_input)

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    if warnings:
        for w in warnings:
            st.warning(w)

    with st.spinner("Analysing your health profile..."):
        result = predict_risk_with_explanation_and_action(user_input)
        risk_pct = int(result["risk_probability"] * 100)
        

    # ---------- CARD 1: RISK ----------

    st.markdown("<h2>Your diabetes risk</h2>", unsafe_allow_html=True)

    st.markdown(
        f"<div style='font-size:46px; font-weight:700; color:#1F4F4A;'>"
        f"{risk_pct}%</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='color:#6B8F8B; margin-bottom:1.5rem;'>Estimated probability</p>",
        unsafe_allow_html=True
    )

    st.progress(risk_pct)
    st.caption(
        "0% = very low risk · 100% = very high risk"
    )


    if result["risk_level"] == "Low":
        badge_color = "#DFF5EC"
        text_color = "#1F7A63"
        label = "Low risk"
    elif result["risk_level"] == "Medium":
        badge_color = "#FFF4D6"
        text_color = "#8A6A00"
        label = "Moderate risk"
    else:
        badge_color = "#FDE2E2"
        text_color = "#9B1C1C"
        label = "High risk"

    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:0.5rem 1.2rem;
            border-radius:999px;
            background-color:{badge_color};
            color:{text_color};
            font-weight:600;
            font-size:14px;
            margin-top:1.2rem;
        ">
            {label}
        </div>
        """,
        unsafe_allow_html=True
    )


    # ---------- CARD 2: DRIVERS ----------
    st.markdown("<h3>What influences your risk</h3>", unsafe_allow_html=True)

    st.markdown(
    """
    ---
    <div style='text-align:center; font-size:16px; color:#2e7d65; margin-top:15px;'>
    Understand what is impacting your result the most:
    </div>
    """,
    unsafe_allow_html=True
)
    
    st.markdown("<br>", unsafe_allow_html=True)

    for d in result["key_drivers"]:
        st.markdown(f"<p>• {d}</p>", unsafe_allow_html=True)

    # ---------- CARD 3: ACTION PLAN ----------

    st.markdown("<h3>What you can do now</h3>", unsafe_allow_html=True)

    st.markdown(
    """
    ---
    <div style='text-align:center; font-size:16px; color:#2e7d65; margin-top:15px;'>
    Small changes, done consistently, have the biggest long-term impact.
    
    </div>
    """,
    unsafe_allow_html=True
)
    
    st.markdown("<br>", unsafe_allow_html=True)

    for item in result["action_plan"]:
        st.markdown(
            f"<p style='font-weight:600; margin-top:1.2rem;'>"
            f"{item['driver']}</p>",
            unsafe_allow_html=True
        )
        for rec in item["recommendations"]:
            st.markdown(
                f"<p style='margin-left:1rem;'>– {rec}</p>",
                unsafe_allow_html=True
            )
    
    with st.expander("How this risk is calculated"):
        st.markdown(
            """
            <div style="
            background-color: #fde7f0;
            padding: 15px;
            border-radius: 10px;
            border-left: 6px solid #d81b60;
        ">
        <b>Model explanation</b><br><br>
        This risk estimation is generated using a machine learning model 
        trained on structured health and lifestyle data. 
        
        The model uses gradient boosting (LightGBM) and interpretable 
        SHAP values to explain individual predictions.
        </div>
        """,
        unsafe_allow_html=True
        )


    log_case(user_input, result)

    LOG_FILE = "usage_log.csv"

    st.subheader("Stored cases (traceability log)")


    if os.path.exists(LOG_FILE):
        df_logs = pd.read_csv(LOG_FILE)
        st.dataframe(df_logs.tail(20))
    else:
        st.info("No cases logged yet.")

    st.download_button(
    "Download logs (CSV)",
    df_logs.to_csv(index=False),
    file_name="premed_case_logs.csv"
    )

st.markdown("---")
st.caption(
    "Disclaimer: This risk estimation is based on statistical modelling "
    "and should not be considered a clinical diagnosis."
)



