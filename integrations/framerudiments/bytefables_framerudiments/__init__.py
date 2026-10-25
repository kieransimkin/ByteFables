"""ByteFables generators for FrameRudiments' trusted Python renderer registry.

Install this optional adapter into the FrameRudiments runtime and register its
factories with ``default_renderers()``. Nothing here implements a second frame
loop, effect stack, animation clock, video encoder or audio-processing engine.
"""
from .renderers import register_bytefables_renderers

__all__ = ["register_bytefables_renderers"]
