# FlagPatcher

Додає прапор `flag_ukrainian` у ресурси гри, щоб він показувався біля «Українська» в списку мов. C#/.NET 10, [AssetsTools.NET](https://github.com/nesrak1/AssetsTools.NET).

```bash
dotnet run --project tools/FlagPatcher -- [--game "<тека гри>"] [--tpk <classdata.tpk>]
dotnet run --project tools/FlagPatcher -- --restore      # повернути оригінали
```

Що робить: у `resources.assets` клонує `flag_english` як `Texture2D` (600×400, RGBA32, #0057B7/#FFD700) і `Sprite`, у `globalgamemanagers` додає два записи `graphics/ui/languageflags/flag_ukrainian` до `ResourceManager`; оригінали зберігає як `*.orig`; повторний запуск нічого не робить. Steam «Verify integrity» відкочує патч.

`classdata.tpk` — база класів Unity для файлів без typetree, з [UABEA](https://github.com/nesrak1/UABEA) (MIT).

**Стан:** на копії файлів результат перевірено (об'єкти, картинка, записи — коректні), але після патчу в грі прапори, ймовірно, зникли всі — підозра на порядок записів у `ResourceManager` (потрібне сортування). Не використовувати до розв'язання [#1](https://github.com/UKA-Localization/Starship-Troopers-Terran-Command-localization-uk-UA/issues/1).
