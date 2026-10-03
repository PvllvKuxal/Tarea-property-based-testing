"""Entidad de dominio y repositorio en memoria para zapatillas."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple, Union
from uuid import UUID


ZapatillaId = Union[int, str, UUID]
Number = Union[int, float]


class ZapatillaValidationError(ValueError):
    """Indica que una zapatilla no cumple sus invariantes de dominio."""


class ZapatillaNotFoundError(KeyError):
    """Indica que el identificador solicitado no esta en el repositorio."""


def _validate_id(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, str, UUID)):
        raise ZapatillaValidationError(
            "id debe ser un entero, una cadena o un UUID"
        )

    if isinstance(value, str) and not value.strip():
        raise ZapatillaValidationError("id no puede ser una cadena vacia")


def _validate_text(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise ZapatillaValidationError(f"{field_name} debe ser una cadena")
    if not value.strip():
        raise ZapatillaValidationError(f"{field_name} no puede estar vacio")


def _validate_number(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ZapatillaValidationError(f"{field_name} debe ser numerico")
    if isinstance(value, float) and not math.isfinite(value):
        raise ZapatillaValidationError(f"{field_name} debe ser finito")


@dataclass(frozen=True)
class Zapatilla:
    """Producto con las reglas de negocio de una zapatilla."""

    id: ZapatillaId
    marca: str
    modelo: str
    talla: Number
    precio: Number
    stock: int

    def __post_init__(self) -> None:
        _validate_id(self.id)
        _validate_text(self.marca, "marca")
        _validate_text(self.modelo, "modelo")
        _validate_number(self.talla, "talla")
        _validate_number(self.precio, "precio")

        if not 20.0 <= self.talla <= 50.0:
            raise ZapatillaValidationError("talla debe estar entre 20.0 y 50.0")
        if self.precio <= 0:
            raise ZapatillaValidationError("precio debe ser mayor que cero")
        if isinstance(self.stock, bool) or not isinstance(self.stock, int):
            raise ZapatillaValidationError("stock debe ser un entero")
        if self.stock < 0:
            raise ZapatillaValidationError("stock no puede ser negativo")


class ZapatillaRepository:
    """Repositorio CRUD en memoria, indexado por el ID de la zapatilla."""

    _UPDATABLE_FIELDS = frozenset(("marca", "modelo", "talla", "precio", "stock"))

    def __init__(self) -> None:
        self._items: Dict[ZapatillaId, Zapatilla] = {}

    def create(self, zapatilla: Zapatilla) -> Zapatilla:
        """Agrega una zapatilla y falla si su ID ya esta registrado."""
        if not isinstance(zapatilla, Zapatilla):
            raise TypeError("zapatilla debe ser una instancia de Zapatilla")
        if zapatilla.id in self._items:
            raise KeyError(f"Ya existe una zapatilla con id {zapatilla.id!r}")

        self._items[zapatilla.id] = zapatilla
        return zapatilla

    def get_by_id(self, id: ZapatillaId) -> Optional[Zapatilla]:
        """Retorna la zapatilla indicada o None cuando no existe."""
        _validate_id(id)
        return self._items.get(id)

    def list_all(self) -> Tuple[Zapatilla, ...]:
        """Retorna una instantanea inmutable de las zapatillas almacenadas."""
        return tuple(self._items.values())

    def update(
        self, id: ZapatillaId, updates: Mapping[str, object]
    ) -> Zapatilla:
        """Actualiza campos permitidos sin cambiar el ID original."""
        _validate_id(id)
        if id not in self._items:
            raise ZapatillaNotFoundError(
                f"No existe una zapatilla con id {id!r}"
            )
        if not isinstance(updates, Mapping):
            raise TypeError("updates debe ser un mapping")

        invalid_fields = set(updates).difference(self._UPDATABLE_FIELDS)
        if invalid_fields:
            invalid = ", ".join(repr(field) for field in invalid_fields)
            raise ZapatillaValidationError(
                f"Campos no actualizables: {invalid}"
            )

        current = self._items[id]
        updated = Zapatilla(
            id=current.id,
            marca=updates.get("marca", current.marca),
            modelo=updates.get("modelo", current.modelo),
            talla=updates.get("talla", current.talla),
            precio=updates.get("precio", current.precio),
            stock=updates.get("stock", current.stock),
        )
        self._items[id] = updated
        return updated

    def delete(self, id: ZapatillaId) -> bool:
        """Elimina una zapatilla y retorna si existia."""
        _validate_id(id)
        if id not in self._items:
            return False

        del self._items[id]
        return True
