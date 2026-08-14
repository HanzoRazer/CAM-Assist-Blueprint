"""
CAM-A25 input provenance: observable, but non-participatory.

Provenance answers "which request and which profile produced this result" without
being able to change the result. That property is structural rather than merely
tested -- `reconcile()` never receives paths or versions -- and these tests pin
it at the model boundary so a later refactor cannot quietly fold provenance into
the comparison.

Filesystem-free. Path resolution and CLI behaviour are covered separately.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reconcile_creation_studio_capabilities import (  # noqa: E402
    InputProvenance,
    ProfileProvenance,
    RequestProvenance,
    extract_profile_provenance,
    extract_request_provenance,
    format_input_traceability,
    reconcile,
    serialize_reconciliation,
)

REQUEST_DOC = {
    "record_type": "cam_assist_creation_studio_request",
    "record_version": "1.0.0",
    "package_reference": "ltb_vcarve_synthetic_example",
    "requested_capabilities": ["a", "b"],
}

PROFILE_DOC = {
    "record_type": "creation_studio_capability_profile",
    "record_version": "1.0.0",
    "profile_version": "2.3.1",
    "studio_reference": "cam-creation-studio",
    "capabilities": [{"capability_id": "b"}],
}


def provenance(
    request_path: str = "examples/creation_studio/pkg_request.json",
    profile_path: str = "examples/creation_studio/capability_profile.json",
) -> InputProvenance:
    return InputProvenance(
        request=extract_request_provenance(REQUEST_DOC, Path(request_path)),
        profile=extract_profile_provenance(PROFILE_DOC, Path(profile_path)),
    )


# --- extraction uses the real contract fields --------------------------------


def test_request_provenance_uses_actual_a22_fields():
    p = extract_request_provenance(REQUEST_DOC, Path("a/b_request.json"))
    assert p.record_version == "1.0.0"
    assert p.package_reference == "ltb_vcarve_synthetic_example"


def test_profile_provenance_uses_actual_a23_fields():
    p = extract_profile_provenance(PROFILE_DOC, Path("a/capability_profile.json"))
    assert p.record_version == "1.0.0"
    assert p.profile_version == "2.3.1"
    assert p.studio_reference == "cam-creation-studio"


def test_profile_keeps_the_two_versions_distinct():
    # record_version is the format, owned here; profile_version is the capability
    # set, owned by Creation Studio. Conflating them would be an A23 contract error.
    p = extract_profile_provenance(PROFILE_DOC, Path("x.json"))
    assert p.record_version != p.profile_version


# --- absent metadata is omitted, never null ----------------------------------


@pytest.mark.parametrize(
    "missing", ["record_version", "package_reference"], ids=["record-version", "package-ref"]
)
def test_absent_request_metadata_is_omitted_not_nulled(missing):
    doc = {k: v for k, v in REQUEST_DOC.items() if k != missing}
    payload = extract_request_provenance(doc, Path("r.json")).as_dict()
    assert missing not in payload
    assert None not in payload.values()
    assert payload["path"] == "r.json"  # path always survives


@pytest.mark.parametrize(
    "missing",
    ["record_version", "profile_version", "studio_reference"],
    ids=["record-version", "profile-version", "studio-ref"],
)
def test_absent_profile_metadata_is_omitted_not_nulled(missing):
    doc = {k: v for k, v in PROFILE_DOC.items() if k != missing}
    payload = extract_profile_provenance(doc, Path("p.json")).as_dict()
    assert missing not in payload
    assert None not in payload.values()


def test_non_string_metadata_is_treated_as_absent():
    # A25 does not re-validate A22/A23. A malformed metadata value cannot affect
    # the reconciliation, so it is surfaced as absent rather than escalated.
    doc = {**PROFILE_DOC, "profile_version": 7}
    assert "profile_version" not in extract_profile_provenance(doc, Path("p.json")).as_dict()


def test_no_metadata_at_all_still_yields_a_path():
    payload = extract_profile_provenance({}, Path("only/path.json")).as_dict()
    assert payload == {"path": "only/path.json"}


# --- path rendering ----------------------------------------------------------


def test_paths_are_posix_normalized():
    # The same repository layout must serialize identically on Windows and Linux.
    p = extract_request_provenance(REQUEST_DOC, Path("examples") / "creation_studio" / "r.json")
    assert p.path == "examples/creation_studio/r.json"
    assert "\\" not in p.path


def test_paths_are_not_absolutized():
    # A machine-specific root would defeat cross-machine reproducibility and tell
    # a reviewer nothing useful.
    p = extract_request_provenance(REQUEST_DOC, Path("examples/creation_studio/r.json"))
    assert not Path(p.path).is_absolute()
    assert p.path == "examples/creation_studio/r.json"


# --- serialization shape -----------------------------------------------------


def test_inputs_block_comes_first_and_sets_follow():
    payload = serialize_reconciliation(reconcile(["a", "b"], ["b"]), provenance())
    assert list(payload) == [
        "inputs",
        "satisfied",
        "unsatisfied",
        "declared_but_unrequested",
        "findings",
    ]


def test_inputs_block_carries_both_records():
    payload = serialize_reconciliation(reconcile(["a"], ["a"]), provenance())
    assert set(payload["inputs"]) == {"request", "profile"}
    assert payload["inputs"]["request"]["package_reference"] == "ltb_vcarve_synthetic_example"
    assert payload["inputs"]["profile"]["profile_version"] == "2.3.1"


def test_serialization_round_trips_as_json():
    payload = serialize_reconciliation(reconcile(["a", "b"], ["b"]), provenance())
    assert json.loads(json.dumps(payload)) == payload


def test_serialization_without_provenance_omits_the_inputs_key():
    # The core result stays usable on its own; provenance is composed on top.
    payload = serialize_reconciliation(reconcile(["a"], ["a"]))
    assert "inputs" not in payload
    assert set(payload) == {"satisfied", "unsatisfied", "declared_but_unrequested", "findings"}


# --- non-participation -------------------------------------------------------


def test_reconcile_cannot_receive_provenance_at_all():
    """Structural guarantee: the core takes two lists and nothing else.

    Non-participation is not merely asserted downstream -- there is no parameter
    through which a path or version could reach the comparison.
    """
    import inspect

    params = list(inspect.signature(reconcile).parameters)
    assert params == ["requested", "declared"]


def test_differing_metadata_produces_identical_reconciliation():
    """Same capability sets, completely different provenance."""
    a = serialize_reconciliation(
        reconcile(["a", "b"], ["b", "c"]),
        InputProvenance(
            request=RequestProvenance("one/r.json", "1.0.0", "pkg-one"),
            profile=ProfileProvenance("one/p.json", "1.0.0", "1.0.0", "studio-one"),
        ),
    )
    b = serialize_reconciliation(
        reconcile(["a", "b"], ["b", "c"]),
        InputProvenance(
            request=RequestProvenance("two/r.json", "9.9.9", "pkg-two"),
            profile=ProfileProvenance("two/p.json", "4.5.6", "7.8.9", "studio-two"),
        ),
    )

    assert a["inputs"] != b["inputs"]
    for key in ("satisfied", "unsatisfied", "declared_but_unrequested", "findings"):
        assert a[key] == b[key], f"{key} varied with provenance"


@pytest.mark.parametrize(
    "profile_version", ["0.0.1", "1.0.0", "99.0.0"], ids=["old", "current", "far-future"]
)
def test_profile_version_is_never_interpreted(profile_version):
    # No semver comparison, no ordering, no rejection. Declared capabilities are
    # held constant, so any variation would prove interpretation.
    doc = {**PROFILE_DOC, "profile_version": profile_version}
    prov = InputProvenance(
        request=extract_request_provenance(REQUEST_DOC, Path("r.json")),
        profile=extract_profile_provenance(doc, Path("p.json")),
    )
    payload = serialize_reconciliation(reconcile(["a", "b"], ["b"]), prov)

    assert payload["satisfied"] == ["b"]
    assert payload["unsatisfied"] == ["a"]
    assert payload["findings"] == []
    assert payload["inputs"]["profile"]["profile_version"] == profile_version


# --- human surface -----------------------------------------------------------


def test_human_traceability_lists_both_records():
    text = format_input_traceability(provenance())
    assert "Request: examples/creation_studio/pkg_request.json" in text
    assert "Package: ltb_vcarve_synthetic_example" in text
    assert "Request record version: 1.0.0" in text
    assert "Profile: examples/creation_studio/capability_profile.json" in text
    assert "Studio: cam-creation-studio" in text
    assert "Profile version: 2.3.1" in text
    assert "Profile record version: 1.0.0" in text


def test_human_traceability_omits_absent_metadata_without_placeholders():
    sparse = InputProvenance(
        request=extract_request_provenance({}, Path("r.json")),
        profile=extract_profile_provenance({}, Path("p.json")),
    )
    text = format_input_traceability(sparse)
    assert "Request: r.json" in text
    assert "Profile: p.json" in text
    for label in ("Package:", "Request record version:", "Studio:", "Profile version:"):
        assert label not in text
    for placeholder in ("None", "null", "n/a", "unknown"):
        assert placeholder not in text


def test_human_traceability_carries_no_authority_language():
    text = format_input_traceability(provenance()).lower()
    for word in ("approved", "authorized", "permitted", "blocked", "safe", "ready"):
        assert word not in text
