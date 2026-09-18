# Шаблон нотаток до релізу

Заголовок: `Starship Troopers: Terran Command v<версія гри> — українська локалізація <тег>` (напр. `Starship Troopers: Terran Command v6.5.0 — українська локалізація 6.5.0-1`); чернеткові релізи — pre-release

```
Українська локалізація Starship Troopers: Terran Command — версія гри v6.5.0.

## Що нового
<розділ із CHANGELOG.md для цього тегу>

## Встановлення
Розпакуйте архів у `<тека гри>\Starship Troopers_Data\StreamingAssets\` (з заміною `Language\languages.txt`),
у грі: Options → Language → Українська → перезапустіть гру.
Після оновлення гри, якщо українська зникла зі списку, — розпакуйте архів ще раз.

## Стан
Перекладено N з M рядків; чернеток (не вичитано) — K.
```

Файл релізу: `STTC-uk-UA-<тег>.zip` — вміст `build/StreamingAssets/` у теці `StreamingAssets/`.
