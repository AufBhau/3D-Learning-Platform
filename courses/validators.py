import math

from django.conf import settings
from django.core.exceptions import ValidationError

GLB_MAGIC = b"glTF"


def validate_upload_size(uploaded_file, max_bytes, label):
    if not uploaded_file:
        return uploaded_file
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise ValidationError(
            f"{label} must be at most {max_mb:g} MB (got {size / (1024 * 1024):.1f} MB)."
        )
    return uploaded_file


def validate_lesson_model_size(uploaded_file):
    return validate_upload_size(
        uploaded_file,
        getattr(settings, "MAX_LESSON_MODEL_BYTES", 20 * 1024 * 1024),
        "3D model",
    )


def validate_course_thumbnail_size(uploaded_file):
    return validate_upload_size(
        uploaded_file,
        getattr(settings, "MAX_COURSE_THUMBNAIL_BYTES", 2 * 1024 * 1024),
        "Thumbnail",
    )


def validate_lesson_model_signature(uploaded_file):
    """Reject uploads that are not real GLB/GLTF payloads (e.g. HTML renamed to .glb)."""
    if not uploaded_file:
        return uploaded_file

    name = (getattr(uploaded_file, "name", "") or "").lower()
    header = uploaded_file.read(64)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    if name.endswith(".glb"):
        if not header.startswith(GLB_MAGIC):
            raise ValidationError(
                "This file is not a valid GLB model (missing glTF header)."
            )
    elif name.endswith(".gltf"):
        stripped = header.lstrip()
        if not (stripped.startswith(b"{") or stripped.startswith(b"[")):
            raise ValidationError(
                "This file is not a valid GLTF model (expected JSON)."
            )
    return uploaded_file


def validate_lesson_model_file(uploaded_file):
    validate_lesson_model_size(uploaded_file)
    return validate_lesson_model_signature(uploaded_file)


def validate_positive_finite(value, *, label="Value", minimum=0.05):
    """Reject NaN/Inf and non-positive camera zoom factors."""
    if value is None:
        return value
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be a number.") from exc
    if math.isnan(number) or math.isinf(number):
        raise ValidationError(f"{label} must be a finite number.")
    if number <= 0:
        raise ValidationError(f"{label} must be greater than zero.")
    if number < minimum:
        raise ValidationError(f"{label} must be at least {minimum:g}.")
    return number


def validate_finite_float(value, *, label="Value"):
    if value is None:
        return value
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be a number.") from exc
    if math.isnan(number) or math.isinf(number):
        raise ValidationError(f"{label} must be a finite number.")
    return number
