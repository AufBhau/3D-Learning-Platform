import json
import struct
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from courses.models import Annotation, Course, Lesson


def _pad4(data: bytes, pad_byte: bytes = b"\x00") -> bytes:
    padding = (4 - (len(data) % 4)) % 4
    return data + (pad_byte * padding)


def build_box_glb() -> bytes:
    """Build a tiny axis-aligned box as a binary .glb (no extra deps)."""
    positions = [
        -0.5, -0.5, 0.5,
         0.5, -0.5, 0.5,
         0.5,  0.5, 0.5,
        -0.5,  0.5, 0.5,
        -0.5, -0.5, -0.5,
         0.5, -0.5, -0.5,
         0.5,  0.5, -0.5,
        -0.5,  0.5, -0.5,
    ]
    normals = [
        -0.577, -0.577, 0.577,
         0.577, -0.577, 0.577,
         0.577,  0.577, 0.577,
        -0.577,  0.577, 0.577,
        -0.577, -0.577, -0.577,
         0.577, -0.577, -0.577,
         0.577,  0.577, -0.577,
        -0.577,  0.577, -0.577,
    ]
    indices = [
        0, 1, 2, 0, 2, 3,
        1, 5, 6, 1, 6, 2,
        5, 4, 7, 5, 7, 6,
        4, 0, 3, 4, 3, 7,
        3, 2, 6, 3, 6, 7,
        4, 5, 1, 4, 1, 0,
    ]

    pos_raw = struct.pack("<" + "f" * len(positions), *positions)
    norm_raw = struct.pack("<" + "f" * len(normals), *normals)
    idx_raw = struct.pack("<" + "H" * len(indices), *indices)

    pos_view = _pad4(pos_raw)
    norm_view = _pad4(norm_raw)
    idx_view = _pad4(idx_raw)

    bin_blob = pos_view + norm_view + idx_view
    pos_offset = 0
    norm_offset = len(pos_view)
    idx_offset = norm_offset + len(norm_view)

    gltf = {
        "asset": {"version": "2.0", "generator": "3d-learning-platform-seed"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "DemoBox"}],
        "meshes": [
            {
                "name": "DemoBoxMesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1},
                        "indices": 2,
                        "material": 0,
                    }
                ],
            }
        ],
        "materials": [
            {
                "name": "DemoMaterial",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.39, 0.40, 0.95, 1.0],
                    "metallicFactor": 0.1,
                    "roughnessFactor": 0.45,
                },
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 8,
                "type": "VEC3",
                "max": [0.5, 0.5, 0.5],
                "min": [-0.5, -0.5, -0.5],
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": 8,
                "type": "VEC3",
            },
            {
                "bufferView": 2,
                "componentType": 5123,
                "count": 36,
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": pos_offset,
                "byteLength": len(pos_raw),
                "target": 34962,
            },
            {
                "buffer": 0,
                "byteOffset": norm_offset,
                "byteLength": len(norm_raw),
                "target": 34962,
            },
            {
                "buffer": 0,
                "byteOffset": idx_offset,
                "byteLength": len(idx_raw),
                "target": 34963,
            },
        ],
        "buffers": [{"byteLength": len(bin_blob)}],
    }

    json_chunk = _pad4(
        json.dumps(gltf, separators=(",", ":")).encode("utf-8"),
        pad_byte=b" ",
    )
    bin_chunk = _pad4(bin_blob)

    total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return b"".join(
        [
            struct.pack("<4sII", b"glTF", 2, total_length),
            struct.pack("<I4s", len(json_chunk), b"JSON"),
            json_chunk,
            struct.pack("<I4s", len(bin_chunk), b"BIN\x00"),
            bin_chunk,
        ]
    )


class Command(BaseCommand):
    help = "Create a demo course, lesson, sample .glb, and hotspots."

    def handle(self, *args, **options):
        course, _ = Course.objects.get_or_create(
            title="Demo: Explore a Box",
            defaults={
                "description": (
                    "A tiny starter course so you can try the 3D viewer "
                    "without uploading a model first."
                ),
            },
        )

        lesson, _ = Lesson.objects.get_or_create(
            course=course,
            order=1,
            defaults={
                "title": "The Demo Box",
                "description": (
                    "Rotate the box, toggle wireframe, and click the hotspots "
                    "on each face."
                ),
                "interaction_guide": (
                    "Drag to orbit. Scroll to zoom. Click numbered hotspots "
                    "or use the sidebar list."
                ),
            },
        )

        sample_dir = Path("media") / "3d_models"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample_path = sample_dir / "demo_box.glb"
        sample_path.write_bytes(build_box_glb())

        if not lesson.model_file:
            with sample_path.open("rb") as handle:
                lesson.model_file.save("demo_box.glb", File(handle), save=True)

        hotspots = [
            ("Front face", "The face pointing toward +Z.", 0.0, 0.0, 0.55),
            ("Top face", "The face pointing toward +Y.", 0.0, 0.55, 0.0),
            ("Right face", "The face pointing toward +X.", 0.55, 0.0, 0.0),
        ]
        created_hotspots = 0
        for index, (title, description, x, y, z) in enumerate(hotspots, start=1):
            _, was_created = Annotation.objects.get_or_create(
                lesson=lesson,
                order=index,
                defaults={
                    "title": title,
                    "description": description,
                    "position_x": x,
                    "position_y": y,
                    "position_z": z,
                },
            )
            if was_created:
                created_hotspots += 1

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"  Course: {course.title} (id={course.id})")
        self.stdout.write(f"  Lesson: {lesson.title} (id={lesson.id})")
        self.stdout.write(f"  Model:  {lesson.model_file.url}")
        self.stdout.write(f"  Hotspots added: {created_hotspots}")
        self.stdout.write(f"  Open:   /viewer/{lesson.id}/")
