"""Streamlit UI for the bilingual citizen scheme assistant."""

from __future__ import annotations

from typing import Any

from config import get_settings
from database.db import initialize_database, list_schemes
from graph.workflow import run_assistant
from utils.i18n import message


def _render_profile(st, language: str) -> dict[str, Any]:
    tamil = language == "ta"
    st.subheader("உங்கள் விவரங்கள்" if tamil else "Your details")
    st.caption(
        "தேவையான விவரங்களை மட்டும் வழங்கவும்." if tamil
        else "Share only the details needed for an indicative eligibility check."
    )
    with st.expander("Edit profile / சுயவிவரத்தைத் திருத்து", expanded=True):
        left, right = st.columns(2)
        with left:
            name = st.text_input("பெயர்" if tamil else "Name (optional)")
            age = st.number_input("வயது" if tamil else "Age", min_value=0, max_value=120, value=0)
            state = st.text_input(
                "மாநிலம்" if tamil else "State",
                placeholder="எ.கா. தமிழ்நாடு" if tamil else "e.g. Tamil Nadu",
            )
            gender_label = st.selectbox("பாலினம்" if tamil else "Gender", ["Not provided", "Female", "Male", "Other"])
            occupation = st.selectbox("தொழில்" if tamil else "Occupation", ["Not provided", "Farmer", "Student", "Other"])
        with right:
            category = st.selectbox("சமூகப் பிரிவு" if tamil else "Community category", ["Not provided", "SC", "ST", "OBC", "General"])
            schemes = list_schemes()
            names = {scheme["id"]: scheme["name_ta"] if tamil else scheme["name"] for scheme in schemes}
            previously_applied = st.multiselect(
                "முன்பே விண்ணப்பித்த திட்டங்கள்" if tamil else "Schemes you have already applied for",
                options=list(names),
                format_func=lambda scheme_id: names[scheme_id],
                help="Select only schemes you have already applied for. This is not an official eligibility decision.",
            )
        st.caption(
            "முன்பு விண்ணப்பித்த திட்டங்களுக்கு புதிய விண்ணப்பம் பரிந்துரைக்கப்படாது; நிலையை அதிகாரப்பூர்வ தளத்தில் சரிபார்க்கவும்."
            if tamil else
            "Previously applied schemes will not be suggested for a new application. Check their status on the official portal."
        )
        unknown = "தெரிவிக்கவில்லை" if tamil else "Not provided"
        yes_no = [unknown, "ஆம்" if tamil else "Yes", "இல்லை" if tamil else "No"]
        with st.expander("Additional eligibility details / கூடுதல் தகுதி விவரங்கள்"):
            detail_left, detail_right = st.columns(2)
            with detail_left:
                is_student = st.selectbox("மாணவர்" if tamil else "Currently a student", yes_no)
                has_land = st.selectbox("நிலம் உள்ளது" if tamil else "Has agricultural land", yes_no)
                is_rural = st.selectbox("கிராமப்புறத்தில் வசிக்கிறேன்" if tamil else "Lives in a rural area", yes_no)
                education_after_matric = st.selectbox(
                    "பத்தாம் வகுப்புக்குப் பிந்தைய படிப்பு" if tamil else "Studying beyond matriculation",
                    yes_no,
                )
            with detail_right:
                government_school_background = st.selectbox(
                    "அரசுப் பள்ளிப் பின்னணி" if tamil else "Government school background",
                    yes_no,
                )
                beneficiary_database_match = st.selectbox(
                    "பயனாளர் தரவுத்தளத்தில் பெயர் உள்ளது" if tamil else "Listed in beneficiary database",
                    yes_no,
                )
                meets_household_rules = st.selectbox(
                    "குடும்பத் தகுதி நிபந்தனைகள் பூர்த்தி" if tamil else "Meets household criteria",
                    yes_no,
                )
                contact = st.text_input("தொடர்பு விவரம்" if tamil else "Contact (optional)")
    def selected_bool(value: str) -> bool | None:
        if value == unknown:
            return None
        return value in {"ஆம்", "Yes"}

    return {
        "name": name.strip(),
        "age": int(age) if age > 0 else None,
        "state": state.strip() or None,
        "gender": gender_label.casefold() if gender_label != "Not provided" else None,
        "occupation": occupation.casefold() if occupation != "Not provided" else None,
        "category": category if category != "Not provided" else None,
        "is_student": selected_bool(is_student),
        "has_land": selected_bool(has_land),
        "is_rural": selected_bool(is_rural),
        "education_after_matric": selected_bool(education_after_matric),
        "government_school_background": selected_bool(government_school_background),
        "beneficiary_database_match": selected_bool(beneficiary_database_match),
        "meets_household_rules": selected_bool(meets_household_rules),
        "contact": contact.strip(),
        "previously_applied_scheme_ids": previously_applied,
    }


