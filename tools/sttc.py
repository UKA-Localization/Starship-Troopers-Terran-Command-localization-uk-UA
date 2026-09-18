"""Спільний код для скриптів локалізації Starship Troopers: Terran Command.

Шляхи гри, список файлів, парсер/серіалізатор CSV гри, читання/запис strings.tsv.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# консоль Windows типово не UTF-8 — інакше українські повідомлення скриптів перетворюються на кракозябри
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "source"
TRANSLATION_DIR = ROOT / "translation"
BUILD_DIR = ROOT / "build"
STRINGS_TSV = TRANSLATION_DIR / "strings.tsv"
GLOSSARY_TSV = TRANSLATION_DIR / "glossary.tsv"

# --- Гра -------------------------------------------------------------------------

GAME_DIR_DEFAULT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Starship Troopers - Terran Command")
# усі шляхи в source/ і в колонці file — відносно цієї теки гри
STREAMING_ASSETS = Path("Starship Troopers_Data") / "StreamingAssets"

SOURCE_LANG = "english"
TARGET_LANG = "ukrainian"
TARGET_LANG_INDEX = 8          # рядок «8 = ukrainian» у languages.txt
LANGUAGES_TXT = Path("Language") / "languages.txt"

UI_GLOB = f"Language/{SOURCE_LANG}*.csv"            # english.csv, english_0.csv … english_99.csv
SCENARIO_GLOB = f"Scenarios/*/text_{SOURCE_LANG}.csv"

# Назва мови в меню: у файлах гри ключів language_ukrainian нема — build.py дописує їх у ukrainian.csv
EXTRA_ENTRIES = {
    "language_ukrainian": "Українська",
    "language_tooltip_ukrainian": "Змінити мову гри на українську",
}

# --- strings.tsv -------------------------------------------------------------------

TSV_COLUMNS = ["file", "key", "original", "translation", "status", "context", "entities", "tone"]
DRAFT_STATUS = "fuzzy"
UNRESOLVED_STATUS = "unresolved"
SKIP_KEYS = {"build_version"}   # службові рядки — не перекладаються


def target_path(source_rel: Path) -> Path:
    """Шлях файлу цільової мови для файлу оригіналу (Language/english_3.csv → Language/ukrainian_3.csv)."""
    return source_rel.with_name(source_rel.name.replace(SOURCE_LANG, TARGET_LANG, 1))


def rel_str(p: Path) -> str:
    """Шлях у колонці file — завжди зі скісною «/»."""
    return p.as_posix()


def source_files(base: Path = SOURCE_DIR) -> list[Path]:
    """Усі файли оригіналу відносно base, у стабільному порядку (english.csv, english_0 … english_99, місії за абеткою)."""
    def ui_key(p: Path):
        stem = p.stem[len(SOURCE_LANG):]          # "", "_0", "_12"
        return (0, int(stem[1:])) if stem else (-1, 0)
    ui = sorted(base.glob(UI_GLOB), key=ui_key)
    scen = sorted(base.glob(SCENARIO_GLOB), key=lambda p: p.as_posix().lower())
    return [p.relative_to(base) for p in ui + scen]


# --- CSV гри -----------------------------------------------------------------------
#
# Формат: рядок «ключ,значення». Значення в лапках може містити коми, подвоєні лапки («""») і переноси рядків;
# без лапок — береться все після першої коми як є (у грі трапляються і коми без лапок, і хвости «,,»).
# Рядки «//…» — коментарі, «,» і порожні — роздільники. Ключ у файлі може повторюватися — тоді в TSV
# другий екземпляр отримує суфікс «#2» (occurrence-суфікс), третій — «#3» і т. д.
#
# Документ зберігає кожен рядок як є (raw), щоб build.py відтворював файл цільової мови один в один:
# змінюються лише рядки, для яких є переклад.


@dataclass
class Row:
    kind: str                 # entry | comment | blank
    raw: str                  # рядок(и) як у файлі, без завершального переносу
    key: str = ""             # для entry
    value: str = ""           # для entry — розкодоване значення
    quoted: bool = False      # для entry — значення було в лапках
    tsv_key: str = ""         # ключ з occurrence-суфіксом


@dataclass
class GameCsv:
    rows: list[Row] = field(default_factory=list)
    bom: bool = False
    newline: str = "\r\n"
    trailing_newline: bool = True   # частина файлів гри не закінчується переносом рядка

    def entries(self) -> list[Row]:
        return [r for r in self.rows if r.kind == "entry"]


def _split_logical_lines(text: str) -> list[str]:
    """Ділить текст на логічні рядки: перенос усередині значення в лапках не розриває рядок."""
    lines, buf, in_quotes, i, n = [], [], False, 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            in_quotes = not in_quotes
            buf.append(c)
        elif c == "\n" and not in_quotes:
            lines.append("".join(buf).rstrip("\r"))
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        lines.append("".join(buf).rstrip("\r"))
    return lines


def _unquote(v: str) -> tuple[str, bool]:
    """«"a ""b"" c"» → («a "b" c», True); значення без лапок — як є."""
    s = v.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1].replace('""', '"'), True
    return v, False


def _quote(v: str, force: bool = False) -> str:
    if force or any(ch in v for ch in ',"\n\r'):
        return '"' + v.replace('"', '""') + '"'
    return v


def parse_game_csv(data: bytes) -> GameCsv:
    doc = GameCsv()
    if data.startswith(b"\xef\xbb\xbf"):
        doc.bom = True
        data = data[3:]
    text = data.decode("utf-8")
    doc.newline = "\r\n" if "\r\n" in text else "\n"
    doc.trailing_newline = text.endswith("\n")
    seen: dict[str, int] = {}
    for raw in _split_logical_lines(text):
        if raw.startswith("//"):
            doc.rows.append(Row("comment", raw))
            continue
        if raw.strip() in ("", ","):
            doc.rows.append(Row("blank", raw))
            continue
        key, sep, rest = raw.partition(",")
        key = key.strip()
        if not sep or not key:
            doc.rows.append(Row("blank", raw))
            continue
        value, quoted = _unquote(rest)
        # у значеннях переноси — лише \n (назад пишемо doc.newline); поодинокі \r у файлах гри — сміття
        value = value.replace("\r\n", "\n").replace("\r", "")
        n = seen.get(key, 0) + 1
        seen[key] = n
        doc.rows.append(Row("entry", raw, key, value, quoted, key if n == 1 else f"{key}#{n}"))
    return doc


def dump_game_csv(doc: GameCsv, values: dict[str, str] | None = None, extra: dict[str, str] | None = None) -> bytes:
    """Серіалізує документ; для tsv_key з values підставляє переклад, решту рядків лишає як є.

    extra — додаткові записи «ключ,значення» в кінець файлу (для language_ukrainian у ukrainian.csv).
    """
    values = values or {}
    out = []
    for r in doc.rows:
        if r.kind == "entry" and r.tsv_key in values:
            v = values[r.tsv_key].replace("\r\n", "\n").replace("\n", doc.newline)
            out.append(r.key + "," + _quote(v, force=r.quoted))
        else:
            out.append(r.raw)
    for k, v in (extra or {}).items():
        out.append(k + "," + _quote(v.replace("\n", doc.newline)))
    text = doc.newline.join(out)
    if out and (doc.trailing_newline or extra):
        text += doc.newline
    return (b"\xef\xbb\xbf" if doc.bom else b"") + text.encode("utf-8")


# --- TSV ---------------------------------------------------------------------------


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\r\n", "\n").replace("\n", "\\n").replace("\r", "")


def _unescape(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"n": "\n", "t": "\t", "\\": "\\"}.get(n, "\\" + n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def read_tsv(path: Path = STRINGS_TSV) -> list[dict[str, str]]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8", newline="") as f:
        header = f.readline().rstrip("\r\n").split("\t")
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("\t")
            parts += [""] * (len(header) - len(parts))
            rows.append({h: _unescape(v) for h, v in zip(header, parts)})
    return rows


def write_tsv(rows: list[dict[str, str]], path: Path = STRINGS_TSV, columns: list[str] = TSV_COLUMNS) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(columns) + "\n")
        for r in rows:
            f.write("\t".join(_escape(r.get(c, "")) for c in columns) + "\n")
