"""Versioned ByteFables artwork-generator v2 candidate surface.

This module is deliberately opt-in.  ``ArtworkRenderer`` in artwork.py remains
v1 and unchanged.  The v2 candidate uses remediation-candidate v2 for the three
families that passed engineering A/B screening and delegates every other family
byte-for-byte to v1.
"""
from __future__ import annotations

from .artwork import ArtworkRenderer
from .artwork_remediation_v2 import RemediationArtworkRendererV2, SUPPORTED_FAMILIES

PROFILE = "bytefables.artwork-generator-v2-candidate.v1"
TARGET_FAMILIES = SUPPORTED_FAMILIES


class ArtworkRendererV2Candidate:
    """Opt-in candidate with the same validated style input as ArtworkRenderer."""

    def __init__(self, size, style):
        # Always construct v1 first so validation and the unchanged-family
        # contract stay centralised in the production implementation.
        self.baseline = ArtworkRenderer(size, style)
        self.size = self.baseline.size
        self.family = self.baseline.family
        self.palette = self.baseline.palette
        self.complexity = self.baseline.complexity
        self._candidate = RemediationArtworkRendererV2(size, style) if self.family in TARGET_FAMILIES else None

    def render(self, frame):
        if self._candidate is None:
            return self.baseline.render(frame)
        return self._candidate.render(frame)