def main() -> None:
    import streamlit as st

    initialize_database()
    st.set_page_config(page_title="Citizen Scheme Assistant", page_icon="🏛️", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem; }
        .hero { padding: 1.2rem 1.4rem; border-radius: 14px; background: #f3f7fb; border: 1px solid #dce7f1; margin-bottom: 1.5rem; }
        .hero h1 { margin: 0; color: #12344d; font-size: 2rem; }
        .hero p { margin: .35rem 0 0; color: #526675; }
        div[data-testid="stExpander"] { border-radius: 10px; border-color: #dce7f1; }
        div.stButton > button[kind="primary"] { border-radius: 8px; min-height: 2.7rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero"><h1>🏛️ Citizen Scheme Eligibility Assistant</h1>'
        '<p>Find relevant welfare schemes, understand indicative eligibility, and prepare an application draft.</p></div>',
        unsafe_allow_html=True,
    )
    language = st.sidebar.selectbox(
        "Language / மொழி", ["en", "ta"], format_func=lambda value: "English" if value == "en" else "தமிழ்"
    )
    st.sidebar.divider()
    st.sidebar.subheader("About")
    st.sidebar.caption("A local-first academic demo for scheme discovery. It does not provide final government approval.")
    settings = get_settings()
    if settings.demo_mode:
        st.sidebar.info("Offline demo mode • No API key required")
    elif settings.tavily_api_key:
        st.sidebar.info("Tavily web search is configured")
    else:
        st.sidebar.info("Local mode • Add TAVILY_API_KEY to enable web search")
    st.sidebar.caption("Confirm scheme details with the linked official source before applying.")
    profile = _render_profile(st, language)

    check_tab, draft_tab, catalog_tab = st.tabs(
        ["🔎 Check eligibility", "📝 Application draft", "📚 Scheme catalog"]
    )
    with check_tab:
        st.subheader("Find schemes")
        st.caption(
            "உதாரணம்: தமிழ்நாட்டில் விவசாயிகளுக்கான திட்டங்கள்"
            if language == "ta"
            else "Describe the support you need in a sentence."
        )
        question = st.text_area(
            "எதைத் தேடுகிறீர்கள்?" if language == "ta" else "What kind of support are you looking for?",
            placeholder="உதா: மாணவர்களுக்கான உதவித்தொகை / e.g. scholarship for students",
            height=90,
            label_visibility="collapsed",
        )
        enable_web = st.checkbox("Use current web search when configured", value=True)
        if st.button("திட்டங்களைத் தேடு" if language == "ta" else "Find schemes", type="primary"):
            if not question.strip():
                st.warning("Enter a question to search." if language == "en" else "தேடுவதற்கு உங்கள் கேள்வியை உள்ளிடவும்.")
            else:
                with st.spinner("திட்டங்களைத் தேடுகிறது..." if language == "ta" else "Searching schemes..."):
                    result = run_assistant(question, profile, language, enable_web_search=enable_web)
                if result["route"] == "collect_profile":
                    st.warning(result["answer"])
                else:
                    st.markdown(result["answer"])

    with draft_tab:
        st.subheader("Prepare an application draft")
        st.caption("Review every field before submitting it to an official department.")
        schemes = list_schemes()
        labels = {f"{scheme['name']} — {scheme['id']}": scheme["id"] for scheme in schemes}
        selected = st.selectbox("Scheme / திட்டம்", list(labels))
        if st.button("Create editable draft / திருத்தக்கூடிய வரைவை உருவாக்கு"):
            result = run_assistant(
                "application draft",
                profile,
                language,
                requested_scheme_id=labels[selected],
                request_draft=True,
                enable_web_search=False,
            )
            st.text_area("Draft / வரைவு", value=result["draft"], height=420)
            st.download_button(
                "Download draft / வரைவைப் பதிவிறக்கு",
                data=result["draft"],
                file_name=f"{labels[selected]}-application-draft.txt",
                mime="text/plain",
            )

    with catalog_tab:
        st.subheader("Available demo schemes")
        st.caption("These records are illustrative demo data with official links for verification.")
        for scheme in list_schemes():
            with st.expander(f"{scheme['name']} · {scheme['name_ta']}"):
                st.write(scheme["summary"])
                st.write(scheme["summary_ta"])
                st.write(f"**Department:** {scheme['department']}")
                st.write(f"**Benefit:** {scheme['benefit']}")
                st.write("**Documents:** " + ", ".join(scheme["documents"]))
                st.markdown(f"[Official information]({scheme['source_url']}) · [Apply / details]({scheme['application_url']})")
    st.divider()
    st.caption(message(language, "disclaimer"))


if __name__ == "__main__":
    main()
