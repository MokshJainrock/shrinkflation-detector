from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class NormalizedMeasurement:
    value: float
    unit: str


WEIGHT_FACTORS = {
    "mg": 0.001,
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.349523125,
    "lb": 453.59237,
}

VOLUME_FACTORS = {
    "ml": 1.0,
    "l": 1000.0,
    "fl oz": 29.5735295625,
    "pt": 473.176473,
    "qt": 946.352946,
    "gal": 3785.411784,
}

COUNT_FACTORS = {
    "count": 1.0,
}

UNIT_ALIASES = {
    "milligram": "mg",
    "milligrams": "mg",
    "gram": "g",
    "grams": "g",
    "kilogram": "kg",
    "kilograms": "kg",
    "ounce": "oz",
    "ounces": "oz",
    "oz": "oz",
    "pound": "lb",
    "pounds": "lb",
    "lbs": "lb",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "fluid ounce": "fl oz",
    "fluid ounces": "fl oz",
    "fl ounce": "fl oz",
    "fl ounces": "fl oz",
    "floz": "fl oz",
    "fl oz": "fl oz",
    "pint": "pt",
    "pints": "pt",
    "quart": "qt",
    "quarts": "qt",
    "gallon": "gal",
    "gallons": "gal",
    "count": "count",
    "counts": "count",
    "ct": "count",
    "ea": "count",
    "each": "count",
    "piece": "count",
    "pieces": "count",
    "pack": "count",
    "packs": "count",
    "pk": "count",
}


def clean_text(value: str | None) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").strip().split())


def normalize_barcode(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits or None


def normalize_identifier(value: str | None) -> set[str]:
    digits = normalize_barcode(value)
    if not digits:
        return set()
    stripped = digits.lstrip("0")
    return {token for token in {digits, stripped} if token}


def primary_brand(raw_brands: str | None) -> str:
    cleaned = clean_text(raw_brands)
    if not cleaned:
        return "Unknown"
    for splitter in (",", ";", "/"):
        if splitter in cleaned:
            cleaned = cleaned.split(splitter)[0]
            break
    return clean_text(cleaned) or "Unknown"


def normalize_name(name: str | None) -> str:
    return clean_text(name)


def canonical_category(category: str | None) -> str:
    return clean_text(str(category or "").replace("-", " "))


def parse_source_timestamp(epoch_seconds) -> datetime | None:
    if epoch_seconds in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _canonical_unit(raw_unit: str | None) -> str | None:
    cleaned = clean_text(raw_unit).lower().replace(".", "")
    cleaned = cleaned.replace("fluid ounce", "fl oz")
    cleaned = cleaned.replace("fluid ounces", "fl oz")
    cleaned = cleaned.replace("fl ounces", "fl oz")
    cleaned = cleaned.replace("fl ounce", "fl oz")
    cleaned = cleaned.replace("ounces", "oz")
    cleaned = cleaned.replace("ounce", "oz")
    cleaned = cleaned.replace("pounds", "lb")
    cleaned = cleaned.replace("pound", "lb")
    return UNIT_ALIASES.get(cleaned, cleaned or None)


def normalize_measurement(value: float | int | None, unit: str | None) -> NormalizedMeasurement | None:
    if value in (None, ""):
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if numeric_value <= 0:
        return None

    canonical_unit = _canonical_unit(unit)
    if not canonical_unit:
        return None

    if canonical_unit in WEIGHT_FACTORS:
        return NormalizedMeasurement(
            value=round(numeric_value * WEIGHT_FACTORS[canonical_unit], 4),
            unit="g",
        )
    if canonical_unit in VOLUME_FACTORS:
        return NormalizedMeasurement(
            value=round(numeric_value * VOLUME_FACTORS[canonical_unit], 4),
            unit="ml",
        )
    if canonical_unit in COUNT_FACTORS:
        return NormalizedMeasurement(
            value=round(numeric_value * COUNT_FACTORS[canonical_unit], 4),
            unit="count",
        )
    return None


def parse_quantity_string(quantity_str: str | None) -> NormalizedMeasurement | None:
    text = clean_text(quantity_str).lower().replace("×", "x")
    if not text:
        return None

    multi_match = re.search(
        r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*([a-zA-Z][a-zA-Z\s.]*)",
        text,
    )
    if multi_match:
        try:
            total = float(multi_match.group(1)) * float(multi_match.group(2))
        except ValueError:
            total = None
        if total:
            normalized = normalize_measurement(total, multi_match.group(3))
            if normalized:
                return normalized

    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*([a-zA-Z][a-zA-Z\s.]*)", text):
        normalized = normalize_measurement(match.group(1), match.group(2))
        if normalized:
            return normalized

    return None


def extract_measurement(raw_product: dict) -> NormalizedMeasurement | None:
    direct_quantity = normalize_measurement(
        raw_product.get("product_quantity"),
        raw_product.get("product_quantity_unit"),
    )
    if direct_quantity:
        return direct_quantity
    return parse_quantity_string(raw_product.get("quantity"))


def build_source_key(barcode: str | None, brand: str, name: str) -> str | None:
    if barcode:
        return f"barcode:{barcode}"

    normalized_brand = primary_brand(brand)
    normalized_name = normalize_name(name)
    if normalized_brand == "Unknown" or not normalized_name:
        return None

    return f"name:{normalized_brand.lower()}::{normalized_name.lower()}"


def extract_off_product_payload(raw_product: dict, category: str) -> dict | None:
    name = normalize_name(raw_product.get("product_name"))
    if not name:
        return None

    brand = primary_brand(raw_product.get("brands"))
    barcode = normalize_barcode(raw_product.get("code"))
    measurement = extract_measurement(raw_product)
    if not measurement:
        return None

    source_key = build_source_key(barcode, brand, name)
    if not source_key:
        return None

    return {
        "name": name,
        "brand": brand,
        "category": canonical_category(category),
        "barcode": barcode,
        "image_url": raw_product.get("image_url"),
        "size_value": measurement.value,
        "size_unit": measurement.unit,
        "source_key": source_key,
        "source_last_modified_at": parse_source_timestamp(raw_product.get("last_modified_t")),
        "raw_quantity": clean_text(raw_product.get("quantity")),
    }
