"""Detector registry and factory for prompt injection detection."""

from detectors.base import BaseDetector, DetectorResult
from detectors.llm_judge import LLMJudgeDetector


# Registry of all available detectors
DETECTOR_REGISTRY = {
    "llm_judge": LLMJudgeDetector,
}

# Lazy imports for detectors with heavier dependencies
_LAZY_DETECTORS = {
    "regex": ("detectors.regex_detector", "RegexDetector"),
    "bert": ("detectors.bert_detector", "BERTDetector"),
    "weak_model": ("detectors.weak_model_detector", "WeakModelDetector"),
    "scramblegate": ("detectors.scramblegate.detector", "ScrambleGateDetector"),
}


def get_detector_class(name: str):
    """Get a detector class by name, with lazy importing."""
    if name in DETECTOR_REGISTRY:
        return DETECTOR_REGISTRY[name]

    if name in _LAZY_DETECTORS:
        module_path, class_name = _LAZY_DETECTORS[name]
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        DETECTOR_REGISTRY[name] = cls
        return cls

    available = list(DETECTOR_REGISTRY.keys()) + list(_LAZY_DETECTORS.keys())
    raise ValueError(f"Unknown detector: {name}. Available: {available}")


def create_detector(name: str, detector_config: dict) -> BaseDetector:
    """Instantiate a detector from its name and config section."""
    cls = get_detector_class(name)
    params = detector_config.get(name, {})
    return cls(**params)


def create_detectors(config) -> dict:
    """Create all enabled detectors from a Config object.

    Returns:
        Dict mapping detector name to BaseDetector instance.
    """
    enabled = config.get("detectors", "enabled")
    detector_cfg = config.config.get("detectors", {})
    detectors = {}
    for name in enabled:
        detectors[name] = create_detector(name, detector_cfg)
    return detectors


def list_available_detectors():
    """Return names of all registered and lazy-loadable detectors."""
    return sorted(set(list(DETECTOR_REGISTRY.keys()) + list(_LAZY_DETECTORS.keys())))
