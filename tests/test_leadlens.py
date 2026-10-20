import json
from pathlib import Path

import pytest

from leadlens import (
    SAMPLE_INQUIRIES,
    _extract_fields,
    _keyword_category,
    _normalize_llm_fields,
    analyze_inquiry,
    delete_lead,
    list_leads,
    save_lead,
)


def test_rejects_too_short_inquiry():
    with pytest.raises(ValueError, match="at least 12"):
        analyze_inquiry("hello", use_llm=False)


def test_rejects_overlong_inquiry():
    with pytest.raises(ValueError, match="6,000"):
        analyze_inquiry("x" * 6001, use_llm=False)


def test_reviews_route_to_revio():
    fields = _extract_fields(SAMPLE_INQUIRIES["Multi-location review intelligence"])
    assert fields["service_category"] == "Reputation management (Revio)"
    assert "Centralized dashboard" in fields["requirements"]
    assert fields["industry"] == "Retail"


def test_career_platform_routes_to_studio():
    assert _keyword_category(SAMPLE_INQUIRIES["Career platform enhancement"]) == "Career technology (Cynbit Studio)"


def test_property_portfolio_routes_to_tenantease():
    assert _keyword_category(SAMPLE_INQUIRIES["Property operations"]) == "Property technology (TenantEase)"


def test_vague_inquiry_is_not_overconfidently_classified():
    fields = _extract_fields(SAMPLE_INQUIRIES["Vague early-stage inquiry"])
    assert fields["service_category"] == "Unclear / discovery needed"
    assert fields["missing_information"]


def test_local_analysis_returns_required_schema():
    result = analyze_inquiry(SAMPLE_INQUIRIES["Cloud migration"], use_llm=False)
    assert result["model_used"] == "Local keyword-based fallback"
    assert 0 <= result["score"]["score"] <= 100
    assert set(result["score"]["components"]) == {
        "Requirement clarity", "Service fit", "Timeline / urgency evidence",
        "Implementation scope", "Information completeness",
    }
    assert result["fields"]["timeline"] is not None
    assert result["discovery_questions"]


def test_analysis_does_not_claim_probability():
    result = analyze_inquiry(SAMPLE_INQUIRIES["Multi-location review intelligence"], use_llm=False)
    assert "not a probability" in result["score"]["disclaimer"].lower()


def test_llm_output_is_normalized_and_category_allowlisted():
    normalized = _normalize_llm_fields(
        {
            "summary": "  concise summary  ",
            "service_category": "Fictional category",
            "requirements": ["Dashboard", "Dashboard", None],
            "industry": None,
            "timeline": None,
            "budget": None,
            "integrations": "not a list",
            "missing_information": [],
        },
        SAMPLE_INQUIRIES["Multi-location review intelligence"],
    )
    assert normalized["summary"] == "concise summary"
    assert normalized["service_category"] == "Reputation management (Revio)"
    assert normalized["requirements"] == ["Dashboard"]
    assert normalized["integrations"]  # local fallback repairs invalid types
    assert normalized["missing_information"] is not None


def test_sqlite_persistence_roundtrip_and_delete(tmp_path: Path):
    db_path = tmp_path / "nested" / "test.db"
    inquiry = SAMPLE_INQUIRIES["Vague early-stage inquiry"]
    result = analyze_inquiry(inquiry, use_llm=False)
    lead_id = save_lead(inquiry, result, "Example Co", "contact@example.com", path=db_path)
    rows = list_leads(path=db_path)
    assert len(rows) == 1
    assert rows[0]["id"] == lead_id
    assert rows[0]["company"] == "Example Co"
    assert rows[0]["contact_email"] == "contact@example.com"
    assert delete_lead(lead_id, path=db_path) is True
    assert list_leads(path=db_path) == []


def test_rejects_invalid_email(tmp_path: Path):
    result = analyze_inquiry(SAMPLE_INQUIRIES["Cloud migration"], use_llm=False)
    with pytest.raises(ValueError, match="valid contact email"):
        save_lead(SAMPLE_INQUIRIES["Cloud migration"], result, contact_email="not-an-email", path=tmp_path / "test.db")


def test_missing_email_is_allowed(tmp_path: Path):
    inquiry = SAMPLE_INQUIRIES["Vague early-stage inquiry"]
    result = analyze_inquiry(inquiry, use_llm=False)
    lead_id = save_lead(inquiry, result, path=tmp_path / "test.db")
    assert list_leads(path=tmp_path / "test.db")[0]["id"] == lead_id


def test_register_limit_is_bounded(tmp_path: Path):
    inquiry = SAMPLE_INQUIRIES["Cloud migration"]
    result = analyze_inquiry(inquiry, use_llm=False)
    save_lead(inquiry, result, path=tmp_path / "test.db")
    assert len(list_leads(path=tmp_path / "test.db", limit=0)) == 1
    assert len(list_leads(path=tmp_path / "test.db", limit=100000)) == 1


def test_sample_dataset_covers_multiple_opportunities():
    routes = {_extract_fields(inquiry)["service_category"] for inquiry in SAMPLE_INQUIRIES.values()}
    assert len(routes) >= 4
