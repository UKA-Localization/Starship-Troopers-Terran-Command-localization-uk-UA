# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/). Версії локалізації — `<версія-гри>-<номер-релізу>`, напр. `6.5.0-1`.

## [Unreleased]

### Fixed
- Гра більше не вилітає з критичним збоєм на місіях «Operation Guillotine» і «The Perimeter».

## [6.5.0-1] — 2026-09-19

Перший реліз: повна чернетка перекладу для Starship Troopers: Terran Command v6.5.0. Усі 7 165 рядків мають `status=fuzzy`/`unresolved` — не вичитано.

### Added
- Скелет репозиторію: документація, порожній глосарій, стиль, `pipeline.toml` за схемою [localization-pipeline-uk-UA](https://github.com/UKA-Localization/localization-pipeline-uk-UA) (плейсхолдери `{N}`, теги rich text, підписи `[…]`, переноси; групування: місія — блок, інтерфейс — за розділом), CI (GitHub Actions: актуальність `strings.tsv`, збірка).
- Оригінальні тексти гри v6.5.0 (`source/`: 24 файли `Language/english*.csv`, `languages.txt`, 84 файли `Scenarios/*/text_english.csv`).
- `translation/strings.tsv` — 7 165 рядків для перекладу (4 061 інтерфейс, 3 104 місії; 96 службових назв редактора з `#` не перекладаються) з колонкою `context` (розділ файлу, коментарі `//,INFO:`, назва місії).
- `tools/sttc.py` — парсер/серіалізатор CSV гри з побайтовим відтворенням (перевірено на всіх 108 файлах), дублікати ключів у файлі отримують суфікс `#2`.
- `tools/extract.py` — витягування рядків із гри (`--from-game`) у `strings.tsv` зі збереженням наявних перекладів; змінений оригінал → чернетка.
- `tools/build.py` — збірка `build/StreamingAssets/` (`ukrainian*.csv`, `text_ukrainian.csv`, `languages.txt` з `8 = ukrainian`, ключі `language_ukrainian` для меню), `--drafts`, `--zip`; у гру не копіює — встановлення вручну або інсталятором.
- `publish/` — шаблон нотаток до релізу, картка КУЛІ, посібник Steam (uk/en), 16 скриншотів гри українською (3440×1440).
- Глосарій: 1 135 термінів (конвеєр `analyze entities` + `glossary suggest`), 72 затверджено; скорочення через `short_of`.
- Чернетки перекладу для всіх 7 165 рядків (конвеєр `translate`, Codex gpt-5.6-sol): `status=fuzzy` / `unresolved`, вичитка триває.
