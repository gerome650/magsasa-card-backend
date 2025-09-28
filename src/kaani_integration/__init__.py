"""
KaAni Agricultural Intelligence Integration Module
MAGSASA-CARD Enhanced Platform

Provides AI-powered agricultural diagnosis and risk assessment capabilities
"""

__version__ = "1.0.0"
__author__ = "MAGSASA-CARD Development Team"

# Module exports
from .diagnosis_engine import DiagnosisEngine
from .agscore_calculator import AgScoreCalculator
from .openai_provider import OpenAIProvider

__all__ = [
    'DiagnosisEngine',
    'AgScoreCalculator', 
    'OpenAIProvider'
]
