"""Estrategias reutilizables de Hypothesis para el dominio de zapatillas."""

from __future__ import annotations

from typing import Any, Dict, FrozenSet

from hypothesis import strategies as st

from zapatilla import Zapatilla


_UPDATABLE_FIELDS = ("marca", "modelo", "talla", "precio", "stock")

# Se excluyen categorias de espacios y caracteres de control para garantizar
# que el primer caracter no pueda convertirse en una cadena vacia al aplicar
# str.strip(). El resto del texto incluye puntuacion y simbolos.
_NON_WHITESPACE_CHARACTERS = st.characters(
    blacklist_categories=("Cc", "Zs", "Zl", "Zp")
)


valid_text_strategy = st.text(
    alphabet=_NON_WHITESPACE_CHARACTERS,
    min_size=1,
    max_size=100,
)

valid_marca_strategy = valid_text_strategy
valid_modelo_strategy = valid_text_strategy

zapatilla_id_strategy = st.uuids()

valid_talla_strategy = st.one_of(
    st.just(20.0),
    st.just(50.0),
    st.floats(
        min_value=20.0,
        max_value=50.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
)

valid_precio_strategy = st.one_of(
    st.just(0.01),
    st.just(1_000_000.0),
    st.floats(
        min_value=0.01,
        max_value=1_000_000.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
)

valid_stock_strategy = st.integers(min_value=0, max_value=100_000)


@st.composite
def valid_zapatilla_strategy(draw: Any) -> Zapatilla:
    """Genera una instancia de :class:`Zapatilla` siempre valida."""
    return Zapatilla(
        id=draw(zapatilla_id_strategy),
        marca=draw(valid_marca_strategy),
        modelo=draw(valid_modelo_strategy),
        talla=draw(valid_talla_strategy),
        precio=draw(valid_precio_strategy),
        stock=draw(valid_stock_strategy),
    )


@st.composite
def zapatilla_update_strategy(draw: Any) -> Dict[str, object]:
    """Genera un payload parcial con uno o mas campos actualizables."""
    selected_fields: FrozenSet[str] = draw(
        st.sets(st.sampled_from(_UPDATABLE_FIELDS), min_size=1, max_size=5)
    )

    field_strategies = {
        "marca": valid_marca_strategy,
        "modelo": valid_modelo_strategy,
        "talla": valid_talla_strategy,
        "precio": valid_precio_strategy,
        "stock": valid_stock_strategy,
    }

    return {
        field: draw(field_strategies[field])
        for field in _UPDATABLE_FIELDS
        if field in selected_fields
    }


__all__ = [
    "valid_marca_strategy",
    "valid_modelo_strategy",
    "zapatilla_id_strategy",
    "valid_talla_strategy",
    "valid_precio_strategy",
    "valid_stock_strategy",
    "valid_zapatilla_strategy",
    "zapatilla_update_strategy",
]
