"""Invariantes CRUD con estado nuevo por cada ejemplo de Hypothesis."""

from dataclasses import asdict, replace

import pytest
from hypothesis import given, settings, strategies as st

from zapatilla import (
    Zapatilla,
    ZapatillaNotFoundError,
    ZapatillaRepository,
    ZapatillaValidationError,
)

from .strategies import (
    valid_zapatilla_strategy,
    zapatilla_id_strategy,
    zapatilla_update_strategy,
)


@st.composite
def collection_and_target_strategy(draw):
    """Genera una colección con IDs únicos y selecciona cualquier elemento."""
    zapatillas = draw(
        st.lists(
            valid_zapatilla_strategy(),
            min_size=1,
            max_size=12,
            unique_by=lambda zapatilla: zapatilla.id,
        )
    )
    target = draw(st.sampled_from(zapatillas))
    return zapatillas, target


def snapshot(repo: ZapatillaRepository) -> dict:
    """Copia los valores públicos sin depender del orden ni de referencias."""
    return {zapatilla.id: asdict(zapatilla) for zapatilla in repo.list_all()}


@settings(max_examples=100)
@given(scenario=collection_and_target_strategy())
def test_create_increases_size_and_preserves_existing_entities(scenario):
    repo = ZapatillaRepository()
    zapatillas, target = scenario
    for zapatilla in zapatillas:
        if zapatilla.id != target.id:
            repo.create(zapatilla)
    before = snapshot(repo)
    expected_target = asdict(target)

    created = repo.create(target)

    assert isinstance(created, Zapatilla)
    assert asdict(created) == expected_target
    assert len(repo.list_all()) == len(before) + 1
    assert snapshot(repo) == {**before, target.id: expected_target}
    assert asdict(repo.get_by_id(target.id)) == expected_target


@settings(max_examples=100)
@given(
    scenario=collection_and_target_strategy(),
    replacement=valid_zapatilla_strategy(),
)
def test_create_duplicate_id_fails_without_changing_state(scenario, replacement):
    repo = ZapatillaRepository()
    zapatillas, target = scenario
    for zapatilla in zapatillas:
        repo.create(zapatilla)
    before = snapshot(repo)

    # Un producto generado independientemente colisiona por ID, no por contenido.
    duplicate = replace(replacement, id=target.id)
    # El repositorio existente usa KeyError para claves duplicadas.
    with pytest.raises(KeyError):
        repo.create(duplicate)

    assert len(repo.list_all()) == len(before)
    assert snapshot(repo) == before
    assert asdict(repo.get_by_id(target.id)) == before[target.id]


@settings(max_examples=100)
@given(
    scenario=collection_and_target_strategy(),
    repetitions=st.integers(min_value=2, max_value=6),
)
def test_read_round_trip_and_repeated_queries_preserve_state(scenario, repetitions):
    repo = ZapatillaRepository()
    zapatillas, target = scenario
    expected = {zapatilla.id: asdict(zapatilla) for zapatilla in zapatillas}
    for zapatilla in zapatillas:
        repo.create(zapatilla)
    first_listing = repo.list_all()

    for _ in range(repetitions):
        retrieved = repo.get_by_id(target.id)
        assert isinstance(retrieved, Zapatilla)
        assert asdict(retrieved) == expected[target.id]

        listing = repo.list_all()
        assert len(listing) == len(expected)
        assert {item.id: asdict(item) for item in listing} == expected
        assert listing == first_listing
        assert snapshot(repo) == expected


