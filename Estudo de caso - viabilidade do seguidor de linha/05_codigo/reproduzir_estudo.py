"""Reproduz os ensaios cinemáticos arquivados, sem alterar a PCB.

Projeto baseado no EVA-RT, © EXOTIC TEAM MX, AGPL-3.0.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import argparse
import json
import math
import sys

import numpy as np
from shapely.geometry import LineString, Polygon

CASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent / "originais"))
import simular_marcas_trif as model
import simular_volta_trif as lap


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(track, marks, length, axle_y, sensor_y, lateral=69.5):
    alpha = model.pose(track, length)
    left = model.sensor_xy(track, alpha, length, lateral, sensor_y - axle_y)
    right = model.sensor_xy(track, alpha, length, -lateral, sensor_y - axle_y)
    events = [lap.inspect_mark(track, left if e["side"] > 0 else right, e) for e in marks]
    return events, left, right


def compact_result(events, **extra):
    return dict(
        **extra,
        nominal_read=sum(e["read"] for e in events),
        common_tolerance_read=sum(e["common_tolerance_read"] for e in events),
        total=len(events),
        missed=[e["label"] for e in events if not e["read"]],
        events=[{k: v for k, v in e.items() if k not in {"spans", "robust_spans"}} for e in events],
    )


def polygon_for_mark(e):
    co, si = math.cos(e["phi"]), math.sin(e["phi"])
    side = e["side"]
    return Polygon([
        (e["x"] + u * co - v * side * si, e["y"] + u * si + v * side * co)
        for u, v in [(-9.5, 49.5), (9.5, 49.5), (9.5, 89.5), (-9.5, 89.5)]
    ])


def closed_oval(step, adjusted):
    archived = read_json(CASE / "03_simulacoes/02_ajuste_8mm_1mm/verificacao_circuito_6_de_7.json")
    segments = archived["segments"]
    cycle, _ = model.path(segments, step)
    period = float(cycle[-1, 0])
    # Three cycles supply both approach and departure at the closing mark.
    track, _ = model.path(segments * 3, step)
    bounds = np.r_[0, np.cumsum([e[0] for e in segments])]
    marks = []
    for i, phase in enumerate(bounds[1:]):
        p = track[np.argmin(abs(track[:, 0] - (period + phase)))]
        marks.append(dict(s=float(p[0]), x=float(p[1]), y=float(p[2]), phi=float(p[3]),
                          side=1, label=f"C{i + 1}", kind="curva"))
    for label, distance, kind in [("Partida", period + 1500, "partida"),
                                   ("Chegada", 2 * period + 500, "chegada")]:
        p = track[np.argmin(abs(track[:, 0] - distance))]
        marks.append(dict(s=float(p[0]), x=float(p[1]), y=float(p[2]), phi=float(p[3]),
                          side=-1, label=label, kind=kind))
    events, left, right = evaluate(track, marks, adjusted["L_mm"], adjusted["axle_y_mm"],
                                   adjusted["sensor_y_mm"])
    independent = []
    polygons = [polygon_for_mark(e) for e in marks]
    for e, polygon, result in zip(marks, polygons, events):
        near = (track[:, 0] > e["s"] - 200) & (track[:, 0] < e["s"] + 300)
        sensor = left if e["side"] > 0 else right
        hit = LineString(sensor[near]).intersection(polygon).length > 1e-8
        assert hit == result["read"], e["label"]
        independent.append(dict(mark=e["label"], shapely_read=hit, matches_clip=True))
    line = LineString(cycle[:, 1:3])
    parts = [LineString(cycle[(cycle[:, 0] >= bounds[i] - 1e-6) &
                              (cycle[:, 0] <= bounds[i + 1] + 1e-6), 1:3]) for i in range(5)]
    checks = dict(
        closed_error_mm=float(np.linalg.norm(cycle[-1, 1:3] - cycle[0, 1:3])),
        no_crossings=line.is_simple,
        length_mm=period,
        min_radius_mm=min(abs(1 / curvature) for _, curvature in segments if curvature),
        parallel_straight_edge_gap_mm=parts[0].distance(parts[3]) - 19,
        opposite_arcs_gap_mm=min(parts[1].distance(parts[4]), parts[2].distance(parts[4])),
        mark_overlap_count=sum(polygons[i].intersection(polygons[j]).area > 1e-7
                               for i in range(len(polygons)) for j in range(i + 1, len(polygons))),
        effective_mark_edge_gap_mm=[line.distance(p) - 9.5 for p in polygons],
        finish_before_start_mm=1000,
        straight_before_finish_mm=500,
        straight_after_start_mm=1500,
        manta_edge_margin_mm=290.5,
        gates_modelled=False,
    )
    assert checks["closed_error_mm"] < 1e-6 and checks["no_crossings"]
    assert checks["parallel_straight_edge_gap_mm"] >= 200 and checks["min_radius_mm"] >= 100
    assert checks["mark_overlap_count"] == 0
    assert min(checks["effective_mark_edge_gap_mm"]) >= 37 - .01
    assert max(checks["effective_mark_edge_gap_mm"]) <= 43 + .01
    return compact_result(events, config=adjusted, segments=segments, checks=checks,
                          independent_checks=independent, step_mm=step)


def audit_crossings():
    """A necessary crossing check, not a full compliance validator."""
    curvatures = [0] + [sign / radius for radius in [100, 150, 200, 300, 500] for sign in [-1, 1]]
    cases = []
    for angle in [math.pi / 2, math.pi]:
        for before in curvatures:
            for after in curvatures:
                if before == after:
                    continue
                segments = [(400., 0.), model.curve(before, angle), model.curve(after), (400., 0.)]
                track, _ = model.path(segments, .5)
                bounds = np.r_[0, np.cumsum([p[0] for p in segments])]
                parts = [LineString(track[(track[:, 0] >= bounds[i] - 1e-6) &
                                          (track[:, 0] <= bounds[i + 1] + 1e-6), 1:3])
                         for i in range(4)]
                problems = []
                for i, j in [(0, 2), (0, 3), (1, 3)]:
                    intersection = parts[i].intersection(parts[j])
                    if intersection.is_empty:
                        continue
                    if intersection.geom_type == "Point":
                        points = [intersection]
                    elif intersection.geom_type == "MultiPoint":
                        points = list(intersection.geoms)
                    else:
                        # Do not silently classify other geometries as approved.
                        points = []
                    for point in points:
                        # Reject only known internal curves, not missing context
                        # beyond the open beginning/end of this local test path.
                        invalid = (segments[i][1] != 0 or segments[j][1] != 0
                                   or parts[0].length - parts[0].project(point) < 250 - 1e-5
                                   or (j == 3 and parts[3].project(point) < 250 - 1e-5))
                        if invalid:
                            problems.append(dict(segments=[i, j],
                                                 point_mm=[round(point.x, 5), round(point.y, 5)],
                                                 rule="4.6: curva conhecida a menos de 250 mm do cruzamento"))
                cases.append(dict(
                    before_signed_radius_mm=None if not before else round(1 / before),
                    after_signed_radius_mm=None if not after else round(1 / after),
                    incoming_angle_deg=round(angle * 180 / math.pi),
                    status="reprovada_nesta_checagem" if problems else "nao_reprovada_nesta_checagem",
                    problems=problems,
                ))
    rejected = sum(bool(e["problems"]) for e in cases)
    assert len(cases) == 220 and rejected == 20
    return dict(total=220, rejected_by_crossing_check=rejected,
                not_rejected_but_not_fully_validated=220 - rejected,
                audit_step_mm=.5,
                note="Não certifica os demais itens do edital. Aproximações por reta incluem geometrias duplicadas.",
                cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=float, default=.25, help="passo espacial máximo em mm")
    parser.add_argument("--output", default="reproducao", help="pasta de saída relativa ao estudo, ou absoluta")
    args = parser.parse_args()
    if not .01 <= args.step <= 1:
        parser.error("use um passo entre 0.01 e 1 mm")
    output = Path(args.output)
    if not output.is_absolute():
        output = CASE / output
    output.mkdir(parents=True, exist_ok=True)
    original = read_json(CASE / "03_simulacoes/01_base_original/analise_volta.json")["config"]
    adjusted = read_json(CASE / "03_simulacoes/02_ajuste_8mm_1mm/comparacao_animacao.json")["config"]
    track, _, marks, checks = lap.build_course(args.step)
    baseline, _, _ = evaluate(track, marks, original["L_mm"], original["axle_y_mm"], 4.5)
    changed, _, _ = evaluate(track, marks, adjusted["L_mm"], adjusted["axle_y_mm"], adjusted["sensor_y_mm"])
    results = {
        "base_original": compact_result(baseline, config=original, checks=checks, step_mm=args.step),
        "ajuste_volta_19": compact_result(changed, config=adjusted, checks=checks, step_mm=args.step),
        "ajuste_circuito_7": closed_oval(args.step, adjusted),
        "auditoria_220_cruzamentos": audit_crossings(),
    }
    assert results["base_original"]["nominal_read"] == 17
    assert results["ajuste_volta_19"]["nominal_read"] == 19
    assert results["ajuste_circuito_7"]["nominal_read"] == 6
    assert results["ajuste_circuito_7"]["missed"] == ["C2"]
    for name, result in results.items():
        (output / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({name: {k: v for k, v in result.items()
                            if k in {"nominal_read", "common_tolerance_read", "total", "missed",
                                     "rejected_by_crossing_check", "not_rejected_but_not_fully_validated"}}
                      for name, result in results.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
