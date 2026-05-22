from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


DEFAULT_COVERAGE_MODE = "top_cities"


@dataclass(frozen=True)
class LocationOption:
    type: str
    value: str
    label: str
    aliases: tuple[str, ...]
    canton: str = ""
    cantons: tuple[str, ...] = ()
    top_cities: tuple[str, ...] = ()
    all_available_cities: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "value": self.value,
            "label": self.label,
            "aliases": list(self.aliases),
            "canton": self.canton,
            "cantons": list(self.cantons),
            "top_cities": list(self.top_cities),
            "all_available_cities": list(self.all_available_cities),
        }


CANTONS: dict[str, dict] = {
    "AG": {"label": "Canton Aargau", "aliases": ("Aargau", "AG", "Kanton Aargau"), "top": ("Aarau", "Baden", "Wettingen", "Brugg", "Zofingen"), "all": ("Aarau", "Baden", "Wettingen", "Brugg", "Zofingen", "Rheinfelden", "Lenzburg", "Wohlen", "Muri", "Oftringen")},
    "AI": {"label": "Canton Appenzell Innerrhoden", "aliases": ("Appenzell Innerrhoden", "AI", "Kanton Appenzell Innerrhoden"), "top": ("Appenzell",), "all": ("Appenzell", "Oberegg", "Gonten", "Rüte")},
    "AR": {"label": "Canton Appenzell Ausserrhoden", "aliases": ("Appenzell Ausserrhoden", "AR", "Kanton Appenzell Ausserrhoden"), "top": ("Herisau", "Teufen", "Heiden"), "all": ("Herisau", "Teufen", "Heiden", "Gais", "Trogen", "Urnäsch")},
    "BE": {"label": "Canton Bern", "aliases": ("Bern", "Berne", "BE", "Kanton Bern"), "top": ("Bern", "Biel/Bienne", "Thun", "Köniz", "Burgdorf"), "all": ("Bern", "Biel/Bienne", "Thun", "Köniz", "Burgdorf", "Langenthal", "Spiez", "Interlaken", "Muri bei Bern", "Münchenbuchsee")},
    "BL": {"label": "Canton Basel-Landschaft", "aliases": ("Basel-Landschaft", "Baselland", "BL", "Kanton Basel-Landschaft"), "top": ("Liestal", "Allschwil", "Muttenz", "Reinach BL"), "all": ("Liestal", "Allschwil", "Muttenz", "Reinach BL", "Pratteln", "Binningen", "Münchenstein", "Oberwil BL")},
    "BS": {"label": "Canton Basel-Stadt", "aliases": ("Basel-Stadt", "Basel Stadt", "BS", "Kanton Basel-Stadt"), "top": ("Basel", "Riehen"), "all": ("Basel", "Riehen", "Bettingen")},
    "FR": {"label": "Canton Fribourg", "aliases": ("Fribourg", "Freiburg", "FR", "Kanton Fribourg"), "top": ("Fribourg", "Bulle", "Villars-sur-Glâne", "Marly"), "all": ("Fribourg", "Bulle", "Villars-sur-Glâne", "Marly", "Düdingen", "Murten", "Estavayer", "Romont")},
    "GE": {"label": "Canton Geneva", "aliases": ("Geneva", "Genève", "GE", "Kanton Genf"), "top": ("Geneva", "Vernier", "Lancy", "Meyrin", "Carouge"), "all": ("Geneva", "Vernier", "Lancy", "Meyrin", "Carouge", "Onex", "Thônex", "Versoix", "Plan-les-Ouates", "Chêne-Bougeries")},
    "GL": {"label": "Canton Glarus", "aliases": ("Glarus", "GL", "Kanton Glarus"), "top": ("Glarus", "Näfels", "Netstal"), "all": ("Glarus", "Näfels", "Netstal", "Mollis", "Glarus Nord", "Glarus Süd")},
    "GR": {"label": "Canton Graubünden", "aliases": ("Graubünden", "Grisons", "GR", "Kanton Graubünden"), "top": ("Chur", "Davos", "St. Moritz", "Landquart"), "all": ("Chur", "Davos", "St. Moritz", "Landquart", "Ilanz", "Thusis", "Arosa", "Samedan", "Scuol")},
    "JU": {"label": "Canton Jura", "aliases": ("Jura", "JU", "Kanton Jura"), "top": ("Delémont", "Porrentruy", "Saignelégier"), "all": ("Delémont", "Porrentruy", "Saignelégier", "Courroux", "Bassecourt")},
    "LU": {"label": "Canton Lucerne", "aliases": ("Lucerne", "Luzern", "LU", "Kanton Luzern"), "top": ("Lucerne", "Emmen", "Kriens", "Sursee"), "all": ("Lucerne", "Emmen", "Kriens", "Sursee", "Horw", "Ebikon", "Willisau", "Sempach")},
    "NE": {"label": "Canton Neuchâtel", "aliases": ("Neuchâtel", "Neuchatel", "NE", "Kanton Neuenburg"), "top": ("Neuchâtel", "La Chaux-de-Fonds", "Le Locle"), "all": ("Neuchâtel", "La Chaux-de-Fonds", "Le Locle", "Val-de-Travers", "Peseux", "Cortaillod")},
    "NW": {"label": "Canton Nidwalden", "aliases": ("Nidwalden", "NW", "Kanton Nidwalden"), "top": ("Stans", "Hergiswil NW", "Buochs"), "all": ("Stans", "Hergiswil NW", "Buochs", "Ennetbürgen", "Oberdorf NW")},
    "OW": {"label": "Canton Obwalden", "aliases": ("Obwalden", "OW", "Kanton Obwalden"), "top": ("Sarnen", "Alpnach", "Kerns"), "all": ("Sarnen", "Alpnach", "Kerns", "Engelberg", "Sachseln")},
    "SG": {"label": "Canton St. Gallen", "aliases": ("St. Gallen", "Sankt Gallen", "SG", "Kanton St. Gallen"), "top": ("St. Gallen", "Rapperswil-Jona", "Wil SG", "Gossau SG"), "all": ("St. Gallen", "Rapperswil-Jona", "Wil SG", "Gossau SG", "Buchs SG", "Uzwil", "Wattwil", "Flawil")},
    "SH": {"label": "Canton Schaffhausen", "aliases": ("Schaffhausen", "SH", "Kanton Schaffhausen"), "top": ("Schaffhausen", "Neuhausen am Rheinfall", "Thayngen"), "all": ("Schaffhausen", "Neuhausen am Rheinfall", "Thayngen", "Stein am Rhein", "Beringen")},
    "SO": {"label": "Canton Solothurn", "aliases": ("Solothurn", "SO", "Kanton Solothurn"), "top": ("Solothurn", "Olten", "Grenchen", "Zuchwil"), "all": ("Solothurn", "Olten", "Grenchen", "Zuchwil", "Dornach", "Balsthal", "Oensingen")},
    "SZ": {"label": "Canton Schwyz", "aliases": ("Schwyz", "SZ", "Kanton Schwyz"), "top": ("Schwyz", "Freienbach", "Einsiedeln", "Küssnacht"), "all": ("Schwyz", "Freienbach", "Einsiedeln", "Küssnacht", "Wollerau", "Lachen SZ", "Arth")},
    "TG": {"label": "Canton Thurgau", "aliases": ("Thurgau", "TG", "Kanton Thurgau"), "top": ("Frauenfeld", "Kreuzlingen", "Arbon", "Weinfelden"), "all": ("Frauenfeld", "Kreuzlingen", "Arbon", "Weinfelden", "Amriswil", "Romanshorn", "Sirnach")},
    "TI": {"label": "Canton Ticino", "aliases": ("Ticino", "Tessin", "TI", "Kanton Tessin"), "top": ("Lugano", "Bellinzona", "Locarno", "Mendrisio"), "all": ("Lugano", "Bellinzona", "Locarno", "Mendrisio", "Chiasso", "Giubiasco", "Biasca", "Ascona")},
    "UR": {"label": "Canton Uri", "aliases": ("Uri", "UR", "Kanton Uri"), "top": ("Altdorf UR", "Schattdorf", "Bürglen UR"), "all": ("Altdorf UR", "Schattdorf", "Bürglen UR", "Erstfeld", "Flüelen")},
    "VD": {"label": "Canton Vaud", "aliases": ("Vaud", "Waadt", "VD", "Kanton Vaud"), "top": ("Lausanne", "Yverdon-les-Bains", "Montreux", "Nyon", "Renens"), "all": ("Lausanne", "Yverdon-les-Bains", "Montreux", "Nyon", "Renens", "Vevey", "Morges", "Pully", "Gland", "Aigle")},
    "VS": {"label": "Canton Valais", "aliases": ("Valais", "Wallis", "VS", "Kanton Valais"), "top": ("Sion", "Martigny", "Monthey", "Sierre", "Brig"), "all": ("Sion", "Martigny", "Monthey", "Sierre", "Brig", "Visp", "Crans-Montana", "Zermatt")},
    "ZG": {"label": "Canton Zug", "aliases": ("Zug", "ZG", "Kanton Zug"), "top": ("Zug", "Baar", "Cham", "Rotkreuz"), "all": ("Zug", "Baar", "Cham", "Rotkreuz", "Steinhausen", "Unterägeri", "Oberägeri")},
    "ZH": {"label": "Canton Zürich", "aliases": ("Zurich", "Zürich", "ZH", "Kanton Zürich", "Canton Zurich"), "top": ("Zurich", "Winterthur", "Uster", "Dübendorf", "Wetzikon"), "all": ("Zurich", "Winterthur", "Uster", "Dübendorf", "Wetzikon", "Horgen", "Bülach", "Dietikon", "Adliswil", "Kloten", "Meilen", "Pfäffikon ZH")},
}


