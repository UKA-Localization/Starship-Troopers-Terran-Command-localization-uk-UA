"""Збирає локалізацію в build/StreamingAssets/ і (за потреби) ставить у гру.

    python tools/build.py                    # build/StreamingAssets/{Language,Scenarios}
    python tools/build.py --drafts           # включити чернетки (status непорожній)
    python tools/build.py --install          # скопіювати в <гра>/Starship Troopers_Data/StreamingAssets/
    python tools/build.py --uninstall        # видалити ukrainian*, повернути languages.txt
    python tools/build.py --zip              # build/STTC-uk-UA-<версія>.zip для Releases

Для кожного файлу source/ створюється файл цільової мови з тією ж структурою (коментарі, роздільники, порядок),
у якому перекладені рядки підставлено, а неперекладені лишено англійською. languages.txt — оригінал + рядок
«8 = ukrainian». При --install оригінальний languages.txt зберігається поруч як languages.txt.orig.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

import sttc

OUT_DIR = sttc.BUILD_DIR / "StreamingAssets"
BACKUP_SUFFIX = ".orig"


def load_translations(drafts: bool) -> dict[str, dict[str, str]]:
    """{file: {tsv_key: translation}} — лише рядки, що йдуть у збірку."""
    by_file: dict[str, dict[str, str]] = {}
    for r in sttc.read_tsv():
        if not r["translation"] or (r["status"] and not drafts):
            continue
        by_file.setdefault(r["file"], {})[r["key"]] = r["translation"]
    return by_file


def build_languages_txt(src: bytes) -> bytes:
    text = src.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
    entry = f"{sttc.TARGET_LANG_INDEX} = {sttc.TARGET_LANG}"
    if not any(ln.split("=")[-1].strip() == sttc.TARGET_LANG for ln in lines):
        lines.append(entry)
    return (newline.join(lines) + newline).encode("utf-8")


def build(drafts: bool) -> dict[str, int]:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    translations = load_translations(drafts)
    stats = {"files": 0, "entries": 0, "translated": 0}
    for rel in sttc.source_files():
        doc = sttc.parse_game_csv((sttc.SOURCE_DIR / rel).read_bytes())
        values = translations.get(sttc.rel_str(rel), {})
        extra = sttc.EXTRA_ENTRIES if rel == Path("Language") / f"{sttc.SOURCE_LANG}.csv" else None
        out = OUT_DIR / sttc.target_path(rel)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(sttc.dump_game_csv(doc, values, extra))
        entries = [r for r in doc.entries() if r.key not in sttc.SKIP_KEYS and r.value.strip()]
        stats["files"] += 1
        stats["entries"] += len(entries)
        stats["translated"] += sum(1 for r in entries if r.tsv_key in values)
    lang_src = sttc.SOURCE_DIR / sttc.LANGUAGES_TXT
    (OUT_DIR / sttc.LANGUAGES_TXT).write_bytes(build_languages_txt(lang_src.read_bytes()))
    # assets/: шлях у репо = шлях у грі
    assets = sttc.ROOT / "assets"
    for p in assets.rglob("*"):
        if p.is_file() and p.name not in ("README.md", ".gitkeep"):
            dst = OUT_DIR / p.relative_to(assets)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)
    return stats


def game_root(game: Path) -> Path:
    base = game / sttc.STREAMING_ASSETS
    if not (base / sttc.LANGUAGES_TXT).exists():
        sys.exit(f"не знайдено {base / sttc.LANGUAGES_TXT}; вкажіть теку гри через --game")
    return base


def install(game: Path) -> int:
    base = game_root(game)
    lang = base / sttc.LANGUAGES_TXT
    backup = lang.with_name(lang.name + BACKUP_SUFFIX)
    if not backup.exists():
        shutil.copyfile(lang, backup)
    n = 0
    for p in OUT_DIR.rglob("*"):
        if p.is_file():
            dst = base / p.relative_to(OUT_DIR)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)
            n += 1
    return n


def uninstall(game: Path) -> int:
    base = game_root(game)
    n = 0
    for p in list(base.glob(f"Language/{sttc.TARGET_LANG}*.csv")) + list(base.glob(f"Scenarios/*/text_{sttc.TARGET_LANG}.csv")):
        p.unlink()
        n += 1
    lang = base / sttc.LANGUAGES_TXT
    backup = lang.with_name(lang.name + BACKUP_SUFFIX)
    if backup.exists():
        shutil.move(backup, lang)
    else:
        # резервної копії нема — прибрати наш рядок зі списку мов
        text = lang.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.split("=")[-1].strip() != sttc.TARGET_LANG]
        lang.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    return n


def make_zip() -> Path:
    version = "dev"
    try:
        import subprocess
        version = subprocess.check_output(["git", "describe", "--tags", "--always"], cwd=sttc.ROOT, text=True).strip()
    except Exception:
        pass
    path = sttc.BUILD_DIR / f"STTC-uk-UA-{version}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT_DIR.rglob("*")):
            if p.is_file():
                z.write(p, Path("StreamingAssets") / p.relative_to(OUT_DIR))
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", action="store_true", help="включити чернетки")
    ap.add_argument("--install", action="store_true", help="поставити в гру")
    ap.add_argument("--uninstall", action="store_true", help="прибрати з гри")
    ap.add_argument("--zip", action="store_true", help="зібрати архів для Releases")
    ap.add_argument("--game", default=str(sttc.GAME_DIR_DEFAULT), help="тека гри")
    args = ap.parse_args()

    if args.uninstall:
        n = uninstall(Path(args.game))
        print(f"прибрано з гри: {n} файлів, languages.txt повернуто")
        return 0

    s = build(args.drafts)
    print(f"build/StreamingAssets: {s['files']} файлів, перекладено {s['translated']} з {s['entries']} рядків"
          + (" (з чернетками)" if args.drafts else ""))
    if args.install:
        n = install(Path(args.game))
        print(f"встановлено в гру: {n} файлів (Options → Language → Українська, потім перезапуск)")
    if args.zip:
        print(f"архів: {make_zip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
