from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_companion_actions_drive_the_existing_job_workflow():
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    assert not app.exception

    app.chat_input[0].set_value("Find a Junior Backend Developer in Jordan").run(timeout=20)
    assert app.session_state["tap_agent"]["current_state"] == "opportunities_found"
    assert app.session_state["tap_agent"]["current_job_results"]
    assert not app.radio  # Assessments are not rendered for unselected results.

    _button(app, "Select this opportunity").click().run(timeout=20)
    assert app.session_state["tap_agent"]["current_state"] == "job_selected"
    assert app.session_state["tap_agent"]["selected_job_id"]

    _button(app, "Analyze Skill Gap").click().run(timeout=20)
    assert app.session_state["tap_agent"]["current_state"] == "gap_analyzed"

    _button(app, "Open Learning Roadmap").click().run(timeout=20)
    assert app.session_state["tap_agent"]["current_state"] == "roadmap_ready"
    assert app.session_state["tap_agent"]["selected_roadmaps"]

    _button(app, "Test My Skills").click().run(timeout=20)
    assert app.session_state["tap_agent"]["current_state"] == "assessment_pending"
    assert len(app.radio) == 3  # Current priority skill only.