REGIONS: dict[str, dict] = {
    "de_ch": {"label": "German-speaking Switzerland", "aliases": ("German-speaking Switzerland", "Deutschschweiz"), "cantons": ("ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG")},
    "romandie": {"label": "Romandie", "aliases": ("Romandie", "French-speaking Switzerland", "Suisse romande"), "cantons": ("GE", "VD", "NE", "JU", "FR", "VS")},
    "ticino": {"label": "Ticino", "aliases": ("Ticino", "Italian-speaking Switzerland", "Tessin"), "cantons": ("TI",)},
    "central": {"label": "Central Switzerland", "aliases": ("Central Switzerland", "Zentralschweiz"), "cantons": ("LU", "UR", "SZ", "OW", "NW", "ZG")},
    "eastern": {"label": "Eastern Switzerland", "aliases": ("Eastern Switzerland", "Ostschweiz"), "cantons": ("SG", "TG", "AR", "AI", "SH", "GL", "GR")},
    "northwestern": {"label": "Northwestern Switzerland", "aliases": ("Northwestern Switzerland", "Nordwestschweiz"), "cantons": ("BS", "BL", "AG", "SO")},
}


def _unique(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        norm = item.strip()
        key = norm.lower()
        if norm and key not in seen:
            seen.add(key)
            out.append(norm)
    return out


def _city_options() -> list[LocationOption]:
    by_city: dict[str, str] = {}
    for code, canton in CANTONS.items():
        for city in canton["all"]:
            by_city.setdefault(city, code)
    return [
        LocationOption(
            type="city",
            value=city,
            label=city,
            aliases=(city,),
            canton=code,
            top_cities=(city,),
            all_available_cities=(city,),
        )
        for city, code in sorted(by_city.items(), key=lambda x: x[0].lower())
    ]


def get_location_options() -> list[LocationOption]:
    options: list[LocationOption] = []
    for code, canton in CANTONS.items():
        options.append(LocationOption(
            type="canton",
            value=code,
            label=canton["label"],
            aliases=tuple(canton["aliases"]),
            canton=code,
            top_cities=tuple(canton["top"]),
            all_available_cities=tuple(canton["all"]),
        ))
    for value, region in REGIONS.items():
        top = []
        all_cities = []
        for canton_code in region["cantons"]:
            top.extend(CANTONS[canton_code]["top"])
            all_cities.extend(CANTONS[canton_code]["all"])
        options.append(LocationOption(
            type="region",
            value=value,
            label=region["label"],
            aliases=tuple(region["aliases"]),
            cantons=tuple(region["cantons"]),
            top_cities=tuple(_unique(top)),
            all_available_cities=tuple(_unique(all_cities)),
        ))
    options.extend(_city_options())
    return options


def locations_payload() -> dict:
    options = get_location_options()
    return {
        "coverage_modes": [
            {"value": "top_cities", "label": "Top cities"},
            {"value": "area_query", "label": "Area query"},
            {"value": "all_available_cities", "label": "All available cities"},
        ],
        "cantons": [o.to_dict() for o in options if o.type == "canton"],
        "regions": [o.to_dict() for o in options if o.type == "region"],
        "cities": [o.to_dict() for o in options if o.type == "city"],
    }


def search_location_options(query: str, limit: int = 20) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    matches = []
    for option in get_location_options():
        haystack = [option.label, option.value, *option.aliases]
        score = 0
        for item in haystack:
            text = item.lower()
            if text == q:
                score = max(score, 100)
            elif text.startswith(q):
                score = max(score, 80)
            elif q in text:
                score = max(score, 50)
        if score:
            data = option.to_dict()
            data["score"] = score
            matches.append(data)
    matches.sort(key=lambda x: (-x["score"], x["type"], x["label"]))
    return matches[:limit]


def _find_option(selection: dict) -> LocationOption | None:
    value = str(selection.get("value", "")).strip().lower()
    label = str(selection.get("label", "")).strip().lower()
    type_ = str(selection.get("type", "")).strip().lower()
    for option in get_location_options():
        candidates = {option.value.lower(), option.label.lower(), *(a.lower() for a in option.aliases)}
        if type_ and option.type != type_:
            continue
        if value in candidates or label in candidates:
            return option
    return None


def selection_from_city(city: str) -> dict:
    return {
        "type": "city",
        "value": city,
        "label": city,
        "coverage_mode": DEFAULT_COVERAGE_MODE,
    }


def expand_location_selection(selection: dict) -> list[str]:
    coverage = selection.get("coverage_mode") or DEFAULT_COVERAGE_MODE
    option = _find_option(selection)
    if not option:
        return _unique([str(selection.get("label") or selection.get("value") or "").strip()])
    if option.type == "city":
        return [option.label]
    if coverage == "area_query":
        return [option.label]
    if coverage == "all_available_cities":
        return _unique(option.all_available_cities)
    return _unique(option.top_cities)


def normalize_location_selections(locations: list[dict] | None, cities: list[str] | None = None) -> list[dict]:
    selections = list(locations or [])
    if not selections and cities:
        selections = [selection_from_city(c) for c in cities]
    normalized = []
    for selection in selections:
        option = _find_option(selection)
        coverage = selection.get("coverage_mode") or DEFAULT_COVERAGE_MODE
        if option:
            normalized.append({
                "type": option.type,
                "value": option.value,
                "label": option.label,
                "coverage_mode": coverage,
            })
        else:
            raw = str(selection.get("label") or selection.get("value") or "").strip()
            if raw:
                normalized.append({
                    "type": "custom",
                    "value": raw,
                    "label": raw,
                    "coverage_mode": "area_query",
                })
    return normalized


def expand_locations(locations: list[dict] | None, cities: list[str] | None = None) -> list[str]:
    terms = []
    for selection in normalize_location_selections(locations, cities):
        terms.extend(expand_location_selection(selection))
    return _unique(terms)


def summarize_locations(locations: list[dict] | None, cities: list[str] | None = None) -> str:
    labels = [s["label"] for s in normalize_location_selections(locations, cities)]
    return ", ".join(labels) if labels else "No locations"
