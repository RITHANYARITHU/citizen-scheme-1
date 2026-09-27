from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_results_require_profile_and_explain_prior_application(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.sqlite3"))
    monkeypatch.setenv("DEMO_MODE", "true")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=15).run()
    assert not app.exception

    app.text_area[0].set_value("farmer")
    app.button[0].click().run()
    assert not app.exception
    assert any("eligibility details" in warning.value for warning in app.warning)

    app.selectbox[1].set_value("Farmer")
    app.selectbox[4].set_value("Yes")
    app.multiselect[0].set_value(["pm-kisan"])
    app.button[0].click().run()
    assert not app.exception
    results = next(item.value for item in app.markdown if "### Previously applied" in item.value)
    eligible = results.split("### Eligible schemes")[1].split("### Need more details")[0]
    assert "PM-KISAN" not in eligible
    assert "**Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)**" in results
    assert "Not eligible for a new application" in results
    assert "already applied" in results
