"""
Pluggable prompt-injection detection subsystem.
Supports:
1. RegexDetector: Heuristic and structural delimiter matching (< 0.05 ms latency).
2. MLDetector: Sublinear TF-IDF + Logistic Regression trained on held-out security corpora (~0.16 ms latency).
3. EnsembleDetector: Fast regex evaluation short-circuit with ML classification fallback.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

import joblib
from pydantic import BaseModel

from core.config import config
from core.security.input_guards import InputGuards

logger = logging.getLogger("gateway.detectors")


class DetectorResult(BaseModel):
    is_injection: bool
    score: float
    detector_name: str
    detail: Optional[str] = None


class BaseInjectionDetector(ABC):
    @abstractmethod
    def predict(self, text: str) -> DetectorResult:
        """Evaluates input text and returns a standardized DetectorResult."""
        pass

    def is_available(self) -> bool:
        """Indicates whether detector dependencies and weights are loaded."""
        return True


class RegexDetector(BaseInjectionDetector):
    def __init__(self):
        self.name = "regex"

    def is_available(self) -> bool:
        return True

    def predict(self, text: str) -> DetectorResult:
        if not text:
            return DetectorResult(is_injection=False, score=0.0, detector_name=self.name)

        is_injected = InputGuards.detect_prompt_injection(text)
        return DetectorResult(
            is_injection=is_injected,
            score=1.0 if is_injected else 0.0,
            detector_name=self.name,
            detail="Heuristic regex pattern matched" if is_injected else "No regex pattern matched"
        )


class MLDetector(BaseInjectionDetector):
    def __init__(self, model_path: Optional[str] = None, threshold: float = 0.5):
        self.name = "ml_tfidf"
        self.threshold = threshold
        self.model = None

        if model_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(base_dir, "models", "injection_classifier.joblib")

        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded ML injection classifier from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load ML model from {self.model_path}: {e}")
                self.model = None
        else:
            logger.warning(f"ML model file not found at {self.model_path}. ML detection will fallback to negative.")

    def is_available(self) -> bool:
        return self.model is not None

    def predict(self, text: str) -> DetectorResult:
        if not text or self.model is None:
            return DetectorResult(
                is_injection=False,
                score=0.0,
                detector_name=self.name,
                detail="Model not loaded or empty text"
            )

        try:
            proba = float(self.model.predict_proba([text])[0, 1])
            is_injected = proba >= self.threshold
            return DetectorResult(
                is_injection=is_injected,
                score=round(proba, 4),
                detector_name=self.name,
                detail=f"Probability {proba:.4f} >= threshold {self.threshold:.2f}" if is_injected else f"Probability {proba:.4f} < threshold {self.threshold:.2f}"
            )
        except Exception as e:
            logger.error(f"Error during ML prediction: {e}")
            return DetectorResult(
                is_injection=False,
                score=0.0,
                detector_name=self.name,
                detail=f"Inference error: {str(e)}"
            )


class EnsembleDetector(BaseInjectionDetector):
    def __init__(self, ml_model_path: Optional[str] = None, threshold: float = 0.5):
        self.name = "ensemble"
        self.regex_detector = RegexDetector()
        self.ml_detector = MLDetector(model_path=ml_model_path, threshold=threshold)

    @property
    def threshold(self) -> float:
        return self.ml_detector.threshold

    @threshold.setter
    def threshold(self, val: float):
        self.ml_detector.threshold = val

    def is_available(self) -> bool:
        return self.ml_detector.is_available()

    def predict(self, text: str) -> DetectorResult:
        if not text:
            return DetectorResult(is_injection=False, score=0.0, detector_name=self.name)

        # 1. Fast regex path (high precision on known signatures)
        regex_res = self.regex_detector.predict(text)
        if regex_res.is_injection:
            return DetectorResult(
                is_injection=True,
                score=1.0,
                detector_name=self.name,
                detail=f"Blocked via Regex Guard ({regex_res.detail})"
            )

        # 2. ML semantic classification path
        ml_res = self.ml_detector.predict(text)
        return DetectorResult(
            is_injection=ml_res.is_injection,
            score=ml_res.score,
            detector_name=self.name,
            detail=f"Evaluated via ML Classifier ({ml_res.detail})"
        )


def get_detector(detector_type: Optional[str] = None, threshold: Optional[float] = None) -> BaseInjectionDetector:
    """Factory creating the configured detector instance."""
    raw_type = detector_type or getattr(config, "DETECTOR_TYPE", "ensemble") or "ensemble"
    dtype = str(raw_type).lower().strip()
    thresh = threshold if threshold is not None else float(getattr(config, "ML_THRESHOLD", 0.5))

    if dtype == "regex":
        return RegexDetector()
    elif dtype == "ml":
        return MLDetector(threshold=thresh)
    else:
        return EnsembleDetector(threshold=thresh)


# Default global detector singleton
detector = get_detector()
