// FlagPatcher — додає прапор «flag_ukrainian» у ресурси гри, щоб він показувався біля «Українська» в списку мов.
//
//   dotnet run --project tools/FlagPatcher -- [--game <тека гри>] [--restore]
//
// Гра вантажить прапори через Resources.Load("Graphics/UI/LanguageFlags/flag_<мова>") — це Texture2D + Sprite
// у resources.assets і два записи в ResourceManager (globalgamemanagers). Файлової альтернативи немає, тому
// патчимо ці два файли: копіюємо flag_english (600×400) як шаблон, підставляємо своє зображення (RGBA32, без
// .resS), реєструємо шлях. Оригінали зберігаються поруч як *.orig; --restore повертає їх. Повторний запуск
// нічого не робить, якщо прапор уже є. Steam «Verify integrity» відкочує патч — тоді запустити ще раз.
using AssetsTools.NET;
using AssetsTools.NET.Extra;

const string Name = "flag_ukrainian";
const string ResourcePath = "graphics/ui/languageflags/" + Name;
const string Template = "flag_english";

var game = @"C:\Program Files (x86)\Steam\steamapps\common\Starship Troopers - Terran Command";
var restore = false;
var tpk = Path.Combine(AppContext.BaseDirectory, "classdata.tpk");
for (var i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--game": game = args[++i]; break;
        case "--restore": restore = true; break;
        case "--tpk": tpk = args[++i]; break;
        default: Console.Error.WriteLine($"невідомий аргумент {args[i]}"); return 1;
    }
}
if (!File.Exists(tpk)) tpk = Path.Combine(Directory.GetCurrentDirectory(), "classdata.tpk");

var dataDir = Path.Combine(game, "Starship Troopers_Data");
var resPath = Path.Combine(dataDir, "resources.assets");
var ggmPath = Path.Combine(dataDir, "globalgamemanagers");
if (!File.Exists(resPath) || !File.Exists(ggmPath))
{
    Console.Error.WriteLine($"не знайдено файли гри в {dataDir}; вкажіть теку гри через --game");
    return 1;
}

if (restore)
{
    var n = 0;
    foreach (var p in new[] { resPath, ggmPath })
        if (File.Exists(p + ".orig")) { File.Copy(p + ".orig", p, true); File.Delete(p + ".orig"); n++; }
    Console.WriteLine(n > 0 ? $"повернуто оригінали: {n} файлів" : "оригіналів (*.orig) немає — нічого повертати");
    return 0;
}

var manager = new AssetsManager();
manager.LoadClassPackage(tpk);
var res = manager.LoadAssetsFile(resPath, false);
manager.LoadClassDatabaseFromPackage(res.file.Metadata.UnityVersion);
var ggm = manager.LoadAssetsFile(ggmPath, false);

// --- уже є? -----------------------------------------------------------------------------
AssetFileInfo? texTemplate = null, spriteTemplate = null;
foreach (var info in res.file.GetAssetsOfType(AssetClassID.Texture2D))
{
    var name = manager.GetBaseField(res, info)["m_Name"].AsString;
    if (name == Name) { Console.WriteLine("прапор уже є в resources.assets — нічого не роблю"); return 0; }
    if (name == Template) texTemplate = info;
}
foreach (var info in res.file.GetAssetsOfType(AssetClassID.Sprite))
    if (manager.GetBaseField(res, info)["m_Name"].AsString == Template) spriteTemplate = info;
if (texTemplate is null || spriteTemplate is null)
{
    Console.Error.WriteLine($"шаблон {Template} не знайдено в resources.assets");
    return 1;
}

// --- зображення: синій зверху, жовтий знизу; Unity зберігає рядки знизу вгору ----------------
const int W = 600, H = 400;
var pixels = new byte[W * H * 4];
for (var y = 0; y < H; y++)
{
    var blue = y >= H / 2;   // верхня половина картинки = останні рядки в пам'яті
    for (var x = 0; x < W; x++)
    {
        var o = (y * W + x) * 4;
        pixels[o] = (byte)(blue ? 0x00 : 0xFF);
        pixels[o + 1] = (byte)(blue ? 0x57 : 0xD7);
        pixels[o + 2] = (byte)(blue ? 0xB7 : 0x00);
        pixels[o + 3] = 0xFF;
    }
}

