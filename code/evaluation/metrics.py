"""Answer metrics shared by online and offline evaluation."""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


CURRENCY_CODES = {
    "USD",
    "EUR",
    "GBP",
    "CAD",
    "AUD",
    "INR",
    "JPY",
    "CNY",
    "RMB",
    "CHF",
    "NZD",
    "SGD",
    "HKD",
}

SMALL_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

TENS_NUMBER_WORDS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def normalize_text(text: Any) -> str:
    text = "" if text is None else str(text)
    text = text.strip()
    text = re.sub(r"^\\boxed\s*\{(.*)\}$", r"\1", text, flags=re.S)
    text = text.strip().strip("`").strip()
    text = re.sub(r"^(?:the\s+answer\s+is|answer|result)\s*[:：]\s*", "", text, flags=re.I)
    text = text.strip().strip("\"'")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*[:：]\s*", " : ", text)
    return text.strip().rstrip(".").lower()


def normalize_list_item(text: Any) -> str:
    item = normalize_text(text)
    # A minus sign is part of a value, including inside a JSON array.
    # Remove only an actual list marker followed by whitespace.
    item = re.sub(r"^(?:[-*•]\s+)+", "", item).strip()
    item = re.sub(r"\s+", " ", item)
    item = re.sub(r"\s*[:：]\s*", " : ", item)
    return item.strip().rstrip(".")


def _try_parse_json_list(text: str) -> Optional[list[Any]]:
    s = str(text).strip()
    if not (s.startswith("[") and s.endswith("]")):
        return None
    try:
        parsed = json.loads(s)
    except Exception:
        return None
    return parsed if isinstance(parsed, list) else None


def split_list_answer(text: str) -> list[str]:
    parsed = _try_parse_json_list(text)
    if parsed is not None:
        return [normalize_list_item(item) for item in parsed]

    cleaned = str(text).strip()
    cleaned = re.sub(r"^\\boxed\s*\{(.*)\}$", r"\1", cleaned, flags=re.S).strip()
    cleaned = re.sub(r"^(?:the\s+answer\s+is|answer|result)\s*[:：]\s*", "", cleaned, flags=re.I).strip()

    # Some benchmark records use comma-separated lists. Also accept
    # newline-separated output when the model renders one item per line.
    if "," in cleaned:
        parts = cleaned.split(",")
    else:
        parts = cleaned.splitlines()
    return [normalize_list_item(part) for part in parts]


def split_ordered_list_answer(text: str) -> list[str]:
    """Split an ordered one-value-per-line answer without treating value commas as separators."""

    parsed = _try_parse_json_list(text)
    if parsed is not None:
        return [normalize_list_item(item) for item in parsed]

    cleaned = str(text).strip()
    cleaned = re.sub(r"^\\boxed\s*\{(.*)\}$", r"\1", cleaned, flags=re.S).strip()
    cleaned = re.sub(r"^(?:the\s+answer\s+is|answer|result)\s*[:：]\s*", "", cleaned, flags=re.I).strip()
    if not cleaned:
        return []
    return [normalize_list_item(line) for line in cleaned.splitlines()]


def extract_numbers(text: str) -> list[float]:
    numbers = []
    # Do not remove commas globally before matching: 1,234 should be one
    # number, while comma-separated IDs should remain separable for list metrics.
    pattern = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    for match in re.findall(pattern, str(text)):
        try:
            numbers.append(float(match.replace(",", "")))
        except ValueError:
            pass
    return numbers


def parse_number_words(text: Any) -> Optional[float]:
    normalized = normalize_text(text).replace("-", " ")
    tokens = [tok for tok in normalized.split() if tok != "and"]
    if not tokens:
        return None

    def parse_under_100(parts: list[str]) -> Optional[int]:
        if len(parts) == 1:
            token = parts[0]
            if token in SMALL_NUMBER_WORDS:
                return SMALL_NUMBER_WORDS[token]
            return TENS_NUMBER_WORDS.get(token)
        if len(parts) == 2 and parts[0] in TENS_NUMBER_WORDS and parts[1] in SMALL_NUMBER_WORDS:
            ones = SMALL_NUMBER_WORDS[parts[1]]
            return TENS_NUMBER_WORDS[parts[0]] + ones if ones else None
        return None

    def parse_under_1000(parts: list[str]) -> Optional[int]:
        if not parts:
            return None
        if "hundred" not in parts:
            return parse_under_100(parts)
        if len(parts) < 2 or parts[1] != "hundred" or parts[0] not in SMALL_NUMBER_WORDS:
            return None
        hundreds = SMALL_NUMBER_WORDS[parts[0]]
        if not hundreds:
            return None
        if len(parts) == 2:
            return hundreds * 100
        remainder = parse_under_100(parts[2:])
        return hundreds * 100 + remainder if remainder is not None else None

    if "thousand" not in tokens:
        value = parse_under_1000(tokens)
        return float(value) if value is not None else None
    if tokens.count("thousand") != 1:
        return None
    split_at = tokens.index("thousand")
    thousands = parse_under_1000(tokens[:split_at])
    remainder = parse_under_1000(tokens[split_at + 1 :]) if tokens[split_at + 1 :] else 0
    if thousands is None or remainder is None or thousands == 0:
        return None
    return float(thousands * 1000 + remainder)


