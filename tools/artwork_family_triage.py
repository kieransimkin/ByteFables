"""Rank ByteFables artwork families from a distinctiveness screening report.

This is deterministic engineering triage, not an accessibility certification or
human-recognisability result. It never changes artwork; it turns existing
screening distributions into a family-level remediation queue.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

SCHEMA = 'bytefables.artwork-family-triage.v1'
SOURCE_SCHEMA = 'bytefables.artwork-distinctiveness.v1'
MODES = ('colour', 'greyscale', 'protan', 'deutan', 'tritan')


def _expect(value, message):
    if not value:
        raise ValueError(message)


def _number(value, label):
    _expect(type(value) in (int, float) and not isinstance(value, bool) and math.isfinite(value), f'Invalid {label}')
    return float(value)


def _load(path: Path) -> dict:
    raw = path.read_bytes()
    _expect(0 < len(raw) <= 32 * 1024 * 1024, 'Distinctiveness report size is invalid')
    try:
        doc = json.loads(raw)
    except Exception as exc:
        raise ValueError('Invalid distinctiveness JSON') from exc
    _expect(isinstance(doc, dict) and doc.get('schema') == SOURCE_SCHEMA and doc.get('status') == 'passed',
            'Expected a successful distinctiveness v1 report')
    return doc


def _ratio(family_value: float, global_value: float) -> float:
    if global_value <= 0:
        return 1.0 if family_value <= 0 else 999.0
    return family_value / global_value


def _recommend(worst: dict, colour_ratio: float | None, greyscale_ratio: float | None, cvd_ratio: float | None) -> list[str]:
    suggestions = []
    if worst['size'] <= 32:
        suggestions.append('Increase silhouette separation and reduce high-frequency detail at 16–32 px.')
    if worst['mode'] == 'greyscale' or (greyscale_ratio is not None and colour_ratio is not None and greyscale_ratio < colour_ratio):
        suggestions.append('Add luminance and shape cues so family variants do not depend mainly on colour.')
    if worst['mode'] in ('protan', 'deutan', 'tritan') or (cvd_ratio is not None and colour_ratio is not None and cvd_ratio < colour_ratio):
        suggestions.append('Increase non-hue cues and palette separation under colour-vision-deficiency screening.')
    if worst['mode'] == 'colour':
        suggestions.append('Increase structural parameter spread between identities within this family.')
    if not suggestions:
        suggestions.append('Review the closest identity pairs and increase structural separation without changing stable identity keys.')
    # Deterministic de-duplication while preserving order.
    return list(dict.fromkeys(suggestions))


def triage(report_path: Path, output: Path) -> dict:
    report_path = Path(report_path).resolve(strict=True)
    output = Path(output)
    _expect(not output.exists(), 'Output path already exists')
    doc = _load(report_path)
    results = doc.get('results')
    _expect(isinstance(results, list) and results, 'Distinctiveness report has no size results')

    cases = []
    family_names = set()
    by_family = {}
    for size_record in results:
        size = size_record.get('size')
        _expect(type(size) is int and size in (16, 32, 64, 128), 'Invalid distinctiveness size')
        modes = size_record.get('modes')
        _expect(isinstance(modes, dict), 'Distinctiveness mode inventory missing')
        for mode in MODES:
            entry = modes.get(mode)
            _expect(isinstance(entry, dict), f'Missing mode {mode}')
            global_dist = entry.get('nearestDifferentDigestDistribution')
            family_dist = entry.get('withinFamilyDistribution')
            _expect(isinstance(global_dist, dict) and isinstance(family_dist, dict), 'Missing family/global distributions')
            gp01 = _number(global_dist.get('p01'), f'{size}/{mode}/global p01')
            gp05 = _number(global_dist.get('p05'), f'{size}/{mode}/global p05')
            gmed = _number(global_dist.get('median'), f'{size}/{mode}/global median')
            for family, dist in family_dist.items():
                _expect(isinstance(family, str) and family and isinstance(dist, dict), 'Invalid family distribution')
                family_names.add(family)
                fp01 = _number(dist.get('p01'), f'{family}/{size}/{mode} p01')
                fp05 = _number(dist.get('p05'), f'{family}/{size}/{mode} p05')
                fmed = _number(dist.get('median'), f'{family}/{size}/{mode} median')
                case = {
                    'family': family,
                    'size': size,
                    'mode': mode,
                    'p01': round(fp01, 8),
                    'p05': round(fp05, 8),
                    'median': round(fmed, 8),
                    'globalP01': round(gp01, 8),
                    'globalP05': round(gp05, 8),
                    'globalMedian': round(gmed, 8),
                    'p01Ratio': round(_ratio(fp01, gp01), 6),
                    'p05Ratio': round(_ratio(fp05, gp05), 6),
                    'medianRatio': round(_ratio(fmed, gmed), 6),
                }
                case['screeningRatio'] = round((case['p01Ratio'] + case['p05Ratio'] + case['medianRatio']) / 3.0, 6)
                cases.append(case)
                by_family.setdefault(family, []).append(case)

    _expect(family_names, 'No families have two or more distinct identities to triage')
    family_results = []
    for family in sorted(family_names):
        entries = by_family[family]
        ordered = sorted(entries, key=lambda c: (c['screeningRatio'], c['size'], c['mode']))
        worst = ordered[0]
        ratios = [c['screeningRatio'] for c in entries]
        colour = [c['screeningRatio'] for c in entries if c['mode'] == 'colour']
        grey = [c['screeningRatio'] for c in entries if c['mode'] == 'greyscale']
        cvd = [c['screeningRatio'] for c in entries if c['mode'] in ('protan', 'deutan', 'tritan')]
        small = [c['screeningRatio'] for c in entries if c['size'] <= 32]
        record = {
            'family': family,
            'worstCase': worst,
            'worstScreeningRatio': round(min(ratios), 6),
            'medianScreeningRatio': round(sorted(ratios)[len(ratios)//2], 6),
            'smallIconWorstRatio': round(min(small), 6) if small else None,
            'colourWorstRatio': round(min(colour), 6) if colour else None,
            'greyscaleWorstRatio': round(min(grey), 6) if grey else None,
            'cvdWorstRatio': round(min(cvd), 6) if cvd else None,
            'recommendations': _recommend(worst, min(colour) if colour else None, min(grey) if grey else None, min(cvd) if cvd else None),
        }
        family_results.append(record)
    family_results.sort(key=lambda r: (r['worstScreeningRatio'], r['medianScreeningRatio'], r['family']))
    for rank, item in enumerate(family_results, 1):
        item['rank'] = rank

    out = {
        'schema': SCHEMA,
        'status': 'passed',
        'sourceSchema': SOURCE_SCHEMA,
        'sourceManifestSha256': doc.get('manifestSha256'),
        'assetCount': doc.get('assetCount'),
        'uniqueDigests': doc.get('uniqueDigests'),
        'familyCount': len(family_results),
        'rankingMethod': 'family/global nearest-neighbour p01+p05+median ratio; lower ratios are weaker relative to this corpus',
        'families': family_results,
        'weakestCases': sorted(cases, key=lambda c: (c['screeningRatio'], c['family'], c['size'], c['mode']))[:50],
        'warning': 'Relative machine-screening triage only; not a pass/fail accessibility threshold or human recognisability result.',
    }

    output.mkdir(parents=True)
    (output / 'family-triage.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    with (output / 'family-ranking.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['rank','family','worst_ratio','median_ratio','worst_size','worst_mode','worst_p05','global_p05'])
        for item in family_results:
            w = item['worstCase']
            writer.writerow([item['rank'], item['family'], item['worstScreeningRatio'], item['medianScreeningRatio'],
                             w['size'], w['mode'], w['p05'], w['globalP05']])
    lines = ['# ByteFables artwork family remediation queue', '',
             'Relative machine screening only; lower ratios mean a family is more collision-prone than the corpus at that size/mode.', '']
    for item in family_results:
        w = item['worstCase']
        lines += [f"## {item['rank']}. {item['family']}",
                  f"Worst relative ratio: **{item['worstScreeningRatio']:.3f}** at {w['size']} px / {w['mode']}.",
                  f"Family p05 {w['p05']:.6f} vs corpus p05 {w['globalP05']:.6f}.", '']
        lines += [f"- {suggestion}" for suggestion in item['recommendations']]
        lines.append('')
    (output / 'REMEDIATION.md').write_text('\n'.join(lines), encoding='utf-8')
    return out
