# OBC1

スーパーファミコンのカートリッジ1本に載っているOBC1スプライトリマッパーをPythonで実装したものです。取り得るすべての状態で、固定したsnes9xのビルドと比較しています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-obc1-python)](https://github.com/gufranco/snes-obc1-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**7**個のアドレス、**256**個の状態をすべて訪問、リファレンスと比較した**3,126**ステップ、不一致**0**件、**580**個のテスト、ステートメントとブランチの**100%**カバレッジ、依存パッケージなし

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

このプログラムはポインタをスプライト2に設定し、`$7FF0`から`$7FF3`に4バイトを書き込みます。書き込んだバイトはチップのメモリのオフセット6152、つまりリセットが選んだベースから8バイト先に入ります。ゲームはすべてのスプライトの4つの属性バイトを同じ4つのアドレスに書き込み、スプライトごとにポインタを動かします。

## インストール

| 必要なもの | バージョン |
|:--|:--|
| Python | 3.12以降 |
| git | 任意。サブモジュールの取得に使います |
| C++17コンパイラ、`g++` | 適合性ウォーク用のリファレンスをビルドする場合のみ |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-obc1-python.git
cd snes-obc1-python
python3 snesobc1/doctor.py
```

このパッケージは標準ライブラリ以外を何もインポートしません。サブモジュールは`snes-driver-python`で、これを使うのは[`conformance/against_cartridges.py`](conformance/against_cartridges.py)だけです。

ドクターはマシンとチェックアウトを確認し、最後に1行を出力します。すべての確認に通れば0、そうでなければ1で終了します。バグ報告には出力全体を貼り付けてください。

```
  7 checks, nothing to report
```

リリースは[セマンティックバージョニング](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付き、[リリースページ](https://github.com/gufranco/snes-obc1-python/releases)に掲載されます。

## インターフェース

`snesobc1.Chip(model, ram=None)`はチップを1つ作ります。`model`は必須です。`ram`を渡さなければ、チップはリセットを実行します。`ram`として8,192バイトの`bytearray`を渡すと、チップはそれをコピーし、何も消去せずにコピーからベースとポインタを導出します。実際のチップにはこのような入力はありません。`ram`はセーブステートを扱うツールのために用意しています。

| モデル | 別名 | ウィンドウ | メモリ |
|:--|:--|:--|:--|
| `obc1` | `obc-1`, `obc` | `$6000`から`$7FFF` | 8,192バイト |

モデル名は大文字と小文字、ハイフン、アンダースコア、空白を区別せずに照合します。そのため`Chip("OBC-1")`も同じチップを作ります。

### 呼び出し

| 呼び出し | 効果 |
|:--|:--|
| `reset()` | 8,192バイトすべてを`FF`にし、そこからベースとポインタを読み戻します。チップを返します |
| `adopt(ram)` | `ram`をチップにコピーし、そこからベースとポインタを導出します。チップを返します |
| `read(address)` | 1バイトを返します。`$7FF0`から`$7FF4`はウィンドウを通して読み、それ以外のアドレスは自身のバイトを読みます |
| `write(address, value)` | `value`の下位8ビットを書き込みます。`$7FF0`から`$7FF6`はリマッピングに加えて、自身のオフセットにもそのバイトを格納します。`None`を返します |

### 状態

| 属性 | 意味 |
|:--|:--|
| `ram` | 8,192バイトの`bytearray`です。インデックス0がアドレス`$6000`です |
| `base` | ウィンドウが重なるスプライトテーブルのオフセットです。`0x1800`または`0x1C00` |
| `address` | ポインタです。0から127 |
| `shift` | `$7FF4`が届く共有バイト内のビット位置です。0、2、4、6のいずれか |
| `model` | 正規のモデル名です |

### モジュールの内容

| 名前 | 内容 |
|:--|:--|
| `snesobc1.MODELS` | 正規名をキーとする`Model`レコードです |
| `snesobc1.Model` | `name`、`aliases`、`summary`を持つレコードです。`build(ram=None)`はチップを返します |
| `snesobc1.models.lookup(name)` | 名前または別名に一致する`Model`を、`Chip`と同じ照合規則で返します。一致しなければ`UnknownModelError`を送出します |
| `snesobc1.UnknownModelError` | モデル名が指定されていないとき、または名前がどのモデルにも一致しないときに送出されます。メッセージには存在するモデルが列挙されます |
| `snesobc1.OutOfRange` | `read`と`write`が、`$6000`未満または`$7FFF`を超えるアドレスに対して送出します |
| `snesobc1.__version__` | インストールされているバージョンです |
| `snesobc1.chip` | アドレスの背後にある定数です。`WINDOW_START`、`WINDOW_END`、`RAM_BYTES`、`BASE_HIGH`、`BASE_LOW`、`PACKED_OFFSET`、`FIRST_REGISTER`、`PACKED_REGISTER`、`BASE_REGISTER`、`POINTER_REGISTER`、`ADDRESS_MASK`、`PACKED_MASK`、`UNWRITTEN` |

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

ウィンドウ外のアドレスは値を返さずに`OutOfRange`を送出します。カートリッジ上では、そのアドレスは基板の別の部品がデコードします。

### レジスタの読み書き

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

`$7FF5`のビット0がベースを選びます。0なら`0x1C00`、1なら`0x1800`です。`$7FF3`に書き込んだバイトは、スプライト127のエントリの最後のバイトに入ります。`$7FF5`と`$7FF6`は最後に書き込まれたバイトを読み返します。8ビットより幅の広い値は下位8ビットだけが残ります。

### コマンドラインツール

どのツールもリポジトリのルートから実行します。

| コマンド | 引数 | 終了コード |
|:--|:--|:--|
| `python3 snesobc1/doctor.py` | なし | すべての確認に通れば0、そうでなければ1 |
| `python3 -m conformance.build` | `--sources DIR`, `--output PATH`, `--pinned FILE`, `--driver-source FILE` | 0はビルド成功、1はコンパイラの失敗、2は不正なオプション、取得の失敗、`obc1.cpp`の欠落、またはマーカーの欠落 |
| `python3 -m conformance.exhaustive` | `--driver PATH` | 0は不一致なし、1はウォークの不一致、2はドライバなし、0以外で終了したドライバ、または不正なオプション |
| `python3 -m conformance.speed` | なし | 0は下限以上、1は下限未満 |
| `python3 -m conformance.documents` | `--check`, `--only SUBSTRING` | 0はすべての文書を検証済み、1は拒否された文書がある、一致なし、または不正なオプション |
| `python3 -m conformance.against_cartridges` | `CARTRIDGES OUTPUT` | 0はレジスタに到達、1はどれにも未到達、2は引数が2つ未満、ディレクトリなし、またはこの部品を持つカートリッジなし |
| `python3 -m conformance.package` | `WHEEL` | 0はすべてのモジュールが同梱されテストは含まれない、1は不具合またはファイルなし、2は引数なし |
| `python3 -m conformance.links` | なし | 0はすべてのアドレスが応答、1は消えたアドレスがある |

インストールしたコピーには`snesobc1-doctor`も入っており、同じ確認を実行します。

## チップの動作

チップは8,192バイトを保持します。ウィンドウの最上部にある7つのアドレスは、そのアドレスが指すバイトを読み書きしません。

| アドレス | 届く先 |
|:--|:--|
| `$7FF0`から`$7FF3` | `base + pointer * 4`から連続する4バイト |
| `$7FF4` | `base + 0x200 + pointer // 4`のバイトのうち2ビット |
| `$7FF5` | ビット0がベース`0x1800`または`0x1C00`を選びます |
| `$7FF6` | ポインタ、および`$7FF4`が届く2ビット |
| `$6000`から`$7FFF`のそれ以外のアドレス | 自身のバイト |

## 間違えやすい2つの点

**ポインタレジスタは1バイトで2つの役割を果たします。** 下位7ビットは、ウィンドウがどのスプライトを指すかを選びます。下位2ビット、つまり同じ2ビットは、`$7FF4`が届く共有バイト内のビットの組も選びます。ポインタを1動かすと両方が動きます。

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

**`$7FF4`はチップ内部でのリードモディファイライトです。** 4つのスプライトが1バイトを2ビットずつ共有します。そこへの書き込みは2ビットを変更し、残りの6ビットはそのままにします。

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

リセット後はすべてのバイトが`FF`です。ポインタ1を通してクリアするとビット2と3がクリアされます。続けてポインタ2を通してクリアするとビット4と5がクリアされ、最初の変更は保たれます。バイト全体を書き込むモデルなら`0x00`を2回出力し、他の3つのスプライトのビットを消してしまいます。

読み出しはバイト全体を返します。1つのスプライトの2ビットを取り出すには、`chip.shift`だけ右シフトして3でマスクします。

## リセットは見た目どおりの動作をしません

レジスタへの書き込みは、リマッピングに加えて、レジスタ自身のオフセットにもそのバイトを格納します。リセットはそれらのバイトを使って状態を復元しません。まずすべてのバイトを`FF`にし、それから書き込んだばかりのバイトからベースとポインタを読みます。そのため、必ずベース`0x1800`、ポインタ127、シフト6で終わります。適合性ウォークはこれを10個の開始状態から確認します。

保存したイメージの復元は別の呼び出しです。

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

`Chip(model, ram=...)`は保存したイメージからポインタ9を読みます。`reset()`はイメージを破棄し、ポインタ127を読みます。

## 自明でない設計判断

- メモリは素の`bytearray`であり、このファミリーのプロセッサ系のメンバーが使うスクランブルされたメモリではありません。リセットは何かが読まれる前にすべてのバイトを書き込むため、未書き込みのバイトが観測されることはありません。
- [`conformance/build.py`](conformance/build.py)は、snes9xの`obc1.cpp`ファイル全体をコンパイルせず、2つのマーカーの間からOBC1の2つの関数を取り出します。そのファイルの残りはメモリマッパーで、ビルドにはエミュレータの大部分が必要です。
- このパッケージは部品であり、クロックで動く部品ではありません。アクセスに応答するだけで、ステップ実行する命令がないため、`step`、`run_for`、サイクルカウンタはありません。

## 正しいかどうか

状態はベース（2通りのうち1つ）とポインタ（128通りのうち1つ）です。256通りの組み合わせはどれも数回の書き込みで到達できるため、ウォークはそのすべてを訪問します。

| ウォーク | ステップ | 比較する内容 |
|:--|--:|:--|
| すべての状態 | 3,076 | 各ベースとポインタについて、ウィンドウの5つのアドレスすべてに書き込んで読み、その後8,192バイトすべてを1バイトずつ比較します |
| リセット | 50 | リセットがメモリの内容を無視することを、10個の開始状態から確認します |

```bash
python3 -m conformance.build
python3 -m conformance.exhaustive
```

```
  every state: 3,076 steps agreed
  the reset: 50 steps agreed
3,126 steps, 0 walks disagreed
```

ビルドは[snes9x](https://github.com/snes9xgit/snes9x)を[`conformance/pinned.json`](conformance/pinned.json)に固定したコミットで取得し、2つの関数を[`conformance/ref/driver.cpp`](conformance/ref/driver.cpp)と一緒にコンパイルします。固定したファイルにマーカーがなくなっていれば失敗します。テストでは、誤った応答を返すドライバにもランナーを向け、ランナーが不一致を報告することを確認しています。

snes9xは2つ目の実装であり、チップの測定ではありません。snes9xとの一致が示すのは、2つの実装が一致することです。

カートリッジ自身のコードは、レジスタアドレスの2つ目の情報源です。[`conformance/against_cartridges.py`](conformance/against_cartridges.py)は、その1本のカートリッジの両方のリリースにあるドライバルーチンを、実行せずにたどります。2つを合わせると、7つのレジスタのうち6つ、`$7FF0`から`$7FF3`、`$7FF5`、`$7FF6`に到達します。[`conformance/cartridges.json`](conformance/cartridges.json)は、両カートリッジのダイジェストとともにその読み取り結果を保持し、カートリッジのバイトは一切含みません。ウォークが見るのはアドレス全体を持つ命令だけなので、`$7FF4`に到達しないことは、それが存在しないことを示しません。

[`conformance/hardware.json`](conformance/hardware.json)は、このモデルが主張する各値とその出典を保持します。文書に由来するのはパックされたオフセット`0x200`だけで、出典は4バイトのスプライト128個からなるNintendoのOAMレイアウトです。それ以外の値はすべてリファレンスに由来します。この部品に言及するメーカー文書はありません。[`conformance/divergences.json`](conformance/divergences.json)は情報源が弱い箇所を記録し、[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)は3つの未解決の問題を、それぞれを決着させる方法とともに列挙しています。

`python3 -m conformance.speed`はウィンドウ経由の読み出しを20,000回、5セット行い、毎秒500,000回を下回ると失敗します。

## 開発に参加する

| 必要なこと | 場所 |
|:--|:--|
| すべてのゲートと実行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| コーディングエージェント向けの同じ内容 | [AGENTS.md](AGENTS.md) |
| このリポジトリがファミリーの他のリポジトリと共有する標準 | [FAMILY.md](FAMILY.md) |
| バグ報告 | [GitHub Issues](https://github.com/gufranco/snes-obc1-python/issues) |
| セキュリティ報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 -m coverage erase
for file in $(find snesobc1 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

各モジュールの隣には、そのモジュール名にちなんだテストファイルがあります。カバレッジはステートメントとブランチで100%という必須のゲートです。`conformance/`以下はすべてモジュールとして実行します。スクリプト自身のディレクトリはインポートパスの先頭に入るため、そこにあるファイルが同名の標準ライブラリモジュールを隠してしまうからです。

## 参考文献

- snes9x、コミット`2971061cf07fdc6fc7d18883edf4e648eb16a6d2`の`obc1.cpp`、https://github.com/snes9xgit/snes9x 。ウォークの比較対象となるリファレンスです。ビルド時に取得し、このリポジトリには含めません。
- *SNES Development Manual, Book I*、Nintendo of America Inc.。240ページ、21,022,582バイト、SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。そのOAM構造がパックされたオフセットの根拠です。再配布できないため、このリポジトリには含まれていません。`python3 -m conformance.documents`はこれをhttps://archive.org/download/SNESDevManual/book1_text.pdf から、gitが無視する`docs/`にダウンロードし、他のファイルは拒否します。`--check`は既にあるコピーを検証します。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻むスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。snes9xは独自のライセンスの下にある別の著作物で、ビルド時に取得し、再配布しません。
