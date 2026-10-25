"""Render an existing authorised FrameRudiments project with ByteFables layers.

The project must already contain valid public assets, audio and clock. Add the
ByteFables layer JSON fragments to ``layers`` first. This script is intentionally
only a thin native-host entry point, not a separate video/animation renderer.
"""
import argparse
from pathlib import Path

from framerudiments import Project, default_renderers, preflight, render
from bytefables_framerudiments import register_bytefables_renderers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    registry = register_bytefables_renderers(default_renderers())
    project = Project.load(args.project)
    # FrameRudiments computes/records every registered source, effect and frame.
    if args.preflight_only:
        preflight(project, args.output, renderers=registry)
    else:
        render(project, args.output, renderers=registry)


if __name__ == '__main__':
    main()
