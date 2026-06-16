from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.problem_instance import ProblemInstance


@dataclass(frozen=True)
class LoadedInstance:
    instance: ProblemInstance
    instance_id: str
    raw: dict[str, Any]


def _as_pairs(name: str, value: Any) -> list[tuple[int, int]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list, got {type(value).__name__}")
    pairs: list[tuple[int, int]] = []
    for item in value:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or not isinstance(item[0], int)
            or not isinstance(item[1], int)
        ):
            raise ValueError(f"{name} entries must be [int, int], got: {item!r}")
        pairs.append((item[0], item[1]))
    return pairs


def _require_int(data: dict[str, Any], key: str) -> int:
    if key not in data:
        raise ValueError(f"Missing required field: {key}")
    val = data[key]
    if not isinstance(val, int):
        raise ValueError(f"{key} must be int, got {type(val).__name__}")
    return val


def _optional_int(data: dict[str, Any], key: str, default: int) -> int:
    if key not in data or data[key] is None:
        return default
    val = data[key]
    if not isinstance(val, int):
        raise ValueError(f"{key} must be int, got {type(val).__name__}")
    return val


def _optional_bool(data: dict[str, Any], key: str, default: bool) -> bool:
    if key not in data or data[key] is None:
        return default
    val = data[key]
    if not isinstance(val, bool):
        raise ValueError(f"{key} must be bool, got {type(val).__name__}")
    return val


def _optional_int_list(data: dict[str, Any], key: str) -> list[int] | None:
    if key not in data or data[key] is None:
        return None
    val = data[key]
    if not isinstance(val, list) or any(not isinstance(x, int) for x in val):
        raise ValueError(f"{key} must be list[int]")
    return val


def load_instance(path: str | Path) -> LoadedInstance:
    """
    Load a benchmark instance from JSON and construct a ProblemInstance.

    Expected JSON schema (fields not mentioned are ignored):
    - instance_id: str (optional; defaults to filename stem)
    - teacher_num: int (required)
    - subjects_num: int (required)
    - classrooms_num: int (required)
    - time_slots_num: int (required)
    - lambda_1: int (optional; defaults to -1)
    - default_classrooms: bool (optional; defaults to true)
    - pensum_list: list[int] (optional; defaults to ProblemInstance default)
    - subject_hours: list[int] (optional; defaults to ProblemInstance default)
    - teacher_subject_pairs: list[[teacher:int, subject:int]] (required)
    - subject_classroom_pairs: list[[subject:int, classroom:int]] (optional)
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Instance JSON must be an object at the top level.")

    teacher_num = _require_int(raw, "teacher_num")
    subjects_num = _require_int(raw, "subjects_num")
    classrooms_num = _require_int(raw, "classrooms_num")
    time_slots_num = _require_int(raw, "time_slots_num")

    lambda_1 = _optional_int(raw, "lambda_1", default=-1)
    default_classrooms = _optional_bool(raw, "default_classrooms", default=True)
    pensum_list = _optional_int_list(raw, "pensum_list")
    subject_hours = _optional_int_list(raw, "subject_hours")

    inst = ProblemInstance(
        teacher_num=teacher_num,
        subjects_num=subjects_num,
        classrooms_num=classrooms_num,
        time_slots_num=time_slots_num,
        lambda_1=lambda_1,
        default_classrooms=default_classrooms,
        pensum_list=pensum_list,
        subject_hours=subject_hours,
    )

    ts_pairs = _as_pairs("teacher_subject_pairs", raw.get("teacher_subject_pairs"))
    if not ts_pairs:
        raise ValueError("teacher_subject_pairs is required and cannot be empty.")
    for t, s in ts_pairs:
        inst.add_teacher_subject_pair(t, s)

    sc_pairs = _as_pairs("subject_classroom_pairs", raw.get("subject_classroom_pairs"))
    for s, c in sc_pairs:
        inst.add_subject_classroom_pair(s, c)

    instance_id = raw.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id.strip():
        instance_id = p.stem

    return LoadedInstance(instance=inst, instance_id=instance_id, raw=raw)

