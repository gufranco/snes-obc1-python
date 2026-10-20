# OBC1

以 Python 實現一款 Super Nintendo 卡帶上的 OBC1 精靈重新映射晶片，並在它的每個狀態下與一個固定版本的 snes9x 比較。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-obc1-python)](https://github.com/gufranco/snes-obc1-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**7** 個位址，**256** 個狀態，全部走訪，**3,126** 步與參考實現比較，**0** 處分歧，**680** 項測試，**100%** 語句及分支覆蓋率，無任何依賴

```python
from snesobc1 import Chip

chip = Chip("obc1")
chip.write(0x7FF6, 0x02)
for offset, value in enumerate((0x10, 0x20, 0x30, 0x40)):
    chip.write(0x7FF0 + offset, value)

print(chip.base + (0x02 << 2))
print(list(chip.ram[chip.base + 8 : chip.base + 12]))
```

```
6152
[16, 32, 48, 64]
```

這段程式把指標設為精靈 2，再向 `$7FF0` 至 `$7FF3` 寫入四個位元組。它們落在晶片記憶體的偏移 6152，即重設所選基址之後 8 個位元組。遊戲把每個精靈的四個屬性位元組都寫到同樣的四個位址，並在精靈之間移動指標。

## 安裝

| 需求               | 版本                               |
| :----------------- | :--------------------------------- |
| Python             | 3.12 或更新                        |
| git                | 任何版本，用於取得子模組           |
| C++17 編譯器 `g++` | 只在為一致性走訪建置參考實現時需要 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-obc1-python.git
cd snes-obc1-python
python3 snesobc1/doctor.py
```

套件不匯入標準程式庫以外的任何東西。子模組是 `snes-driver-python`，只有 [`conformance/against_cartridges.py`](conformance/against_cartridges.py) 使用它。

診斷腳本檢查本機及這份簽出，最後輸出一行。所有檢查通過時以 0 結束，否則以 1 結束。提交錯誤報告時，請貼上它的完整輸出。

```
  7 checks, nothing to report
```

發佈遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每次發佈都會加上標籤，並列在[發佈頁面](https://github.com/gufranco/snes-obc1-python/releases)上。

## 介面

`snesobc1.Chip(model, ram=None)` 建立一個晶片。`model` 為必填。沒有 `ram` 時，晶片執行重設。提供 `ram` 時，它須是 8,192 位元組的 `bytearray`，晶片複製它，並從副本推導基址及指標，不清除任何內容。實際晶片沒有這樣的輸入；`ram` 參數是為攜帶存檔狀態的工具而設。

| 型號   | 別名           | 窗口               | 記憶體       |
| :----- | :------------- | :----------------- | :----------- |
| `obc1` | `obc-1`, `obc` | `$6000` 至 `$7FFF` | 8,192 位元組 |

比對型號名稱時不區分大小寫、連字號、底線及空格，所以 `Chip("OBC-1")` 建立的是同一個晶片。

### 呼叫

| 呼叫                    | 效果                                                                                                 |
| :---------------------- | :--------------------------------------------------------------------------------------------------- |
| `reset()`               | 把全部 8,192 個位元組設為 `FF`，再從中讀回基址及指標。回傳晶片                                       |
| `adopt(ram)`            | 把 `ram` 複製到晶片內，並從中推導基址及指標。回傳晶片                                                |
| `read(address)`         | 回傳一個位元組。`$7FF0` 至 `$7FF4` 經由窗口讀取；其他位址讀取各自的位元組                            |
| `write(address, value)` | 寫入 `value` 的低 8 位。`$7FF0` 至 `$7FF6` 在重新映射之外，也會把該位元組存到各自的偏移。回傳 `None` |

### 狀態

| 屬性      | 含義                                                          |
| :-------- | :------------------------------------------------------------ |
| `ram`     | 以 `bytearray` 表示的 8,192 個位元組。索引 0 對應位址 `$6000` |
| `base`    | 窗口所覆蓋的精靈表的偏移：`0x1800` 或 `0x1C00`                |
| `address` | 指標，0 至 127                                                |
| `shift`   | `$7FF4` 在共用位元組中觸及的位元位置：0、2、4 或 6            |
| `model`   | 正式型號名稱                                                  |

### 模組內容

| 名稱                           | 內容                                                                                                                                                                                                                      |
| :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `snesobc1.MODELS`              | 以正式名稱為鍵的 `Model` 記錄                                                                                                                                                                                             |
| `snesobc1.Model`               | 包含 `name`、`aliases` 及 `summary` 的記錄。`build(ram=None)` 回傳一個晶片                                                                                                                                                |
| `snesobc1.models.lookup(name)` | 按與 `Chip` 相同的比對規則，回傳名稱或別名所對應的 `Model`。否則拋出 `UnknownModelError`                                                                                                                                  |
| `snesobc1.UnknownModelError`   | 未指定型號，或名稱不對應任何型號時拋出。訊息列出現有的型號                                                                                                                                                                |
| `snesobc1.OutOfRange`          | `read` 及 `write` 遇到低於 `$6000` 或高於 `$7FFF` 的位址時拋出                                                                                                                                                            |
| `snesobc1.__version__`         | 已安裝的版本                                                                                                                                                                                                              |
| `snesobc1.chip`                | 位址背後的常數：`WINDOW_START`、`WINDOW_END`、`RAM_BYTES`、`BASE_HIGH`、`BASE_LOW`、`PACKED_OFFSET`、`FIRST_REGISTER`、`PACKED_REGISTER`、`BASE_REGISTER`、`POINTER_REGISTER`、`ADDRESS_MASK`、`PACKED_MASK`、`UNWRITTEN` |

```python
import snesobc1

for name, model in snesobc1.MODELS.items():
    print(name, model.aliases, model)

chip = snesobc1.Chip("OBC-1")
print(chip, chip.model)

for named in (None, "obc2"):
    try:
        snesobc1.Chip(named)
    except snesobc1.UnknownModelError as error:
        print(error)

try:
    chip.read(0x8000)
except snesobc1.OutOfRange as error:
    print(error)
```

```
obc1 ('obc-1', 'obc') <Model obc1, answering at 0x6000>
<OBC1 base 0x1800 pointer 0x7f shift 6> obc1
no model was named, and this package will not choose one for you. Name one of: obc1
no model called 'obc2'; this package publishes obc1
0x8000 is not an address this chip answers
```

窗口以外的位址會拋出 `OutOfRange`，而不是回傳一個值。在卡帶上，該位址由電路板的其他部分解碼。

### 讀寫暫存器

```python
from snesobc1 import Chip

chip = Chip("obc1")
chip.write(0x7FF5, 0x00)
chip.write(0x7FF6, 0x7F)
chip.write(0x7FF3, 0x12)
print(hex(chip.base), chip.address, chip.shift)
print(hex(chip.read(0x7FF3)), hex(chip.ram[0x1C00 + 0x7F * 4 + 3]))
print(hex(chip.read(0x7FF5)), hex(chip.read(0x7FF6)), hex(chip.read(0x6000)))
chip.write(0x6000, 0x1FF)
print(hex(chip.read(0x6000)))
```

```
0x1c00 127 6
0x12 0x12
0x0 0x7f 0xff
0xff
```

`$7FF5` 的位元 0 選擇基址：0 對應 `0x1C00`，1 對應 `0x1800`。寫入 `$7FF3` 的位元組落在精靈 127 項目的最後一個位元組。`$7FF5` 及 `$7FF6` 讀回最後寫入它們的位元組。超過 8 位的值只保留低 8 位。

### 命令列工具

所有工具都在儲存庫根目錄執行。

| 命令                                        | 參數                                                                      | 結束碼                                                                                 |
| :------------------------------------------ | :------------------------------------------------------------------------ | :------------------------------------------------------------------------------------- |
| `python3 snesobc1/doctor.py`                | 無                                                                        | 所有檢查通過時為 0，否則為 1                                                           |
| `python3 -m conformance.build`              | `--sources DIR`、`--output PATH`、`--pinned FILE`、`--driver-source FILE` | 0 建置成功，1 編譯器失敗，2 選項錯誤、取得失敗、缺少 `obc1.cpp` 或缺少標記             |
| `python3 -m conformance.exhaustive`         | `--driver PATH`                                                           | 0 沒有分歧，1 有走訪出現分歧，2 沒有驅動程式、驅動程式以非零值結束，或選項錯誤         |
| `python3 -m conformance.speed`              | 無                                                                        | 0 達到或高於下限，1 低於下限                                                           |
| `python3 -m conformance.documents`          | `--check`、`--only SUBSTRING`                                             | 0 所有文件已驗證，1 有文件被拒、沒有任何匹配，或選項錯誤                               |
| `python3 -m conformance.against_cartridges` | `CARTRIDGES OUTPUT`                                                       | 0 觸及了暫存器，1 未觸及任何暫存器，2 參數少於兩個、目錄不存在，或沒有帶這個零件的卡帶 |
| `python3 -m conformance.package`            | `WHEEL`                                                                   | 0 所有模組都已包含且不含測試，1 有錯誤或檔案不存在，2 沒有參數                         |
| `python3 -m conformance.links`              | 無                                                                        | 0 所有網址都有回應，1 有網址已失效                                                     |
| `python3 -m conformance.quotes`             | 無                                                                        | 0 每條引文都在其引用的頁面上，或文件不在本機，1 有引文不在該頁或記錄中沒有引文         |

安裝後的副本還提供 `snesobc1-doctor`，執行相同的檢查。

## 晶片做甚麼

晶片持有 8,192 個位元組。其窗口頂端的七個位址並不讀寫它們所指名的位元組。

| 位址                                  | 觸及的內容                                              |
| :------------------------------------ | :------------------------------------------------------ |
| `$7FF0` 至 `$7FF3`                    | 位於 `base + pointer * 4` 的四個連續位元組              |
| `$7FF4`                               | 位於 `base + 0x200 + pointer // 4` 的位元組中的兩個位元 |
| `$7FF5`                               | 位元 0 選擇基址，`0x1800` 或 `0x1C00`                   |
| `$7FF6`                               | 指標，以及 `$7FF4` 觸及的兩個位元                       |
| `$6000` 至 `$7FFF` 之間的任何其他位址 | 它自己的位元組                                          |

## 兩處容易弄錯的地方

**指標暫存器用一個位元組做兩件事。** 它的低 7 位選擇窗口指向哪個精靈。它的低 2 位，即同樣那兩位，還選擇 `$7FF4` 觸及共用位元組中的哪一對位元。指標移動一格，兩者同時移動。

```python
from snesobc1 import Chip

chip = Chip("obc1")
chip.write(0x7FF6, 0x05)

print(chip.address)
print(chip.shift)
```

```
5
2
```

**`$7FF4` 在晶片內部是讀取、修改、寫回。** 四個精靈共用一個位元組，每個佔 2 位。寫入該處只改變 2 位，其餘 6 位保持不變。

```python
from snesobc1 import Chip

chip = Chip("obc1")

chip.write(0x7FF6, 0x01)
chip.write(0x7FF4, 0x00)
print(f"{chip.read(0x7FF4):#04x}")

chip.write(0x7FF6, 0x02)
chip.write(0x7FF4, 0x00)
print(f"{chip.read(0x7FF4):#04x}")
```

```
0xf3
0xc3
```

重設把每個位元組都設為 `FF`。經由指標 1 清除，會清除位元 2 及 3。接着經由指標 2 清除，會清除位元 4 及 5，並保留第一次的改動。若模型寫入整個位元組，就會兩次都印出 `0x00`，並抹去其他三個精靈的位元。

讀取回傳整個位元組。要取出一個精靈的 2 位，先右移 `chip.shift` 位，再與 3 做遮罩。

## 重設並非表面看來那樣

寫入暫存器時，也會在重新映射之外把該位元組存到暫存器自己的偏移。重設並不使用這些位元組來恢復狀態。它先把每個位元組設為 `FF`，再從剛寫入的位元組讀出基址及指標，所以結果必定是基址 `0x1800`、指標 127、移位 6。一致性走訪從 10 個起始狀態檢查這一點。

還原已儲存的映像檔是另一個呼叫：

```python
from snesobc1 import Chip

saved = bytearray(0x2000)
saved[0x1FF6] = 0x09

print(Chip("obc1", ram=saved).address)
print(Chip("obc1", ram=saved).reset().address)
```

```
9
127
```

`Chip(model, ram=...)` 從已儲存的映像檔讀出指標 9。`reset()` 捨棄映像檔，讀出指標 127。

## 不明顯的決定

- 記憶體是普通的 `bytearray`，而不是本系列中處理器成員所用的打亂記憶體。重設在任何讀取之前寫入每個位元組，所以觀察不到未寫入的位元組。
- [`conformance/build.py`](conformance/build.py) 在兩個標記之間，從 snes9x 的 `obc1.cpp` 抽出兩個 OBC1 函數，而不是編譯整個檔案。該檔案的其餘部分是一個記憶體映射器，需要模擬器的大部分才能建置。
- 這個套件是一個零件，而不是有時鐘的零件。它回應存取，沒有可單步執行的指令，所以沒有 `step`、`run_for` 或週期計數器。

## 它是否正確

狀態由基址及指標組成，基址有 2 個可能值，指標有 128 個。全部 256 種組合都能在幾次寫入內到達，所以走訪全部經過。

| 走訪     |  步數 | 比較甚麼                                                                  |
| :------- | ----: | :------------------------------------------------------------------------ |
| 每個狀態 | 3,076 | 每個基址及指標，寫入並讀取全部五個窗口位址，再逐一比較全部 8,192 個位元組 |
| 重設     |    50 | 從 10 個起始狀態確認重設忽略記憶體原有的內容                              |

```bash
python3 -m conformance.build
python3 -m conformance.exhaustive
```

```
  every state: 3,076 steps agreed
  the reset: 50 steps agreed
3,126 steps, 0 walks disagreed
```

建置會在 [`conformance/pinned.json`](conformance/pinned.json) 固定的提交上取得 [snes9x](https://github.com/snes9xgit/snes9x)，並以 [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp) 編譯那兩個函數。當固定的檔案不再含有標記時，建置失敗。測試還會讓執行器指向一個回答錯誤的驅動程式，並確認它報告分歧。

snes9x 是第二個實現，而不是對晶片的量度。與它一致，表示兩個實現相符。

卡帶本身的程式碼是暫存器位址的第二個來源。[`conformance/against_cartridges.py`](conformance/against_cartridges.py) 在不執行的情況下，走訪這款卡帶兩個發行版本中的驅動常式，並為每次存取的寬度加上標籤：程式碼設定了寬度時為 known，映像檔的一次執行用過該寬度時為 executed，snes-driver-python 記錄的一次無頭 MAME 0.289 執行在該指令處看到匯流排搬運該寬度時為 traced，以上都說不出時為 assumed。assumed 的存取按一個位元組重放。[`conformance/cartridges.json`](conformance/cartridges.json) 保存這次解讀，連同兩款卡帶的摘要值，但不含它們的任何位元組。它沿每個分支的兩條分路統計的 1,624 次存取中，known 183 次，traced 38 次，assumed 1,403 次。兩個發行版本合起來觸及全部七個暫存器。`$7FF4` 只透過 traced 的寬度被觸及：它是寫往 `$7FF3` 的 16 位元儲存的高位元組；每次儲存之前的卡帶位元組，即帶兩位元組立即值的 `ora #$0200` 或 `and #$FDFF`，無需模擬器便證實了這個寬度。

[`conformance/hardware.json`](conformance/hardware.json) 保存這個模型斷言的每個值及其來源。只有打包偏移 `0x200` 來自文件：Nintendo 的 OAM 佈局，128 個精靈，每個 4 位元組。其他每個值都來自參考實現。沒有任何製造商文件提及這個零件。[`conformance/divergences.json`](conformance/divergences.json) 記錄來源薄弱之處，[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出 4 個未解決的問題，以及能解決每個問題的依據。

`python3 -m conformance.speed` 經由窗口讀取 20,000 次，重複 5 遍，低於每秒 500,000 次讀取時失敗。

## 參與開發

| 需要                                   | 位置                                                                 |
| :------------------------------------- | :------------------------------------------------------------------- |
| 每個關卡檢查及執行次序                 | [CONTRIBUTING.md](CONTRIBUTING.md)                                   |
| 給編程代理的同樣資料                   | [AGENTS.md](AGENTS.md)                                               |
| 這個儲存庫與本系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md)                                               |
| 錯誤報告                               | [GitHub Issues](https://github.com/gufranco/snes-obc1-python/issues) |
| 安全報告                               | [SECURITY.md](SECURITY.md)                                           |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for file in $(find snesobc1 conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$file"
done
"${cov[@]}" report
```

每個模組旁邊都有一個以它命名的測試檔案。覆蓋率是硬性關卡，語句及分支均須 100%。`conformance/` 下的所有內容都以模組方式執行，因為腳本所在的目錄排在匯入路徑首位，該目錄中的檔案會遮蔽標準程式庫中同名的模組。

## 參考資料

- snes9x，`obc1.cpp`，提交 `2971061cf07fdc6fc7d18883edf4e648eb16a6d2`，https://github.com/snes9xgit/snes9x 。這是走訪所比較的參考實現。它在建置時取得，從不存放在這裏。
- _SNES Development Manual, Book I_，Nintendo of America Inc.。240 頁，21,022,582 位元組，SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。它的 OAM 結構給出打包偏移。它不可轉發，也不在這個儲存庫中。`python3 -m conformance.documents` 從 https://archive.org/download/SNESDevManual/book1_text.pdf 把它下載到 git 忽略的 `docs/`，並拒絕任何其他檔案。`--check` 驗證已存在的副本。

## 引用

[CITATION.cff](CITATION.cff) 在每次發佈時，由寫入套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。snes9x 是另一部作品，採用自己的授權，在建置時取得，不會轉發。
