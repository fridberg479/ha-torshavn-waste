from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect text and coordinates in the green calendar PDF."
    )

    parser.add_argument(
        "pdf",
        type=Path,
        help="Path to the PDF file.",
    )

    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"PDF-fílan varð ikki funnin: {args.pdf}")
        return 1

    document = fitz.open(args.pdf)

    try:
        page = document[0]

        print(f"Page width: {page.rect.width}")
        print(f"Page height: {page.rect.height}")
        print()

        words = page.get_text("words", sort=True)

        for word in words:
            x0, y0, x1, y1, text = word[:5]

            print(
                f"{text!r:25} "
                f"x0={x0:8.2f} "
                f"y0={y0:8.2f} "
                f"x1={x1:8.2f} "
                f"y1={y1:8.2f}"
            )

    finally:
        document.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())