"""Small bilingual response templates for the no-key demo."""

from __future__ import annotations

MESSAGES = {
    "en": {
        "found": "I found **{count}** potentially relevant scheme(s).",
        "eligible": "Based on the indicative demo rules, your profile appears to meet the listed checks.",
        "not_eligible": "One or more supplied details do not match the indicative demo rules.",
        "need_info": "I need a few more details before checking the listed criteria.",
        "disclaimer": "Demo information only. Scheme rules and application windows change; verify eligibility and details with the official department before applying.",
        "draft_intro": "Application preparation draft (review and edit before submission)",
        "official_info": "Official information",
        "missing_label": "Missing information",
        "web_search": "Web search",
        "web_unavailable": "Tavily search is unavailable; continuing with local scheme information.",
        "enter_profile": "Please enter some eligibility details in your profile before checking schemes. Name and contact details alone are not enough.",
        "eligible_heading": "Eligible schemes (indicative demo check)",
        "more_details_heading": "Need more details",
        "applied_heading": "Previously applied",
        "not_eligible_heading": "Not eligible based on the supplied details",
        "no_eligible": "No schemes meet all the available demo checks yet. Review the sections below or provide more details.",
        "applied_status": "Not eligible for a new application based on your reported prior application.",
    },
    "ta": {
        "found": "உங்கள் கேள்விக்கு தொடர்புடைய **{count}** திட்டங்கள் கிடைத்தன.",
        "eligible": "குறிப்புக்கான டெமோ விதிகளின்படி, வழங்கிய விவரங்கள் பட்டியலிடப்பட்ட சரிபார்ப்புகளுடன் பொருந்துகின்றன.",
        "not_eligible": "வழங்கிய விவரங்களில் ஒன்று அல்லது அதற்கு மேற்பட்டவை குறிப்புக்கான டெமோ விதிகளுடன் பொருந்தவில்லை.",
        "need_info": "பட்டியலிடப்பட்ட தகுதி நிபந்தனைகளைச் சரிபார்க்க மேலும் சில விவரங்கள் தேவை.",
        "disclaimer": "இது டெமோ தகவல் மட்டுமே. திட்ட விதிகளும் விண்ணப்ப காலங்களும் மாறலாம்; விண்ணப்பிக்கும் முன் அதிகாரப்பூர்வ துறையில் சரிபார்க்கவும்.",
        "draft_intro": "விண்ணப்பத் தயாரிப்பு வரைவு (சமர்ப்பிக்கும் முன் சரிபார்த்து திருத்தவும்)",
        "official_info": "அதிகாரப்பூர்வ தகவல்",
        "missing_label": "தேவையான விவரங்கள்",
        "web_search": "இணையத் தேடல்",
        "web_unavailable": "Tavily தேடல் கிடைக்கவில்லை; உள்ளூர் திட்டத் தகவலுடன் தொடர்கிறோம்.",
        "enter_profile": "திட்டங்களைச் சரிபார்க்கும் முன் உங்கள் சுயவிவரத்தில் சில தகுதி விவரங்களை உள்ளிடவும். பெயர் அல்லது தொடர்பு விவரம் மட்டும் போதாது.",
        "eligible_heading": "தகுதி பொருந்தும் திட்டங்கள் (குறிப்புக்கான டெமோ சரிபார்ப்பு)",
        "more_details_heading": "மேலும் விவரங்கள் தேவை",
        "applied_heading": "முன்பே விண்ணப்பித்த திட்டங்கள்",
        "not_eligible_heading": "வழங்கிய விவரங்களின்படி தகுதி பொருந்தாதவை",
        "no_eligible": "தற்போதைய டெமோ சரிபார்ப்புகள் அனைத்துக்கும் பொருந்தும் திட்டம் இல்லை. கீழே உள்ளவற்றைப் பார்க்கவும் அல்லது கூடுதல் விவரங்களை உள்ளிடவும்.",
        "applied_status": "நீங்கள் முன்பு விண்ணப்பித்ததாகத் தெரிவித்ததால் புதிய விண்ணப்பத்திற்கு தகுதி இல்லை.",
    },
}


