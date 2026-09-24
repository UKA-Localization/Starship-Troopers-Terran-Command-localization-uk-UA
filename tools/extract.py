"""Оновлює translation/strings.tsv із source/, зберігаючи наявні переклади.

    python tools/extract.py                  # source/ -> strings.tsv
    python tools/extract.py --from-game      # спершу скопіювати свіжі файли з гри в source/
    python tools/extract.py --refresh-context
    python tools/extract.py --game D:/Games/STTC

Контекст рядка: розділ файлу («// #### Розділ ####», «// РОЗДІЛ»), примітка з коментаря («//,INFO: …», «//NOTE: …»,
«//{0} will be replaced…») — діє на рядки під нею до наступного роздільника, для місій — назва місії (scenario_name)
і тека. Рядок, чий оригінал змінився після минулого витягування, стає чернеткою.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import sttc

SKIP_COMMENT = re.compile(r"^(===|other\b|TOTAL\b)|\d+ entries\b")   # службові підсумки генератора файлів гри
NOTE_PREFIX = re.compile(r"^(INFO|NOTE)\s*:\s*", re.I)


def copy_from_game(game: Path) -> int:
    base = game / sttc.STREAMING_ASSETS
    if not (base / sttc.LANGUAGES_TXT).exists():
        sys.exit(f"не знайдено {base / sttc.LANGUAGES_TXT}; вкажіть теку гри через --game")
    # прибрати старі копії, щоб видалені в грі файли не лишалися в source/
    for rel in sttc.source_files():
        (sttc.SOURCE_DIR / rel).unlink()
    files = sttc.source_files(base) + [sttc.LANGUAGES_TXT]
    for rel in files:
        dst = sttc.SOURCE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base / rel, dst)
    return len(files)


FRAME = re.compile(r"^#+\s*(.*?)\s*#+,?$")   # «// #### Розділ ####»


def _comment_text(raw: str) -> str:
    text = sttc.unquote_comment(raw)[2:].strip().rstrip(",").strip()
    m = FRAME.match(text)
    if m:
        return m.group(1).strip()
    # «#» усередині лишаємо: «Don't translate names starting with #» — це зміст примітки
    return text.strip("*/, ").strip()


def extract_rows(rel: Path) -> list[dict[str, str]]:
    doc = sttc.parse_game_csv((sttc.SOURCE_DIR / rel).read_bytes())
    file = sttc.rel_str(rel)
    is_scenario = rel.parts[0] == "Scenarios"
    scenario = rel.parts[1] if is_scenario else ""
    scenario_name = next((r.value for r in doc.entries() if r.key == "scenario_name"), "")
    section, note, rows = "", "", []
    for r in doc.rows:
        if r.kind == "comment":
            text = _comment_text(r.raw)
            if not text or SKIP_COMMENT.search(text):
                continue
            if NOTE_PREFIX.match(text) or "replaced" in text:
                note = NOTE_PREFIX.sub("", text)        # примітка до рядків нижче
            else:
                section, note = text, ""              # заголовок розділу
            continue
        if r.kind == "blank":
            note = ""                                 # роздільник закриває дію примітки
            continue
        if r.key in sttc.SKIP_KEYS or not r.value.strip():
            continue
        if r.value.startswith("#"):
            continue   # службові назви редактора/камер («#cam start»): «Don't translate names starting with #»
        parts = []
        if is_scenario:
            parts.append(f"місія «{scenario_name}» ({scenario})" if scenario_name else f"місія {scenario}")
        if section:
            parts.append(section)
        if note:
            parts.append(note)
        # entities/tone порожні = ще не аналізовано конвеєром («-» він ставить сам: проаналізовано, нічого немає)
        rows.append({"file": file, "key": r.tsv_key, "original": r.value, "translation": "", "status": "",
                     "context": "; ".join(parts), "entities": "", "tone": ""})
    return rows


def merge(new: list[dict[str, str]], old: list[dict[str, str]], refresh_context: bool) -> tuple[list[dict[str, str]], dict]:
    index = {(r["file"], r["key"]): r for r in old}
    stats = {"new": 0, "changed": 0, "kept": 0, "removed": len(index)}
    for r in new:
        o = index.pop((r["file"], r["key"]), None)
        if o is None:
            stats["new"] += 1
            continue
        for c in ("translation", "status", "entities", "tone"):
            r[c] = o.get(c, r[c])
        if not refresh_context and o.get("context"):
            r["context"] = o["context"]
        if o["original"] != r["original"]:
            stats["changed"] += 1
            if r["translation"]:
                r["status"] = sttc.DRAFT_STATUS
        else:
            stats["kept"] += 1
    stats["removed"] = len(index)
    return new, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-game", action="store_true", help="спершу скопіювати файли з гри в source/")
    ap.add_argument("--refresh-context", action="store_true", help="перегенерувати колонку context для всіх рядків")
    ap.add_argument("--game", default=str(sttc.GAME_DIR_DEFAULT), help="тека гри")
    args = ap.parse_args()

    if args.from_game:
        n = copy_from_game(Path(args.game))
        print(f"source/: скопійовано {n} файлів з гри")

    files = sttc.source_files()
    if not files:
        sys.exit("source/ порожній — запустіть з --from-game")
    rows = [r for rel in files for r in extract_rows(rel)]
    rows, stats = merge(rows, sttc.read_tsv(), args.refresh_context)
    sttc.write_tsv(rows)
    translated = sum(1 for r in rows if r["translation"] and not r["status"])
    drafts = sum(1 for r in rows if r["translation"] and r["status"])
    print(f"strings.tsv: {len(rows)} рядків з {len(files)} файлів "
          f"(нових {stats['new']}, змінених {stats['changed']}, видалених {stats['removed']}); "
          f"перекладено {translated}, чернеток {drafts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
