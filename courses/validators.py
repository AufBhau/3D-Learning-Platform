from django.conf import settings
from django.core.exceptions import ValidationError


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
