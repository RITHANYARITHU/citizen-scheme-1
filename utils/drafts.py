"""User-editable application draft generation."""

from __future__ import annotations

from typing import Any

from utils.i18n import message


def create_application_draft(
    scheme: dict[str, Any],
    profile: dict[str, Any],
    language: str = "en",
) -> str:
    tamil = language.lower().startswith("ta")
    intro = message(language, "draft_intro")
    applicant = profile.get("name") or ("[விண்ணப்பதாரர் பெயர்]" if tamil else "[Applicant name]")
    lines = [
        f"# {intro}",
        "",
        f"**Scheme:** {scheme['name_ta'] if tamil else scheme['name']}",
        f"**Department:** {scheme['department']}",
        "",
        ("மதிப்பிற்குரிய அதிகாரிக்கு," if tamil else "To the Scheme Officer,"),
        "",
        (
            f"நான் {applicant}. {scheme['name_ta']} திட்டத்திற்கான எனது விண்ணப்பத்தை பரிசீலிக்குமாறு கேட்டுக்கொள்கிறேன்."
            if tamil
            else f"I, {applicant}, request that my application for {scheme['name']} be considered."
        ),
        "",
        f"**Age / வயது:** {profile.get('age') or '[Enter age / வயதை உள்ளிடவும்]'}",
        f"**State / மாநிலம்:** {profile.get('state') or '[Enter state / மாநிலத்தை உள்ளிடவும்]'}",
        f"**Occupation / தொழில்:** {profile.get('occupation') or '[Enter occupation / தொழிலை உள்ளிடவும்]'}",
        f"**Contact / தொடர்பு:** {profile.get('contact') or '[Enter phone or email / தொலைபேசி அல்லது மின்னஞ்சல்]'}",
        "",
        ("தேவையான ஆவணங்களை இணைத்துள்ளேன். கூடுதல் தகவல் தேவைப்பட்டால் தெரிவிக்கவும்." if tamil else "I have attached the required supporting documents. Please let me know if further information is needed."),
        "",
        ("நன்றி,\n" if tamil else "Sincerely,\n"),
        applicant,
        "",
        "**Documents to verify / சரிபார்க்க வேண்டிய ஆவணங்கள்:**",
        *[f"- {document}" for document in scheme["documents"]],
        "",
        f"**Official application page:** {scheme['application_url']}",
        "",
        message(language, "disclaimer"),
    ]
    return "\n".join(lines)
