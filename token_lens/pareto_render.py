"""Pareto frontier rendering (ASCII + SVG)."""
from __future__ import annotations

import html

from .types import ParetoCurve, ParetoPoint


def render_pareto_ascii(curve, width=50, height=12):
    if not curve.points:
        return "(no pareto data)"
    max_tok = max((p.tokens for p in curve.points), default=0) or 1
    min_tok = min((p.tokens for p in curve.points), default=0)
    max_q = max((p.quality for p in curve.points), default=1.0)
    min_q = min((p.quality for p in curve.points), default=0.0)
    out = ["QUALITY vs TOKENS  (Pareto frontier)", ""]
    rows = []
    for row in range(height):
        q_at_row = max_q - (row / max(height - 1, 1)) * (max_q - min_q)
        line = " " * 6
        for p in curve.points:
            if abs(p.quality - q_at_row) < (max_q - min_q) / max(height - 1, 1) / 1.5:
                line += "*"
            else:
                line += " "
            line += " "
        rows.append(line)
    out.extend(rows)
    out.append("")
    out.append("  tokens: " + str(min_tok) + " " + " " * (width - 16) + str(max_tok))
    out.append("")
    out.append("  points:")
    for p in curve.points:
        out.append("    " + str(p.tokens).rjust(8) + " tokens  q=" + ("%.3f" % p.quality) + "  " + (p.label or ""))
    return "\n".join(out)


def render_pareto_svg(curve, path, width=720, height=360):
    if not curve.points:
        body = '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(width) + '" height="' + str(height) + '"></svg>'
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        return
    margin_l, margin_r, margin_t, margin_b = 60, 30, 40, 50
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    max_tok = max((p.tokens for p in curve.points), default=1) or 1
    min_tok = min((p.tokens for p in curve.points), default=0)
    max_q = max((p.quality for p in curve.points), default=1.0)
    min_q = min((p.quality for p in curve.points), default=0.0)

    def sx(tokens):
        if max_tok == min_tok:
            return margin_l + plot_w / 2.0
        return margin_l + (tokens - min_tok) / (max_tok - min_tok) * plot_w

    def sy(quality):
        if max_q == min_q:
            return margin_t + plot_h / 2.0
        return margin_t + (1 - (quality - min_q) / (max_q - min_q)) * plot_h

    points_attr = " ".join(str(sx(p.tokens)) + "," + str(sy(p.quality)) for p in curve.points)
    markers = "\n".join(
        '<circle cx="' + str(sx(p.tokens)) + '" cy="' + str(sy(p.quality)) + '" r="4" fill="#0a7" />\n<text x="' + str(sx(p.tokens) + 6) + '" y="' + str(sy(p.quality) - 6) + '" font-size="10" fill="#333">' + html.escape(str(p.tokens)) + "</text>"
        for p in curve.points
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(width) + '" height="' + str(height) + '" viewBox="0 0 ' + str(width) + " " + str(height) + '">\n'
        '<rect width="100%" height="100%" fill="#fafafa" />\n'
        '<text x="20" y="24" font-family="sans-serif" font-size="14" fill="#222">QUALITY vs TOKENS  (Pareto frontier)</text>\n'
        '<line x1="' + str(margin_l) + '" y1="' + str(margin_t + plot_h) + '" x2="' + str(margin_l + plot_w) + '" y2="' + str(margin_t + plot_h) + '" stroke="#888" />\n'
        '<line x1="' + str(margin_l) + '" y1="' + str(margin_t) + '" x2="' + str(margin_l) + '" y2="' + str(margin_t + plot_h) + '" stroke="#888" />\n'
        '<text x="' + str(margin_l + plot_w / 2 - 30) + '" y="' + str(height - 10) + '" font-size="11" fill="#444">tokens (lower = better)</text>\n'
        '<text x="10" y="' + str(margin_t + plot_h / 2) + '" font-size="11" fill="#444" transform="rotate(-90 10 ' + str(margin_t + plot_h / 2) + ')">quality (higher = better)</text>\n'
        '<polyline points="' + points_attr + '" fill="none" stroke="#0a7" stroke-width="2" />\n'
        + markers + "\n"
        + "</svg>\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


__all__ = ["render_pareto_ascii", "render_pareto_svg"]