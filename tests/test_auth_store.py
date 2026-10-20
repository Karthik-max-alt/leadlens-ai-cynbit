import os
from pathlib import Path

import pytest

import auth_store
from leadlens import analyze_inquiry


def setup_db(path: Path, monkeypatch):
    monkeypatch.setenv("LEADLENS_DEMO_MODE", "false")
    monkeypatch.setenv("LEADLENS_DB", str(path))
    auth_store.init_db(path, demo_mode=False)
    return path


def test_passwords_are_hashed_and_verified():
    salt, digest = auth_store.hash_password("correct-horse-battery")
    assert salt != "correct-horse-battery"
    assert digest != "correct-horse-battery"
    assert auth_store.verify_password("correct-horse-battery", salt, digest)
    assert not auth_store.verify_password("wrong-password-value", salt, digest)


def test_user_creation_login_and_invalid_login(tmp_path, monkeypatch):
    db = setup_db(tmp_path / "test.db", monkeypatch)
    auth_store.create_user("karthik_test", "Karthik Test", "Admin", "a-strong-password-123", actor="tester", db_path=db)
    user = auth_store.authenticate("karthik_test", "a-strong-password-123", db_path=db)
    assert user is not None
    assert user["role"] == "Admin"
    assert auth_store.authenticate("karthik_test", "wrong-password-123", db_path=db) is None


def test_user_validation_and_duplicate_username(tmp_path, monkeypatch):
    db = setup_db(tmp_path / "test.db", monkeypatch)
    with pytest.raises(ValueError):
        auth_store.create_user("bad name", "Test", "Sales", "a-strong-password-123", db_path=db)
    auth_store.create_user("sales_one", "Sales One", "Sales", "a-strong-password-123", db_path=db)
    with pytest.raises(ValueError):
        auth_store.create_user("sales_one", "Sales Duplicate", "Sales", "a-strong-password-123", db_path=db)


def test_lead_create_duplicate_detection_and_audit(tmp_path, monkeypatch):
    db = setup_db(tmp_path / "test.db", monkeypatch)
    result = analyze_inquiry("We need an AI workflow automation and dashboard for our retail stores with API integration.", use_llm=False)
    lead_id = auth_store.create_lead(
        "We need an AI workflow automation and dashboard for our retail stores with API integration.", result,
        company="Example Retail", contact_email="ops@example.com", actor="tester", db_path=db,
    )
    assert lead_id > 0
    duplicates = auth_store.find_duplicates(
        "Example Retail", "OPS@example.com", "We need an AI workflow automation and dashboard for our retail stores with API integration.", db_path=db,
    )
    assert len(duplicates) == 1
    # Same contact, distinct inquiry should not be flagged as an exact duplicate.
    distinct = auth_store.find_duplicates("Example Retail", "ops@example.com", "We need a new website for our retail stores.", db_path=db)
    assert distinct == []
    rows = auth_store.list_leads(db_path=db)
    assert rows[0]["id"] == lead_id
    auth_store.update_lead(lead_id, actor="tester", status="Contacted", assigned_to="sales_one", follow_up_date="2030-01-01", notes="Called prospect", db_path=db)
    updated = auth_store.get_lead(lead_id, db_path=db)
    assert updated["status"] == "Contacted"
    events = auth_store.list_events(db_path=db)
    assert any(event["action"] == "LEAD_UPDATED" for event in events)


def test_analyst_role_is_valid_and_demo_users_not_seeded_in_non_demo_mode(tmp_path, monkeypatch):
    db = setup_db(tmp_path / "fresh.db", monkeypatch)
    assert auth_store.list_users(db_path=db) == []
    auth_store.create_user("analyst_one", "Analyst One", "Analyst", "a-strong-password-123", db_path=db)
    assert next(u for u in auth_store.list_users(db_path=db) if u["username"] == "analyst_one")["role"] == "Analyst"


def test_deactivated_user_cannot_authenticate(tmp_path, monkeypatch):
    db = setup_db(tmp_path / "test.db", monkeypatch)
    auth_store.create_user("sales_two", "Sales Two", "Sales", "a-strong-password-123", db_path=db)
    auth_store.change_user_status("sales_two", False, actor="admin_test", db_path=db)
    assert auth_store.authenticate("sales_two", "a-strong-password-123", db_path=db) is None


def test_password_change_requires_correct_current_password(tmp_path, monkeypatch):
    db = setup_db(tmp_path / "test.db", monkeypatch)
    auth_store.create_user("analyst_two", "Analyst Two", "Analyst", "a-strong-password-123", db_path=db)
    with pytest.raises(ValueError):
        auth_store.set_own_password("analyst_two", "wrong-current-password", "a-new-strong-password-456", db_path=db)
    auth_store.set_own_password("analyst_two", "a-strong-password-123", "a-new-strong-password-456", db_path=db)
    assert auth_store.authenticate("analyst_two", "a-new-strong-password-456", db_path=db) is not None


def test_invalid_pipeline_status_rejected(tmp_path, monkeypatch):
    db = setup_db(tmp_path / "test.db", monkeypatch)
    result = analyze_inquiry("We need AI workflow automation and a dashboard for retail stores.", use_llm=False)
    lead_id = auth_store.create_lead("We need AI workflow automation and a dashboard for retail stores.", result, actor="tester", db_path=db)
    with pytest.raises(ValueError):
        auth_store.update_lead(lead_id, actor="tester", status="MAGIC WON", db_path=db)