// --- нові об'єкти -----------------------------------------------------------------------
var nextId = res.file.Metadata.AssetInfos.Max(a => a.PathId) + 1;
var texId = nextId;
var spriteId = nextId + 1;

var tex = manager.GetBaseField(res, texTemplate);
tex["m_Name"].AsString = Name;
tex["m_TextureFormat"].AsInt = 4;          // RGBA32 — без стиснення й без .resS
tex["m_CompleteImageSize"].AsUInt = (uint)pixels.Length;
tex["m_MipCount"].AsInt = 1;
tex["m_MipsStripped"].AsInt = 0;
tex["m_StreamingMipmaps"].AsBool = false;
tex["image data"].AsByteArray = pixels;
tex["m_StreamData"]["offset"].AsULong = 0;
tex["m_StreamData"]["size"].AsUInt = 0;
tex["m_StreamData"]["path"].AsString = "";
var texInfo = AssetFileInfo.Create(res.file, texId, (int)AssetClassID.Texture2D, manager.ClassDatabase);
texInfo.SetNewData(tex);
res.file.Metadata.AddAssetInfo(texInfo);

var sprite = manager.GetBaseField(res, spriteTemplate);
sprite["m_Name"].AsString = Name;
sprite["m_RD"]["texture"]["m_PathID"].AsLong = texId;
var guid = Guid.NewGuid().ToByteArray();
var key = sprite["m_RenderDataKey"]["first"];
key["data[0]"].AsUInt = BitConverter.ToUInt32(guid, 0);
key["data[1]"].AsUInt = BitConverter.ToUInt32(guid, 4);
key["data[2]"].AsUInt = BitConverter.ToUInt32(guid, 8);
key["data[3]"].AsUInt = BitConverter.ToUInt32(guid, 12);
var spriteInfo = AssetFileInfo.Create(res.file, spriteId, (int)AssetClassID.Sprite, manager.ClassDatabase);
spriteInfo.SetNewData(sprite);
res.file.Metadata.AddAssetInfo(spriteInfo);

// --- ResourceManager: шлях → обидва об'єкти (як у інших прапорів) ------------------------------
var rmInfo = ggm.file.GetAssetsOfType(AssetClassID.ResourceManager).Single();
var rm = manager.GetBaseField(ggm, rmInfo);
var container = rm["m_Container"]["Array"];
var sample = container.Children.First(e => e["first"].AsString == "graphics/ui/languageflags/" + Template);
var fileId = sample["second"]["m_FileID"].AsInt;
foreach (var id in new[] { texId, spriteId })
{
    var entry = ValueBuilder.DefaultValueFieldFromArrayTemplate(container);
    entry["first"].AsString = ResourcePath;
    entry["second"]["m_FileID"].AsInt = fileId;
    entry["second"]["m_PathID"].AsLong = id;
    container.Children.Add(entry);
}
rmInfo.SetNewData(rm);

// --- запис: резервні копії, потім заміна через тимчасовий файл -----------------------------------
foreach (var p in new[] { resPath, ggmPath })
    if (!File.Exists(p + ".orig")) File.Copy(p, p + ".orig");
Write(res, resPath);
Write(ggm, ggmPath);
Console.WriteLine($"додано {Name}: Texture2D #{texId}, Sprite #{spriteId}, 2 записи ResourceManager (file {fileId}); оригінали — *.orig");
return 0;

static void Write(AssetsFileInstance inst, string path)
{
    var tmp = path + ".tmp";
    using (var writer = new AssetsFileWriter(tmp)) inst.file.Write(writer);
    inst.file.Close();
    File.Move(tmp, path, true);
}
