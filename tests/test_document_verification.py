from src.document_verification import (
    _names_match, extract_supporting_document, overall_verification_status,
    unsupported_certification_claims, verify_supporting_document,
)
from src.resume_parser import parse_resume_sections

RESUME_TEXT = """Rahul Sharma
rahul.sharma@example.com

Experience
Software Engineer, ABC Technologies | Jan 2023 - Jun 2024
Built backend services.
"""


def test_extracts_organization_role_dates_and_credential_id():
    cert_text = (
        "Rahul Sharma\nExperience Certificate\nCompany: ABC Tech Pvt. Ltd.\n"
        "Role: Software Engineer\nJan 2023 - Jun 2024\nCertificate ID: EXP-12345\n"
    )
    doc = extract_supporting_document(cert_text, "exp_cert.pdf")
    assert doc.document_type == "employment_certificate"
    assert doc.candidate_name == "Rahul Sharma"
    assert "ABC" in doc.organization
    assert doc.role_or_degree == "Software Engineer"
    assert doc.credential_id == "EXP-12345"
    assert doc.date_range is not None


def test_consistent_document_produces_no_high_severity_flags():
    resume = parse_resume_sections(RESUME_TEXT)
    cert_text = "Rahul Sharma\nCompany: ABC Tech Pvt. Ltd.\nRole: Software Engineer\nJan 2023 - Jun 2024\n"
    doc = extract_supporting_document(cert_text, "exp_cert.pdf")
    flags = verify_supporting_document(resume, doc)
    assert overall_verification_status(flags) == "clean"


def test_date_mismatch_between_resume_and_certificate_flagged():
    resume = parse_resume_sections(RESUME_TEXT)
    cert_text = "Rahul Sharma\nCompany: ABC Technologies\nRole: Software Engineer\nMar 2023 - Aug 2024\n"
    doc = extract_supporting_document(cert_text, "exp_cert.pdf")
    flags = verify_supporting_document(resume, doc)
    assert overall_verification_status(flags) == "verification_required"
    assert any("date mismatch" in f.message.lower() for f in flags)


def test_name_mismatch_flagged():
    resume = parse_resume_sections(RESUME_TEXT)
    cert_text = "Rahul Verma\nCompany: ABC Technologies\nRole: Software Engineer\nJan 2023 - Jun 2024\n"
    doc = extract_supporting_document(cert_text, "exp_cert.pdf")
    flags = verify_supporting_document(resume, doc)
    assert any("identity mismatch" in f.message.lower() for f in flags)


def test_minor_name_formatting_difference_not_flagged():
    """Regression: middle initial / minor punctuation differences must not
    be treated as an identity mismatch."""
    assert _names_match("Rahul Sharma", "Rahul S. Sharma") is True


def test_different_surname_is_flagged_despite_shared_first_name():
    """Regression: a shared first name must not mask a genuinely different
    surname — pure fused-string similarity previously let this through."""
    assert _names_match("Rahul Sharma", "Rahul Verma") is False


def test_company_name_variants_normalize_to_match():
    resume = parse_resume_sections(RESUME_TEXT)
    cert_text = "Rahul Sharma\nCompany: ABC Tech Pvt. Ltd.\nRole: Software Engineer\nJan 2023 - Jun 2024\n"
    doc = extract_supporting_document(cert_text, "exp_cert.pdf")
    flags = verify_supporting_document(resume, doc)
    # Should find a matched entry (company names normalize to the same thing)
    # and report consistency rather than "could not locate a corresponding entry".
    assert not any("could not confidently locate" in f.message.lower() for f in flags)


def test_certification_document_never_claims_verified_authenticity():
    resume = parse_resume_sections(RESUME_TEXT)
    cert_text = "Rahul Sharma\nAWS Certified Developer\nCredential ID: ABC123\nIssue date: 2025\n"
    doc = extract_supporting_document(cert_text, "aws_cert.pdf")
    assert doc.document_type == "certification"
    flags = verify_supporting_document(resume, doc)
    assert any("cannot be independently verified" in f.message.lower() for f in flags)
    banned = ["fake", "fraud", "lying", "forged"]
    for f in flags:
        for word in banned:
            assert word not in f.message.lower()


def test_certification_claimed_without_document_flagged():
    resume_text = RESUME_TEXT + "\nCertifications\nAWS Certified Developer — Amazon\n"
    flags = unsupported_certification_claims(resume_text, supporting_docs=[])
    assert any("aws certified developer" in f.message.lower() for f in flags)


def test_certification_with_matching_document_not_flagged_as_unsupported():
    resume_text = RESUME_TEXT + "\nCertifications\nAWS Certified Developer — Amazon\n"
    doc = extract_supporting_document("AWS Certified Developer\nCredential ID: X\n", "aws.pdf")
    flags = unsupported_certification_claims(resume_text, supporting_docs=[doc])
    assert not any("aws certified developer" in f.message.lower() for f in flags)