def message(language: str, key: str, **values: object) -> str:
    language_key = "ta" if language.lower().startswith("ta") else "en"
    return MESSAGES[language_key][key].format(**values)


def localize_eligibility_text(text: str, language: str) -> str:
    if not language.lower().startswith("ta"):
        return text
    translated = {
        "Gender does not match this scheme's listed group": "பாலினம் இந்தத் திட்டத்தின் பட்டியலிடப்பட்ட குழுவுடன் பொருந்தவில்லை",
        "Occupation does not match this scheme's listed group": "தொழில் இந்தத் திட்டத்தின் பட்டியலிடப்பட்ட குழுவுடன் பொருந்தவில்லை",
        "This scheme is intended for students": "இந்தத் திட்டம் மாணவர்களுக்கானது",
        "Landholding is required by the demo rule": "டெமோ விதிப்படி நிலம் வைத்திருத்தல் தேவை",
        "Rural residence is required by the demo rule": "டெமோ விதிப்படி கிராமப்புற வசிப்பு தேவை",
        "Applicant must be an adult": "விண்ணப்பதாரர் வயது வந்தவராக இருக்க வேண்டும்",
        "Community category does not match this scheme's listed group": "சமூகப் பிரிவு இந்தத் திட்டத்தின் பட்டியலிடப்பட்ட குழுவுடன் பொருந்தவில்லை",
        "Study beyond matriculation is required by the demo rule": "டெமோ விதிப்படி பத்தாம் வகுப்புக்குப் பிந்தைய படிப்பு தேவை",
        "Government school background is required by the demo rule": "டெமோ விதிப்படி அரசுப் பள்ளிப் பின்னணி தேவை",
        "A beneficiary database match is required": "பயனாளர் தரவுத்தளப் பொருத்தம் தேவை",
        "Household criteria do not match the supplied information": "குடும்பத் தகுதி நிபந்தனைகள் வழங்கிய தகவலுடன் பொருந்தவில்லை",
        "Household housing status does not match this scheme's listed group": "குடும்பத்தின் வீட்டு நிலை இந்தத் திட்டத்தின் பட்டியலிடப்பட்ட குழுவுடன் பொருந்தவில்லை",
        "You reported having already applied for this scheme. Check your existing application status with the official department before applying again; prior application alone does not establish official ineligibility.": "இந்தத் திட்டத்திற்கு முன்பே விண்ணப்பித்ததாக நீங்கள் தெரிவித்துள்ளீர்கள். மீண்டும் விண்ணப்பிக்கும் முன் அதிகாரப்பூர்வ துறையில் ஏற்கனவே உள்ள விண்ணப்பத்தின் நிலையைச் சரிபார்க்கவும்; முன்பு விண்ணப்பித்தது மட்டும் அதிகாரப்பூர்வ தகுதியின்மையை உறுதிப்படுத்தாது.",
        "state": "மாநிலம்",
        "gender": "பாலினம்",
        "occupation": "தொழில்",
        "student status": "மாணவர் நிலை",
        "landholding status": "நிலம் வைத்திருக்கும் நிலை",
        "rural residence": "கிராமப்புற வசிப்பு",
        "age": "வயது",
        "community category": "சமூகப் பிரிவு",
        "studying beyond matriculation": "பத்தாம் வகுப்புக்குப் பிந்தைய படிப்பு",
        "government school background": "அரசுப் பள்ளிப் பின்னணி",
        "beneficiary database match": "பயனாளர் தரவுத்தளப் பொருத்தம்",
        "household eligibility criteria": "குடும்பத் தகுதி நிபந்தனைகள்",
        "household housing status": "குடும்பத்தின் வீட்டு நிலை",
    }
    if text.startswith("State should be "):
        return f"மாநிலம் {text.removeprefix('State should be ')} ஆக இருக்க வேண்டும்"
    return translated.get(text, text)
