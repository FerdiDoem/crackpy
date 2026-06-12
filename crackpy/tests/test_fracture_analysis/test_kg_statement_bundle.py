from crackpy.results.kg_statement_bundle import envelope_to_kg_statement_bundle
from crackpy.fracture_analysis.methods.cjp_fit import build_cjp_fit_envelope_from_result
from crackpy.fracture_analysis.methods.williams_fit import build_williams_fit_envelope_from_analysis
from crackpy.tests.test_fracture_analysis.test_cjp_provenance import _typed_cjp_inputs, _typed_cjp_result
from crackpy.tests.test_fracture_analysis.test_williams_provenance import _fake_analysis


def test_envelope_to_kg_statement_bundle_exports_result_and_quantity_statements():
    envelope = build_williams_fit_envelope_from_analysis(_fake_analysis(), crackpy_version="test-version")
    bundle = envelope_to_kg_statement_bundle(envelope)
    payload = bundle.to_dict()

    assert payload["bundle_schema_version"] == "crackpy.kg_statement_bundle.williams_fit.v1"
    assert payload["uri_policy"] == "local IDs only; URI minting belongs to exporter or KG importer policy"
    assert "ResultQuantity" in payload["groups"]

    statements = payload["statements"]
    keys = {(item["metadata_type"], item["key"]) for item in statements}
    assert ("CrackPyAnalysisResult", "crackpy_result_schema_version") in keys
    assert ("CrackPyAnalysis", "crackpy_method_id") in keys
    assert ("ResultQuantity", "crackpy_quantity_symbol") in keys
    assert any(item["value"] == "K_I" and item["unit"] == "1" for item in statements)
    assert all(item["subject_uri"] is None for item in statements)


def test_envelope_to_kg_statement_bundle_uses_cjp_envelope_schema():
    frame, parameters, _ = _typed_cjp_inputs()
    envelope = build_cjp_fit_envelope_from_result(
        input_id="input:demo",
        data_ref="DemoNodemap.txt",
        source_label="demo",
        crack_tip_frame=frame,
        parameters=parameters,
        result=_typed_cjp_result(),
        crackpy_version="test-version",
    )

    payload = envelope_to_kg_statement_bundle(envelope).to_dict()

    assert payload["bundle_schema_version"] == "crackpy.kg_statement_bundle.cjp_fit.v1"
    assert any(item["value"] == "K_II" for item in payload["statements"])
