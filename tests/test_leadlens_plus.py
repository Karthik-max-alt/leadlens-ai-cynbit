from leadlens import SAMPLE_INQUIRIES, analyze_inquiry
from leadlens_plus import generate_discovery_pack, inquiry_tone, urgency_signal


def test_discovery_pack_never_claims_to_send_email():
    inquiry = SAMPLE_INQUIRIES["Vague early-stage inquiry"]
    result = analyze_inquiry(inquiry, use_llm=False)
    pack = generate_discovery_pack("Example Co", inquiry, result, use_llm=False)
    assert "DRAFT ONLY" in pack["email_draft"]
    assert "No scope or pricing has been assumed" in pack["email_draft"]
    assert pack["generation_mode"] == "Local template fallback"
    assert pack["scope_outline"]["out_of_scope_until_confirmed"]


def test_urgency_requires_explicit_phrase_or_stated_timeline():
    urgent = analyze_inquiry("We need an AI workflow automation solution urgently this week.", use_llm=False)
    signal = urgency_signal("We need an AI workflow automation solution urgently this week.", urgent)
    assert signal["is_urgent"] is True
    non_urgent = analyze_inquiry("We are exploring a possible website for a small business.", use_llm=False)
    signal2 = urgency_signal("We are exploring a possible website for a small business.", non_urgent)
    assert signal2["label"] == "No timeline stated"
    assert signal2["is_urgent"] is False


def test_tone_cue_is_labeled_not_inferred_by_default():
    assert inquiry_tone("We are interested in learning more.") == "Positive interest wording"
    assert inquiry_tone("We have an issue with our current system.") == "Concern / issue mentioned"
    assert inquiry_tone("Need a new website with an API integration.") == "Neutral / not inferred"