@settings(max_examples=100)
@given(
    scenario=collection_and_target_strategy(),
    updates=zapatilla_update_strategy(),
)
def test_update_preserves_identity_omitted_fields_and_other_entities(scenario, updates):
    repo = ZapatillaRepository()
    zapatillas, target = scenario
    for zapatilla in zapatillas:
        repo.create(zapatilla)
    before = snapshot(repo)
    original_updates = dict(updates)
    previous_listing = repo.list_all()
    expected_target = {**before[target.id], **updates}

    updated = repo.update(target.id, updates)

    assert isinstance(updated, Zapatilla)
    assert updated.id == target.id
    for field, previous_value in before[target.id].items():
        assert getattr(updated, field) == updates.get(field, previous_value)
    assert asdict(updated) == expected_target
    assert asdict(repo.get_by_id(target.id)) == expected_target
    assert len(repo.list_all()) == len(before)
    assert snapshot(repo) == {**before, target.id: expected_target}
    assert updates == original_updates
    # Las instantáneas anteriores tampoco deben mutar al actualizar.
    assert {item.id: asdict(item) for item in previous_listing} == before


@settings(max_examples=100)
@given(
    scenario=collection_and_target_strategy(),
    updates=zapatilla_update_strategy(),
    invalid_price=st.one_of(
        st.integers(max_value=0),
        st.floats(max_value=0, allow_nan=False, allow_infinity=False),
    ),
)
def test_update_invalid_price_is_atomic(scenario, updates, invalid_price):
    repo = ZapatillaRepository()
    zapatillas, target = scenario
    for zapatilla in zapatillas:
        repo.create(zapatilla)
    before = snapshot(repo)

    # Mezclar campos válidos e inválidos detecta aplicaciones parciales del update.
    invalid_updates = {**updates, "precio": invalid_price}
    with pytest.raises(ZapatillaValidationError):
        repo.update(target.id, invalid_updates)

    assert len(repo.list_all()) == len(before)
    assert snapshot(repo) == before
    assert asdict(repo.get_by_id(target.id)) == before[target.id]


@settings(max_examples=100)
@given(
    scenario=collection_and_target_strategy(),
    updates=zapatilla_update_strategy(),
    proposed_id=zapatilla_id_strategy,
)
def test_update_rejects_id_field_without_changing_state(scenario, updates, proposed_id):
    repo = ZapatillaRepository()
    zapatillas, target = scenario
    for zapatilla in zapatillas:
        repo.create(zapatilla)
    before = snapshot(repo)

    # El campo id está prohibido incluso si se propone su valor actual.
    with pytest.raises(ZapatillaValidationError):
        repo.update(target.id, {**updates, "id": proposed_id})

    assert len(repo.list_all()) == len(before)
    assert snapshot(repo) == before
    assert asdict(repo.get_by_id(target.id)) == before[target.id]


@settings(max_examples=100)
@given(
    scenario=collection_and_target_strategy(),
    updates=zapatilla_update_strategy(),
)
def test_update_missing_id_raises_domain_error_without_changing_state(scenario, updates):
    repo = ZapatillaRepository()
    zapatillas, missing = scenario
    for zapatilla in zapatillas:
        if zapatilla.id != missing.id:
            repo.create(zapatilla)
    before = snapshot(repo)

    assert repo.get_by_id(missing.id) is None
    with pytest.raises(ZapatillaNotFoundError):
        repo.update(missing.id, updates)

    assert len(repo.list_all()) == len(before)
    assert snapshot(repo) == before
    assert repo.get_by_id(missing.id) is None


@settings(max_examples=100)
@given(
    scenario=collection_and_target_strategy(),
    repetitions=st.integers(min_value=2, max_value=6),
)
def test_delete_removes_only_target_and_repeated_deletes_are_idempotent(
    scenario, repetitions
):
    repo = ZapatillaRepository()
    zapatillas, target = scenario
    for zapatilla in zapatillas:
        repo.create(zapatilla)
    before = snapshot(repo)
    expected = {id: values for id, values in before.items() if id != target.id}

    assert repo.delete(target.id) is True
    assert repo.get_by_id(target.id) is None
    assert len(repo.list_all()) == len(before) - 1
    assert snapshot(repo) == expected

    for _ in range(repetitions):
        for id, values in expected.items():
            assert asdict(repo.get_by_id(id)) == values
        assert repo.get_by_id(target.id) is None
        assert repo.delete(target.id) is False
        assert len(repo.list_all()) == len(before) - 1
        assert snapshot(repo) == expected
        assert repo.get_by_id(target.id) is None