def extract_currency_codes(text: str) -> set[str]:
    code_pattern = "|".join(sorted(CURRENCY_CODES))
    matches = re.findall(rf"(?<![A-Za-z])(?:{code_pattern})(?![A-Za-z])", str(text), flags=re.I)
    return {match.upper() for match in matches}


def numbers_match(pred_value: float, gold_value: float) -> bool:
    tolerance = max(1e-2, abs(gold_value) * 1e-3)
    return math.isfinite(pred_value) and math.isfinite(gold_value) and abs(pred_value - gold_value) <= tolerance


def _strip_scalar_number_affixes(text: Any) -> str:
    value = str(text)
    value = re.sub(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", " ", value)
    if CURRENCY_CODES:
        code_pattern = "|".join(sorted(CURRENCY_CODES))
        value = re.sub(rf"(?<![A-Za-z])(?:{code_pattern})(?![A-Za-z])", " ", value, flags=re.I)
    value = re.sub(r"(?<![A-Za-z])(?:US|AU|CA|HK|NZ|SG|NT)(?=\s*[$€£¥₹₩₽₺₴₫฿₱₪₦₭₲₵₡₢₣₤₥₧₨₮₯₠₸₼₾₿])", " ", value, flags=re.I)
    value = re.sub(r"[%$€£¥₹₩₽₺₴₫฿₱₪₦₭₲₵₡₢₣₤₥₧₨₮₯₠₸₼₾₿]", " ", value)
    value = re.sub(r"[\s,.:;_\\/+\-()\\[\\]{}]+", " ", value)
    return value.strip()


def numeric_scalar_match(prediction: Any, gold: Any) -> bool:
    pred_value = parse_numeric_scalar(prediction)
    gold_value = parse_numeric_scalar(gold)
    if pred_value is None or gold_value is None:
        return False
    gold_currencies = extract_currency_codes(str(gold))
    if gold_currencies and not gold_currencies.issubset(extract_currency_codes(str(prediction))):
        return False
    return numbers_match(pred_value, gold_value)


def parse_numeric_scalar(text: Any) -> Optional[float]:
    """Parse a complete scalar answer, including standard currency formatting."""
    normalized = normalize_text(text)
    currency = "(?:" + "|".join(sorted(CURRENCY_CODES)) + r"|(?:US|AU|CA|HK|NZ|SG|NT)?[$€£¥₹₩₽])"
    number = r"[-+]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"
    match = re.fullmatch(
        rf"(?:{currency}\s*)?({number})(?:\s*(?:{currency}|%))?",
        normalized, flags=re.I,
    )
    if match:
        value = float(match.group(1).replace(",", ""))
    else:
        value = parse_number_words(normalized)
    return value if value is not None and math.isfinite(value) else None


def exact_number_match(prediction: str, gold: str) -> bool:
    """Compare complete finite decimal scalars without a tolerance or float rounding.

    This opt-in contract is for direct numeric extraction, including tiny values.
    Answer-wrapper extraction belongs to the caller, as with evaluation.replay.
    """
    pattern = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
    values = []
    for text in (prediction, gold):
        scalar = str(text).strip()
        if not re.fullmatch(pattern, scalar):
            return False
        try:
            value = Decimal(scalar)
        except InvalidOperation:
            return False
        if not value.is_finite():
            return False
        values.append(value)
    return values[0] == values[1]


def accuracy_string(prediction: str, gold: str) -> bool:
    return normalize_text(prediction) == normalize_text(gold) or numeric_scalar_match(prediction, gold)


def contains_match(prediction: str, gold: str) -> bool:
    pred = normalize_text(prediction)
    target = normalize_text(gold)
    return bool(target) and target in pred


def unordered_list_str_match(prediction: str, gold: str) -> bool:
    return unordered_list_str_score(prediction, gold) >= 1.0


def unordered_list_str_score(prediction: str, gold: str) -> float:
    pred_items = split_list_answer(prediction)
    gold_items = split_list_answer(gold)
    if not pred_items and not gold_items:
        return 0.0
    if not gold_items:
        return 0.0
    if _gold_looks_like_id_value_pairs(gold_items):
        return unordered_id_value_pair_score(pred_items, gold_items)
    # Empty slots count toward length but cannot match an answer value.
    # Maximum one-to-one matching preserves multiplicity. Greedy matching can
    # undercount when numerical tolerance lets one value match several others.
    owner: dict[int, int] = {}

    def augment(gold_index: int, seen: set[int]) -> bool:
        for pred_index, pred in enumerate(pred_items):
            if pred_index in seen or not _pair_value_match(pred, gold_items[gold_index]):
                continue
            seen.add(pred_index)
            if pred_index not in owner or augment(owner[pred_index], seen):
                owner[pred_index] = gold_index
                return True
        return False

    overlap = sum(augment(index, set()) for index in range(len(gold_items)))
    return overlap / max(len(pred_items), len(gold_items), 1)


def ordered_list_str_match(prediction: str, gold: str) -> bool:
    return ordered_list_str_score(prediction, gold) >= 1.0


def ordered_list_str_score(prediction: str, gold: str) -> float:
    pred_items = split_ordered_list_answer(prediction)
    gold_items = split_ordered_list_answer(gold)
    if not pred_items and not gold_items:
        return 0.0
    if not gold_items:
        return 0.0
    matched = sum(
        _pair_value_match(pred_value, gold_value)
        for pred_value, gold_value in zip(pred_items, gold_items)
    )
    return matched / max(len(pred_items), len(gold_items), 1)


def _split_id_value_pair(item: str) -> Optional[tuple[str, str]]:
    if " : " not in item:
        return None
    key, value = item.split(" : ", 1)
    key = normalize_list_item(key)
    value = value.strip()
    if not key or not value:
        return None
    return key, value


def _gold_looks_like_id_value_pairs(gold_items: list[str]) -> bool:
    return bool(gold_items) and all(_split_id_value_pair(item) is not None for item in gold_items)


def _pair_value_match(pred_value: str, gold_value: str) -> bool:
    pred = normalize_list_item(pred_value)
    gold = normalize_list_item(gold_value)
    return bool(pred and gold) and (pred == gold or numeric_scalar_match(pred_value, gold_value))


def unordered_id_value_pair_match(pred_items: list[str], gold_items: list[str]) -> bool:
    return unordered_id_value_pair_score(pred_items, gold_items) >= 1.0


def unordered_id_value_pair_score(pred_items: list[str], gold_items: list[str]) -> float:
    pred_pairs = [_split_id_value_pair(item) for item in pred_items]
    gold_pairs = [_split_id_value_pair(item) for item in gold_items]
    if any(pair is None for pair in gold_pairs):
        return 0.0
    valid_pred_pairs = [pair for pair in pred_pairs if pair is not None]
    valid_gold_pairs = [pair for pair in gold_pairs if pair is not None]
    used_pred = set()
    matched = 0
    for gold_key, gold_value in valid_gold_pairs:
        for pred_idx, pred_pair in enumerate(valid_pred_pairs):
            if pred_idx in used_pred:
                continue
            pred_key, pred_value = pred_pair
            if pred_key == gold_key and _pair_value_match(pred_value, gold_value):
                used_pred.add(pred_idx)
                matched += 1
                break
    return matched / max(len(pred_items), len(gold_items), 1)


def approx_number_match(prediction: str, gold: str) -> bool:
    return numeric_scalar_match(prediction, gold)


def score_prediction(prediction: str, gold: str, metric_type: str) -> bool:
    return score_prediction_value(prediction, gold, metric_type) >= 1.0


def score_prediction_value(prediction: str, gold: str, metric_type: str) -> float:
    if metric_type == "exact_number_match":
        return float(exact_number_match(prediction, gold))
    if not normalize_text(prediction) or not normalize_text(gold):
        return 0.0
    if metric_type in {"ordered_list_str_match", "unordered_list_str_match"}:
        for value in (prediction, gold):
            text = str(value).strip()
            if text.startswith("[") or text.endswith("]"):
                parsed = _try_parse_json_list(text)
                if not parsed or any(isinstance(item, (dict, list)) or item is None for item in parsed):
                    return 0.0
    if metric_type == "accuracy_string":
        return 1.0 if accuracy_string(prediction, gold) else 0.0
    if metric_type == "unordered_list_str_match":
        return unordered_list_str_score(prediction, gold)
    if metric_type == "ordered_list_str_match":
        return ordered_list_str_score(prediction, gold)
    if metric_type == "approx_number_match":
        return 1.0 if approx_number_match(prediction, gold) else 0.0
    return 1.0 if accuracy_string(prediction, gold) else 0.0
