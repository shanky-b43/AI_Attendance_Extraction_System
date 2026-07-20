import yaml
from dataclasses import dataclass
from typing import List
from pathlib import Path


@dataclass
class PathsConfig:
    input_pdfs: Path
    input_images: Path
    output_excel: Path
    output_logs: Path
    output_debug: Path
    output_crops: Path
    models: Path


@dataclass
class AttendanceRulesConfig:
    present_marks: List[str]
    absent_marks: List[str]


@dataclass
class OcrConfig:
    confidence_threshold: float
    lang: str
    use_gpu: bool


@dataclass
class AppConfig:
    debug_mode: bool


@dataclass
class Config:
    paths: PathsConfig
    attendance_rules: AttendanceRulesConfig
    ocr: OcrConfig
    app: AppConfig


def load_config(config_path: str | Path) -> Config:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    base_dir = path.parent

    paths_config = PathsConfig(
        input_pdfs=base_dir / data["paths"]["input_pdfs"],
        input_images=base_dir / data["paths"]["input_images"],
        output_excel=base_dir / data["paths"]["output_excel"],
        output_logs=base_dir / data["paths"]["output_logs"],
        output_debug=base_dir / data["paths"]["output_debug"],
        output_crops=base_dir / data["paths"]["output_crops"],
        models=base_dir / data["paths"]["models"]
    )

    attendance_rules_config = AttendanceRulesConfig(
        present_marks=data["attendance_rules"]["present_marks"],
        absent_marks=data["attendance_rules"]["absent_marks"]
    )

    ocr_config = OcrConfig(
        confidence_threshold=data["ocr"]["confidence_threshold"],
        lang=data["ocr"]["lang"],
        use_gpu=data["ocr"]["use_gpu"]
    )

    app_config = AppConfig(
        debug_mode=data["app"]["debug_mode"]
    )

    return Config(
        paths=paths_config,
        attendance_rules=attendance_rules_config,
        ocr=ocr_config,
        app=app_config
    )
