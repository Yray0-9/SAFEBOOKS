"""Shared input checks based on existing storage limits, without rewriting saved data."""
from decimal import Decimal, DecimalException, localcontext
import re

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db.models import CharField, EmailField, TextField


def text_value_error(value, label):
    if value is not None and not isinstance(value, (str, int, float, Decimal)):
        return f"{label} must be text."
    if isinstance(value, bool):
        return f"{label} must be text."
    if "\x00" in str(value or ""):
        return f"{label} cannot contain null characters."
    return None


def valid_formatted_tin(value):
    text = str(value or "").strip()
    return bool(re.fullmatch(r"[0-9\s-]+", text)) and sum("0" <= char <= "9" for char in text) == 12


def model_text_errors(model, values, *, labels=None):
    """Validate only submitted text fields; errors never include submitted values."""
    errors = []
    for name, value in values.items():
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            continue
        if not isinstance(field, (CharField, TextField)):
            continue
        label = (labels or {}).get(name) or str(field.verbose_name).capitalize()
        error = text_value_error(value, label)
        if error:
            errors.append(error)
            continue
        text = str(value if value is not None else "").strip()
        if field.max_length is not None and len(text) > field.max_length:
            errors.append(f"{label} must be {field.max_length} characters or fewer.")
        if isinstance(field, EmailField) and text:
            try:
                validate_email(text)
            except ValidationError:
                errors.append("Email format is invalid.")
    return errors


def decimal_field_max(model, field_name):
    field = model._meta.get_field(field_name)
    return Decimal(10) ** (field.max_digits - field.decimal_places) - Decimal(1).scaleb(-field.decimal_places)


def parse_finite_decimal(value, *, label):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, f"{label} is required."
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None, f"{label} must be a valid number."
    try:
        text = str(value).strip()
        amount = Decimal(text)
        if not amount.is_finite():
            return None, f"{label} must be a finite number."
        if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", text):
            return None, f"{label} must be a valid number."
        return amount, None
    except (DecimalException, TypeError, ValueError, OverflowError):
        return None, f"{label} must be a valid number."


def normalize_nonnegative_decimal(value, *, label, maximum, optional=False, raw_maximum=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        return (Decimal("0.00"), None) if optional else (None, f"{label} is required.")
    amount, error = parse_finite_decimal(value, label=label)
    if error:
        return None, error
    try:
        if amount < 0:
            return None, f"{label} cannot be negative."
        # Bound before quantization too, so enormous exponents never reach arithmetic.
        exceeds_limit = amount > maximum if raw_maximum else amount >= maximum + Decimal("0.01")
        if exceeds_limit:
            return None, f"{label} must be {maximum} or less."
        with localcontext() as context:
            context.prec = max(28, len(maximum.as_tuple().digits) + 1)
            rounded = amount.quantize(Decimal("0.01"))
        if rounded > maximum:
            return None, f"{label} must be {maximum} or less after rounding."
        return rounded, None
    except (DecimalException, TypeError, ValueError, OverflowError):
        return None, f"{label} must be a valid number."
