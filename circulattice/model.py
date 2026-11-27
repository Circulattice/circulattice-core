# SPDX-License-Identifier: Apache-2.0
"""Validate the version 1 JSON model and give all algorithms a canonical order."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

MAX_BYTES = 1_048_576
MAX_PARTICIPANTS = 64
MAX_POOLS = 32
MAX_OBLIGATIONS = 256
MAX_AMOUNT = 10**15
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")


@dataclass(frozen=True)
class Pool:
    agreement: str
    currency: str
    members: tuple[str, ...]
    funding: Mapping[str, int]


@dataclass(frozen=True)
class Obligation:
    id: str
    debtor: str
    creditor: str
    agreement: str
    currency: str
    amount: int
    eligible: bool


@dataclass(frozen=True)
class Problem:
    participants: tuple[str, ...]
    pools: tuple[Pool, ...]
    obligations: tuple[Obligation, ...]


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_decimal(_: str) -> Any:
    raise ValueError("only integer JSON numbers are accepted")


def _check_depth(value: Any, depth: int = 0) -> None:
    if isinstance(value, (dict, list)):
        if depth >= 16:
            raise ValueError("JSON nesting exceeds 16 containers")
        for child in value.values() if isinstance(value, dict) else value:
            _check_depth(child, depth + 1)


def load_json(path: str | Path) -> Any:
    """Read at most 1 MiB of UTF-8 JSON; reject duplicate keys at every level."""
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("file exceeds 1 MiB")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_fields,
            parse_float=_reject_decimal,
            parse_constant=_reject_decimal,
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds parser limit") from exc
    _check_depth(value)
    return value


def _fields(value: Any, keys: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ValueError(f"object must contain exactly {keys}")
    return value


def _rows(value: Any, limit: int, name: str) -> list[Any]:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{name} must be an array with at most {limit} entries")
    return value


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError("invalid identifier")
    return value


def _names(raw: Any, name: str) -> tuple[str, ...]:
    names = [_identifier(i) for i in _rows(raw, MAX_PARTICIPANTS, name)]
    if not names or len(set(names)) != len(names):
        raise ValueError(f"{name} must be nonempty and contain unique identifiers")
    return tuple(sorted(names))


def _money(value: Any, low: int) -> int:
    if type(value) is not int or not low <= value <= MAX_AMOUNT:
        raise ValueError(f"minor units must be integers between {low} and {MAX_AMOUNT}")
    return value


def parse_problem(raw: Any) -> Problem:
    """Decode a JSON value. Use this factory before calling solve or check."""
    fields = _fields(raw, "version participants pools obligations")
    if type(fields["version"]) is not int or fields["version"] != 1:
        raise ValueError("unsupported version")
    participants = _names(fields["participants"], "participants")
    pools: dict[tuple[str, str], Pool] = {}
    for row in _rows(fields["pools"], MAX_POOLS, "pools"):
        _fields(row, "agreement currency members funding")
        agreement = _identifier(row["agreement"])
        currency = _identifier(row["currency"])
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("currency must have three uppercase ASCII letters")
        key = (agreement, currency)
        members = _names(row["members"], "members")
        if key in pools or not set(members).issubset(participants):
            raise ValueError("duplicate pool or unregistered member")
        funding = row["funding"]
        if not isinstance(funding, dict) or set(funding) != set(members):
            raise ValueError("funding must cover exactly the members of each pool")
        caps = MappingProxyType({member: _money(funding[member], 0) for member in members})
        pools[key] = Pool(agreement, currency, members, caps)

    obligations: dict[str, Obligation] = {}
    for row in _rows(fields["obligations"], MAX_OBLIGATIONS, "obligations"):
        _fields(row, "id debtor creditor agreement currency amount eligible")
        oid = _identifier(row["id"])
        key = (_identifier(row["agreement"]), _identifier(row["currency"]))
        debtor, creditor = _identifier(row["debtor"]), _identifier(row["creditor"])
        if oid in obligations or debtor == creditor:
            raise ValueError("duplicate obligation id or self-payment")
        if key not in pools or not {debtor, creditor}.issubset(pools[key].members):
            raise ValueError("endpoints must be members of the named pool")
        if type(row["eligible"]) is not bool:
            raise ValueError("eligible must be boolean")
        obligations[oid] = Obligation(
            oid, debtor, creditor, *key, _money(row["amount"], 1), row["eligible"]
        )
    return Problem(
        participants,
        tuple(pools[k] for k in sorted(pools)),
        tuple(obligations[i] for i in sorted(obligations)),
    )
