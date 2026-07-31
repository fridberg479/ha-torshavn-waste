from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:
    print(
        "PyMuPDF manglar.\n"
        "Installera tað við:\n\n"
        "  python -m pip install pymupdf\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


MONTH_ALIASES = {
    "JANUAR": 1,
    "FEBRUAR": 2,
    "MARS": 3,
    "APRÍL": 4,
    "APR═L": 4,
    "MAI": 5,
    "JUNI": 6,
    "JULI": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OKTOBER": 10,
    "NOVEMBER": 11,
    "DESEMBER": 12,
}

MONTH_NAMES = {
    1: "JANUAR",
    2: "FEBRUAR",
    3: "MARS",
    4: "APRÍL",
    5: "MAI",
    6: "JUNI",
    7: "JULI",
    8: "AUGUST",
    9: "SEPTEMBER",
    10: "OKTOBER",
    11: "NOVEMBER",
    12: "DESEMBER",
}

AREA_WORD_ALIASES = {
    "øki",
    "ïki",
}

# Feitu staðarnøvnini í PDF-fíluni merkja, at alt staðið hoyrir
# til økið, eisini gøtur sum ikki standa í gøtulistanum.
SETTLEMENTS_BY_AREA: dict[int, tuple[str, ...]] = {
    1: (
        "Kaldbaksbotnur",
        "Kaldbak",
        "Kollafjørður",
        "Langasandur",
        "Oyrareingir",
        "Hvítanes",
        "Signabøur",
    ),
    6: (
        "Argir",
        "Kirkjubøur",
        "Norðadalur",
        "Syðradalur",
        "Velbastaður",
    ),
}

# Trygg og eksplisitt normalisering av vanligum bendingum.
# Vit gita ikki endingar sjálvvirkandi.
SETTLEMENT_ALIASES: dict[str, str] = {
    "kaldbaksbotnur": "Kaldbaksbotnur",
    "kaldbaksbotni": "Kaldbaksbotnur",
    "kaldbak": "Kaldbak",
    "kollafjørður": "Kollafjørður",
    "kollafirði": "Kollafjørður",
    "langasandur": "Langasandur",
    "langasandi": "Langasandur",
    "oyrareingir": "Oyrareingir",
    "oyrareingjum": "Oyrareingir",
    "hvítanes": "Hvítanes",
    "hvítanesi": "Hvítanes",
    "signabøur": "Signabøur",
    "signabø": "Signabøur",
    "argir": "Argir",
    "argjum": "Argir",
    "kirkjubøur": "Kirkjubøur",
    "kirkjubø": "Kirkjubøur",
    "norðadalur": "Norðadalur",
    "norðadali": "Norðadalur",
    "syðradalur": "Syðradalur",
    "syðradali": "Syðradalur",
    "velbastaður": "Velbastaður",
    "velbastað": "Velbastaður",
}

# Absoluttar koordinatir á síðu 2.
#
# Gøtulistarnir eru soleiðis skipaðir:
#
# x ≈ 703: øki 1, síðani øki 2
# x ≈ 801: øki 3
# x ≈ 899: fyrsti teigur hjá øki 4
# x ≈ 997: framhald av øki 4, síðani øki 5
# x ≈ 1094: framhald av øki 4, síðani øki 6
#
STREET_REGIONS: dict[
    int,
    list[tuple[float, float, float, float]],
] = {
    1: [
        (695.0, 129.0, 790.0, 319.0),
    ],
    2: [
        (695.0, 332.0, 790.0, 777.0),
    ],
    3: [
        (793.0, 129.0, 889.0, 777.0),
    ],
    4: [
        (891.0, 129.0, 987.0, 777.0),
        (989.0, 116.0, 1088.0, 354.0),
        (1089.0, 116.0, 1180.0, 383.0),
    ],
    5: [
        (989.0, 368.0, 1088.0, 777.0),
    ],
    6: [
        (1089.0, 397.0, 1180.0, 777.0),
    ],
}


def normalize_text(value: str) -> str:
    """Normalise Unicode and whitespace."""

    value = unicodedata.normalize("NFC", value)
    value = value.replace("\u00ad", "")
    value = value.replace("\u00a0", " ")
    value = value.replace("\u2003", " ")
    value = value.replace("\u2009", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def word_text(word: tuple[Any, ...]) -> str:
    return normalize_text(str(word[4]))


def word_center(
    word: tuple[Any, ...],
) -> tuple[float, float]:
    x0, y0, x1, y1 = word[:4]

    return (
        (float(x0) + float(x1)) / 2,
        (float(y0) + float(y1)) / 2,
    )


def word_height(word: tuple[Any, ...]) -> float:
    return float(word[3]) - float(word[1])


def get_words(
    page: fitz.Page,
) -> list[tuple[Any, ...]]:
    return page.get_text(
        "words",
        sort=True,
    )


def find_month_columns(
    page: fitz.Page,
    words: list[tuple[Any, ...]],
) -> list[dict[str, Any]]:
    """Find the twelve month columns on page 1."""

    found: dict[int, tuple[Any, ...]] = {}

    for word in words:
        text = word_text(word).upper()
        month = MONTH_ALIASES.get(text)

        if month is not None and month not in found:
            found[month] = word

    missing = [
        MONTH_NAMES[month]
        for month in range(1, 13)
        if month not in found
    ]

    if missing:
        raise ValueError(
            "Fann ikki allar mánaðirnar. Mangla: "
            + ", ".join(missing)
        )

    columns: list[dict[str, Any]] = []

    for month in range(1, 13):
        word = found[month]
        x_center, _ = word_center(word)

        columns.append(
            {
                "month": month,
                "name": MONTH_NAMES[month],
                "word": word,
                "x_center": x_center,
            }
        )

    for index, column in enumerate(columns):
        center = float(column["x_center"])

        if index == 0:
            next_center = float(
                columns[index + 1]["x_center"]
            )
            left = center - ((next_center - center) / 2)
        else:
            previous_center = float(
                columns[index - 1]["x_center"]
            )
            left = (previous_center + center) / 2

        if index == len(columns) - 1:
            previous_center = float(
                columns[index - 1]["x_center"]
            )
            right = center + ((center - previous_center) / 2)
        else:
            next_center = float(
                columns[index + 1]["x_center"]
            )
            right = (center + next_center) / 2

        column["left"] = max(0.0, left)
        column["right"] = min(
            float(page.rect.width),
            right,
        )
        column["header_bottom"] = float(
            column["word"][3]
        )

    return columns


def find_date_words(
    page: fitz.Page,
    words: list[tuple[Any, ...]],
    month_columns: list[dict[str, Any]],
    year: int,
) -> dict[int, list[dict[str, Any]]]:
    """Find date numbers in every month column."""

    dates_by_month: dict[
        int,
        list[dict[str, Any]],
    ] = {}

    calendar_bottom = float(page.rect.height) * 0.79

    for column in month_columns:
        month = int(column["month"])
        left = float(column["left"])
        right = float(column["right"])
        width = right - left

        date_right = left + width * 0.42

        candidates: dict[int, dict[str, Any]] = {}

        for word in words:
            text = word_text(word)

            if not re.fullmatch(r"\d{1,2}", text):
                continue

            day = int(text)

            if not 1 <= day <= 31:
                continue

            x, y = word_center(word)

            if not left <= x <= date_right:
                continue

            if y <= float(column["header_bottom"]):
                continue

            if y >= calendar_bottom:
                continue

            try:
                actual_date = date(
                    year,
                    month,
                    day,
                )
            except ValueError:
                continue

            existing = candidates.get(day)

            if existing is None or x < float(existing["x"]):
                candidates[day] = {
                    "day": day,
                    "date": actual_date.isoformat(),
                    "x": x,
                    "y": y,
                }

        if month < 12:
            next_month = date(
                year,
                month + 1,
                1,
            )
        else:
            next_month = date(
                year + 1,
                1,
                1,
            )

        expected_count = (
            next_month - date(year, month, 1)
        ).days

        if len(candidates) != expected_count:
            raise ValueError(
                f"Mánaður {month}: væntaði "
                f"{expected_count} dato-tøl, "
                f"men fann {len(candidates)}."
            )

        dates_by_month[month] = sorted(
            candidates.values(),
            key=lambda item: int(item["day"]),
        )

    return dates_by_month


def is_area_word(text: str) -> bool:
    return text.casefold() in AREA_WORD_ALIASES


def find_area_labels(
    words: list[tuple[Any, ...]],
    month_columns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find the area labels on page 1."""

    labels: list[dict[str, Any]] = []

    numeric_words = [
        word
        for word in words
        if word_text(word) in {
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
        }
    ]

    for area_word in words:
        text = word_text(area_word)

        if not is_area_word(text):
            continue

        area_x, area_y = word_center(area_word)
        area_height = word_height(area_word)

        candidates: list[
            tuple[float, tuple[Any, ...]]
        ] = []

        for number_word in numeric_words:
            number_x, number_y = word_center(number_word)
            number_height = word_height(number_word)

            dx = number_x - area_x
            dy = abs(number_y - area_y)

            if dx < 5 or dx > 55:
                continue

            if dy > 18:
                continue

            if number_height < area_height * 0.60:
                continue

            distance = abs(dx) + dy * 2

            candidates.append(
                (
                    distance,
                    number_word,
                )
            )

        if not candidates:
            continue

        candidates.sort(
            key=lambda item: item[0]
        )

        number_word = candidates[0][1]
        area_number = int(word_text(number_word))
        number_x, number_y = word_center(number_word)

        marker_x = (area_x + number_x) / 2
        marker_y = (area_y + number_y) / 2

        month: int | None = None

        for column in month_columns:
            if (
                float(column["left"])
                <= marker_x
                < float(column["right"])
            ):
                month = int(column["month"])
                break

        if month is None:
            continue

        labels.append(
            {
                "area": area_number,
                "month": month,
                "x": marker_x,
                "y": marker_y,
            }
        )

    if not labels:
        raise ValueError(
            "Fann eingi økismerki á kalendarasíðuni."
        )

    return labels


def map_labels_to_dates(
    labels: list[dict[str, Any]],
    dates_by_month: dict[
        int,
        list[dict[str, Any]],
    ],
) -> dict[int, list[str]]:
    """Map every area label to the nearest date row."""

    result: dict[int, set[str]] = {
        area: set()
        for area in range(1, 7)
    }

    for label in labels:
        month = int(label["month"])
        label_y = float(label["y"])

        nearest_date = min(
            dates_by_month[month],
            key=lambda item: abs(
                float(item["y"]) - label_y
            ),
        )

        result[int(label["area"])].add(
            str(nearest_date["date"])
        )

    return {
        area: sorted(dates)
        for area, dates in result.items()
    }


def extract_region_lines(
    page: fitz.Page,
    region: tuple[
        float,
        float,
        float,
        float,
    ],
) -> list[str]:
    """Extract complete text lines from an absolute rectangle."""

    rectangle = fitz.Rect(*region)

    text = page.get_text(
        "text",
        clip=rectangle,
        sort=True,
    )

    return [
        normalize_text(line)
        for line in text.splitlines()
        if normalize_text(line)
    ]


def clean_street_line(
    line: str,
) -> str | None:
    """Remove headings and non-street text."""

    line = normalize_text(line)

    if not line:
        return None

    upper = line.upper()

    if re.fullmatch(
        r"[ØÏ]KI\s*[1-6]",
        upper,
    ):
        return None

    if upper.startswith(
        (
            "FINN TÍTT",
            "FINN TITT",
            "KOMMUNALA",
            "TEL ",
            "WWW.",
        )
    ):
        return None

    if line in {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }:
        return None

    return line


def extract_streets(
    page: fitz.Page,
) -> dict[int, list[str]]:
    """Extract the street lists from page 2."""

    result: dict[int, list[str]] = {}

    for area, regions in STREET_REGIONS.items():
        streets: list[str] = []

        for region in regions:
            lines = extract_region_lines(
                page,
                region,
            )

            for line in lines:
                cleaned = clean_street_line(line)

                if (
                    cleaned
                    and cleaned
                    not in SETTLEMENTS_BY_AREA.get(area, ())
                ):
                    streets.append(cleaned)

        # Preserve the printed order while removing duplicates.
        streets = list(
            dict.fromkeys(streets)
        )

        if not streets:
            raise ValueError(
                f"Eingin gøta varð funnin fyri øki {area}."
            )

        result[area] = streets

    return result


def validate_data(
    collection_dates: dict[int, list[str]],
    streets: dict[int, list[str]],
) -> list[str]:
    """Validate the generated data."""

    warnings: list[str] = []

    for area in range(1, 7):
        dates = collection_dates.get(area, [])
        area_streets = streets.get(area, [])

        if not dates:
            warnings.append(
                f"Eingin tømingardagur varð funnin fyri øki {area}."
            )

        if not area_streets:
            warnings.append(
                f"Eingin gøta varð funnin fyri øki {area}."
            )

    street_areas: dict[str, set[int]] = defaultdict(set)

    for area, area_streets in streets.items():
        for street in area_streets:
            street_areas[
                street.casefold()
            ].add(area)

    for street, areas in sorted(
        street_areas.items()
    ):
        if len(areas) > 1:
            warnings.append(
                "Sama gøta varð funnin í fleiri økjum: "
                f"{street!r} -> {sorted(areas)}"
            )

    return warnings


def build_output(
    pdf_path: Path,
    year: int,
) -> tuple[
    dict[str, Any],
    list[str],
    dict[str, Any],
]:
    """Build structured calendar data."""

    document = fitz.open(pdf_path)

    try:
        if document.page_count < 2:
            raise ValueError(
                "PDF-fílan skal hava minst tvær síður."
            )

        calendar_page = document[0]
        street_page = document[1]

        calendar_words = get_words(
            calendar_page
        )

        month_columns = find_month_columns(
            calendar_page,
            calendar_words,
        )

        dates_by_month = find_date_words(
            calendar_page,
            calendar_words,
            month_columns,
            year,
        )

        area_labels = find_area_labels(
            calendar_words,
            month_columns,
        )

        collection_dates = map_labels_to_dates(
            area_labels,
            dates_by_month,
        )

        streets = extract_streets(
            street_page
        )

        warnings = validate_data(
            collection_dates,
            streets,
        )

        output: dict[str, Any] = {
            "schema_version": 1,
            "year": year,
            "source": {
                "title": f"Grøni kalendarin {year}",
                "organisation": "Kommunala Brennistøðin",
                "file": pdf_path.name,
                "generated_at": (
                    datetime.now(timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                ),
            },
            "areas": {
                str(area): {
                    "streets": streets[area],
                    "settlements": list(
                        SETTLEMENTS_BY_AREA.get(area, ())
                    ),
                    "collection_dates": (
                        collection_dates[area]
                    ),
                }
                for area in range(1, 7)
            },
            "settlement_aliases": SETTLEMENT_ALIASES,
            "bag_deliveries": {
                "grey_bags": {
                    "months": [4, 10],
                    "exact_dates_known": False,
                    "description": (
                        "Rullur við gráum posum verða bornar "
                        "húsarhaldunum í apríl og oktober."
                    ),
                },
                "red_bag": {
                    "months": [4, 10],
                    "exact_dates_known": False,
                    "description": (
                        "Reyði posin verður útflýggjaður "
                        "í apríl og oktober."
                    ),
                },
            },
        }

        debug: dict[str, Any] = {
            "area_labels_found": len(area_labels),
            "area_labels": area_labels,
            "street_regions": {
                str(area): regions
                for area, regions in STREET_REGIONS.items()
            },
            "street_counts": {
                str(area): len(area_streets)
                for area, area_streets in streets.items()
            },
            "settlement_counts": {
                str(area): len(
                    SETTLEMENTS_BY_AREA.get(area, ())
                )
                for area in range(1, 7)
            },
            "collection_date_counts": {
                str(area): len(dates)
                for area, dates in collection_dates.items()
            },
        }

        return output, warnings, debug

    finally:
        document.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build JSON data from KOB's green calendar PDF."
        )
    )

    parser.add_argument(
        "pdf",
        type=Path,
        help="Path to the PDF file.",
    )

    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Calendar year. Default: 2026.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/green_calendar_2026.json"
        ),
        help=(
            "Output JSON file. Default: "
            "data/green_calendar_2026.json"
        ),
    )

    parser.add_argument(
        "--debug-output",
        type=Path,
        default=Path(
            "green_calendar_debug.json"
        ),
        help=(
            "Debug JSON file. Default: "
            "green_calendar_debug.json"
        ),
    )

    parser.add_argument(
        "--integration-output",
        type=Path,
        default=Path(
            "custom_components/torshavn_waste/data/"
            "green_calendar_2026.json"
        ),
        help=(
            "Copy the generated JSON into the integration. "
            "Default: custom_components/torshavn_waste/data/"
            "green_calendar_2026.json"
        ),
    )

    args = parser.parse_args()

    if not args.pdf.is_file():
        print(
            f"PDF-fílan varð ikki funnin: {args.pdf}",
            file=sys.stderr,
        )
        return 1

    try:
        output, warnings, debug = build_output(
            pdf_path=args.pdf,
            year=args.year,
        )
    except Exception as error:
        print(
            f"Feilur undir útdrátti: {error}",
            file=sys.stderr,
        )
        return 1

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    args.debug_output.write_text(
        json.dumps(
            debug,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    args.integration_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        args.integration_output.resolve()
        != args.output.resolve()
    ):
        shutil.copyfile(
            args.output,
            args.integration_output,
        )

    print()
    print(f"JSON varð goymt í: {args.output}")
    print(
        "JSON varð kopierað til integratiónina: "
        f"{args.integration_output}"
    )
    print(
        f"Debug-dáta varð goymd í: "
        f"{args.debug_output}"
    )
    print()

    for area, area_data in output["areas"].items():
        print(
            f"Øki {area}: "
            f"{len(area_data['streets'])} gøtur, "
            f"{len(area_data['settlements'])} staðir, "
            f"{len(area_data['collection_dates'])} "
            "tømingardagar"
        )

    print(
        f"\nFunnin økismerki í alt: "
        f"{debug['area_labels_found']}"
    )

    if warnings:
        print("\nÁvaringar:")

        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\nGrundvalidering: OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())