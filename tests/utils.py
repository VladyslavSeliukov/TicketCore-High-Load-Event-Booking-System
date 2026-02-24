import pytest

def get_missing_field_cases(payload: dict):
    cases = []

    cases.append(pytest.param('all', {}, id='missing_all_fields'))

    for field in payload:
        bad_payload = payload.copy()
        del bad_payload[field]
        cases.append(pytest.param(field, bad_payload, id=f'missing_{field}'))

    return cases