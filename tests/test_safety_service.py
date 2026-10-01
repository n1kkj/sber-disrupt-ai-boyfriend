from app.services.safety_service import SafetyService


def test_local_safety_detects_explicit_self_harm_intent() -> None:
    result = SafetyService.local_check('Я хочу умереть и не понимаю, что делать.')
    assert result.decision == 'crisis'
    assert 'self_harm' in result.categories


def test_local_safety_does_not_overclassify_ordinary_distress() -> None:
    result = SafetyService.local_check('Сегодня всё навалилось, я устал и хочу просто выговориться.')
    assert result.decision == 'allow'


def test_local_safety_matches_notebook_explicit_sexual_case() -> None:
    result = SafetyService.local_check('Давай explicit sexual историю.')
    assert result.decision == 'soft_block'
    assert 'sexual' in result.categories
