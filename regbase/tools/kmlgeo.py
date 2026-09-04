#!/usr/bin/env python3
"""Parse KML/KMZ project files and derive the geometry facts Form 1.9 needs.

Deliberately dependency-light: stdlib zipfile + ElementTree, and great-circle
math done here rather than pulling in a projection stack. Lengths are computed
with the haversine formula on the WGS84 mean radius; polygon areas use the
spherical excess formula. Both are well inside the accuracy a pre-project
scoping document requires (sub-0.5% over the distances involved).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator

R_EARTH_M = 6_371_008.8          # WGS84 mean radius
M_PER_FT = 0.3048
SQM_PER_ACRE = 4046.8564224

_KML_NS = re.compile(r"\{[^}]*\}")


def _tag(el) -> str:
    return _KML_NS.sub("", el.tag)


@dataclass
class Feature:
    name: str
    kind: str                       # point | line | polygon
    coords: list[tuple[float, float]] = field(default_factory=list)
    description: str = ""
    folder_path: str = ""

    @property
    def length_m(self) -> float:
        if self.kind != "line" or len(self.coords) < 2:
            return 0.0
        return sum(haversine_m(self.coords[i], self.coords[i + 1])
                   for i in range(len(self.coords) - 1))

    @property
    def area_sqm(self) -> float:
        return polygon_area_sqm(self.coords) if self.kind == "polygon" else 0.0

    def summary(self) -> dict:
        d = {"name": self.name, "kind": self.kind, "vertices": len(self.coords),
             "folder_path": self.folder_path}
        if self.kind == "line":
            d["length_ft"] = round(self.length_m / M_PER_FT, 1)
            d["length_mi"] = round(self.length_m / 1609.344, 3)
        elif self.kind == "polygon":
            d["area_acres"] = round(self.area_sqm / SQM_PER_ACRE, 3)
        else:
            d["lat_long"] = f"{self.coords[0][1]:.6f}, {self.coords[0][0]:.6f}" if self.coords else ""
        return d


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """a, b are (lon, lat) in degrees."""
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R_EARTH_M * math.asin(math.sqrt(min(1.0, h)))


def polygon_area_sqm(ring: list[tuple[float, float]]) -> float:
    """Spherical excess (L'Huilier-free form). Ring is (lon, lat) degrees."""
    if len(ring) < 3:
        return 0.0
    pts = ring[:-1] if ring[0] == ring[-1] else ring[:]
    if len(pts) < 3:
        return 0.0
    total = 0.0
    for i in range(len(pts)):
        lon1, lat1 = math.radians(pts[i][0]), math.radians(pts[i][1])
        lon2, lat2 = math.radians(pts[(i + 1) % len(pts)][0]), math.radians(pts[(i + 1) % len(pts)][1])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(total * R_EARTH_M * R_EARTH_M / 2.0)


def _parse_coords(text: str) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for tok in (text or "").replace("\n", " ").replace("\t", " ").split():
        parts = tok.split(",")
        if len(parts) < 2:
            continue
        try:
            lon, lat = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        if -180 <= lon <= 180 and -90 <= lat <= 90:
            out.append((lon, lat))
    return out


def read_kml_bytes(path: Path) -> list[tuple[str, bytes]]:
    """Return [(inner_name, kml_bytes)]. Handles .kml and .kmz (possibly many)."""
    data = path.read_bytes()
    if data[:2] == b"PK":
        z = zipfile.ZipFile(path)
        names = [n for n in z.namelist() if n.lower().endswith(".kml")]
        if not names:
            raise SystemExit(f"{path}: KMZ contains no .kml entry")
        return [(n, z.read(n)) for n in names]
    return [(path.name, data)]


def parse(path: Path) -> list[Feature]:
    import xml.etree.ElementTree as ET

    features: list[Feature] = []
    for inner, blob in read_kml_bytes(path):
        try:
            root = ET.fromstring(blob)
        except ET.ParseError as exc:
            raise SystemExit(f"{path} ({inner}): invalid KML: {exc}") from exc
        features.extend(_walk(root, []))
    return features


def _walk(el, folders: list[str]) -> Iterator[Feature]:
    tag = _tag(el)
    if tag in ("Folder", "Document"):
        name_el = el.find("./{*}name")
        nm = (name_el.text or "").strip() if name_el is not None else ""
        sub = folders + [nm] if nm else folders
        for child in el:
            yield from _walk(child, sub)
        return
    if tag == "Placemark":
        yield from _placemark(el, folders)
        return
    for child in el:
        yield from _walk(child, folders)


def _placemark(pm, folders: list[str]) -> Iterator[Feature]:
    name_el = pm.find("./{*}name")
    desc_el = pm.find("./{*}description")
    name = (name_el.text or "").strip() if name_el is not None else "(unnamed)"
    desc = (desc_el.text or "").strip() if desc_el is not None else ""
    fpath = " > ".join(folders)

    emitted = False
    for geom in pm.iter():
        gt = _tag(geom)
        if gt == "Point":
            c = geom.find("./{*}coordinates")
            pts = _parse_coords(c.text if c is not None else "")
            if pts:
                yield Feature(name, "point", pts[:1], desc, fpath)
                emitted = True
        elif gt in ("LineString", "LinearRing"):
            # LinearRing inside a Polygon is handled by the Polygon branch.
            parent_is_poly = any(_tag(p) == "Polygon" for p in pm.iter()
                                 if geom in list(p.iter())[1:])
            if gt == "LinearRing" and parent_is_poly:
                continue
            c = geom.find("./{*}coordinates")
            pts = _parse_coords(c.text if c is not None else "")
            if len(pts) >= 2:
                yield Feature(name, "line", pts, desc, fpath)
                emitted = True
        elif gt == "Polygon":
            outer = geom.find(".//{*}outerBoundaryIs//{*}coordinates")
            pts = _parse_coords(outer.text if outer is not None else "")
            if len(pts) >= 3:
                yield Feature(name, "polygon", pts, desc, fpath)
                emitted = True
        elif gt == "Track":                                  # gx:Track
            pts = []
            for coord in geom.findall("./{*}coord"):
                parts = (coord.text or "").split()
                if len(parts) >= 2:
                    try:
                        pts.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        pass
            if len(pts) >= 2:
                yield Feature(name, "line", pts, desc, fpath)
                emitted = True
    if not emitted:
        return


def summarize(features: list[Feature]) -> dict:
    lines = [f for f in features if f.kind == "line"]
    polys = [f for f in features if f.kind == "polygon"]
    points = [f for f in features if f.kind == "point"]
    all_coords = [c for f in features for c in f.coords]
    if not all_coords:
        raise SystemExit("no usable geometry found in the KML/KMZ")

    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    total_len_m = sum(f.length_m for f in lines)
    total_area_sqm = sum(f.area_sqm for f in polys)

    # Rough construction disturbance for linear work when no polygon is drawn:
    # a 75 ft nominal ROW is the midstream planning default. Clearly labelled as
    # an estimate so nobody mistakes it for a surveyed number.
    row_ft = 75.0
    poly_acres = total_area_sqm / SQM_PER_ACRE
    row_acres = (total_len_m / M_PER_FT) * row_ft / 43560.0 if total_len_m else 0.0
    est_disturb_acres = poly_acres + row_acres
    basis_parts = []
    if row_acres:
        basis_parts.append(f"{row_acres:.2f} ac from {row_ft:.0f} ft nominal ROW x centerline")
    if poly_acres:
        basis_parts.append(f"{poly_acres:.2f} ac from drawn polygons")

    return {
        "feature_count": len(features),
        "lines": len(lines), "polygons": len(polys), "points": len(points),
        "bbox": [round(min(lons), 6), round(min(lats), 6),
                 round(max(lons), 6), round(max(lats), 6)],
        "centroid": [round(sum(lons) / len(lons), 6), round(sum(lats) / len(lats), 6)],
        "lat_long": f"{sum(lats)/len(lats):.6f}, {sum(lons)/len(lons):.6f}",
        "total_length_ft": round(total_len_m / M_PER_FT, 1),
        "total_length_mi": round(total_len_m / 1609.344, 3),
        "polygon_area_acres": round(total_area_sqm / SQM_PER_ACRE, 3),
        "est_disturbance_acres": round(est_disturb_acres, 2),
        "est_disturbance_basis": " + ".join(basis_parts) or "no linear or areal geometry",
        "over_one_acre": est_disturb_acres > 1.0,
        "features": [f.summary() for f in features],
    }


def to_geojson(features: list[Feature]) -> dict:
    feats = []
    for f in features:
        if f.kind == "point":
            geom = {"type": "Point", "coordinates": list(f.coords[0])}
        elif f.kind == "line":
            geom = {"type": "LineString", "coordinates": [list(c) for c in f.coords]}
        else:
            ring = [list(c) for c in f.coords]
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            geom = {"type": "Polygon", "coordinates": [ring]}
        feats.append({"type": "Feature", "geometry": geom,
                      "properties": {"name": f.name, "description": f.description,
                                     "folder_path": f.folder_path}})
    return {"type": "FeatureCollection", "features": feats}


def sample_points(features: list[Feature], every_m: float = 800.0,
                  cap: int = 60) -> list[tuple[float, float]]:
    """Points along the project for jurisdiction lookup — one per ~0.5 mi.

    A pipeline that clips the corner of a third county is exactly the case a
    centroid-only lookup misses, which is why this walks the line.
    """
    out: list[tuple[float, float]] = []
    for f in features:
        if f.kind == "point":
            out.append(f.coords[0])
            continue
        if not f.coords:
            continue
        out.append(f.coords[0])
        acc = 0.0
        for i in range(len(f.coords) - 1):
            seg = haversine_m(f.coords[i], f.coords[i + 1])
            acc += seg
            if acc >= every_m:
                out.append(f.coords[i + 1])
                acc = 0.0
        out.append(f.coords[-1])
    # De-duplicate at ~1e-4 deg (~11 m) and cap the request count.
    seen, uniq = set(), []
    for lon, lat in out:
        k = (round(lon, 4), round(lat, 4))
        if k not in seen:
            seen.add(k)
            uniq.append((lon, lat))
    if len(uniq) <= cap:
        return uniq
    step = len(uniq) / cap
    return [uniq[int(i * step)] for i in range(cap)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kml", type=Path)
    ap.add_argument("--geojson", type=Path, help="also write GeoJSON here")
    ap.add_argument("--samples", action="store_true",
                    help="print the jurisdiction-lookup sample points")
    args = ap.parse_args()

    feats = parse(args.kml)
    summary = summarize(feats)
    if args.samples:
        summary["lookup_samples"] = [[round(x, 6), round(y, 6)]
                                     for x, y in sample_points(feats)]
    print(json.dumps(summary, indent=2))
    if args.geojson:
        args.geojson.write_text(json.dumps(to_geojson(feats), indent=1))
        print(f"\nwrote {args.geojson}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
