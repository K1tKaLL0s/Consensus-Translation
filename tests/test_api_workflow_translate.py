from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_translate_workflow_happy_path_allows_copy_after_confirm() -> None:
    start_response = client.post(
        "/workflow/translate/start",
        data={"source_declaration": "主题"},
        files={"file": ("sample.txt", "first draft".encode("utf-8"), "text/plain")},
    )

    assert start_response.status_code == 200
    started = start_response.json()
    assert started["status"] == "translate_started"
    workflow_id = started["workflow_id"]

    revise_response = client.post(
        "/workflow/translate/revise",
        json={"workflow_id": workflow_id, "user_revision_text": "revised draft"},
    )

    assert revise_response.status_code == 200
    revised = revise_response.json()
    assert revised["status"] == "translate_revised"

    confirm_response = client.post(
        "/workflow/translate/confirm",
        json={"workflow_id": workflow_id, "confirmed": True},
    )

    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert confirmed["status"] == "translate_confirmed"
    assert confirmed["copy_allowed"] is True

    get_response = client.get(f"/workflow/translate/{workflow_id}")
    assert get_response.status_code == 200
    current = get_response.json()
    assert current["confirmed"] is True
    assert current["copy_allowed"] is True


def test_translate_workflow_start_rejects_blank_source_declaration() -> None:
    response = client.post(
        "/workflow/translate/start",
        data={"source_declaration": "   "},
        files={"file": ("sample.txt", "hello".encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 400


def test_translate_workflow_unknown_ids_return_404() -> None:
    revise_response = client.post(
        "/workflow/translate/revise",
        json={"workflow_id": "missing-id", "user_revision_text": "revised draft"},
    )
    assert revise_response.status_code == 404

    confirm_response = client.post(
        "/workflow/translate/confirm",
        json={"workflow_id": "missing-id", "confirmed": True},
    )
    assert confirm_response.status_code == 404

    get_response = client.get("/workflow/translate/missing-id")
    assert get_response.status_code == 404


def test_translate_workflow_start_rejects_non_utf8_upload() -> None:
    response = client.post(
        "/workflow/translate/start",
        data={"source_declaration": "主题"},
        files={"file": ("sample.txt", b"\xff\xfe\xfa", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "uploaded file must be valid UTF-8 text"
