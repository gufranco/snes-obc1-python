# OBC1

用 Python 实现的一款超级任天堂卡带中的 OBC1 精灵重映射芯片，在其全部状态下与固定版本的 snes9x 构建进行对比。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/snes-obc1-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/snes-obc1-python?style=flat-square&label=release)](https://github.com/gufranco/snes-obc1-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/snes-obc1-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/snes-obc1-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/snes-obc1-python)
[![license](https://img.shields.io/github/license/gufranco/snes-obc1-python?style=flat-square&label=license)](LICENSE)

**7** 个地址，**256** 个状态，全部访问过，**3,126** 步与参考实现对比，**0** 处分歧，**733** 个测试，**100%** 语句和分支覆盖率，无依赖

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

该程序把指针设为精灵 2，并向 `$7FF0` 到 `$7FF3` 写入四个字节。这些字节落在芯片内存的偏移 6152 处，即复位所选基址之后 8 个字节。游戏把每个精灵的四个属性字节都写到这同样的四个地址，并在精灵之间移动指针。

## 安装

| 要求               | 版本                               |
| :----------------- | :--------------------------------- |
| Python             | 3.12 或更新                        |
| git                | 任意版本，用于获取子模块           |
| C++17 编译器 `g++` | 仅在为一致性遍历构建参考实现时需要 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-obc1-python.git
cd snes-obc1-python
python3 snesobc1/doctor.py
```

本包只导入标准库中的内容。子模块是 `snes-driver-python`，只有 [`conformance/against_cartridges.py`](conformance/against_cartridges.py) 使用它。

诊断脚本检查本机和检出的代码，最后输出一行结果。所有检查通过时退出码为 0，否则为 1。提交任何缺陷报告时，请粘贴它的完整输出。

```
  7 checks, nothing to report
```

版本遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史发布。每个版本都打了标签，并列在[发布页面](https://github.com/gufranco/snes-obc1-python/releases)上。

## 接口

`snesobc1.Chip(model, ram=None)` 构建一个芯片。`model` 为必填项。不传 `ram` 时，芯片执行复位。传入 `ram`（一个 8,192 字节的 `bytearray`）时，芯片复制它，并从副本推导出基址和指针，不清除任何内容。真实芯片没有这样的输入；`ram` 参数是为携带存档状态的工具提供的。

| 型号   | 别名           | 窗口               | 内存       |
| :----- | :------------- | :----------------- | :--------- |
| `obc1` | `obc-1`、`obc` | `$6000` 到 `$7FFF` | 8,192 字节 |

型号名称匹配时不区分大小写，并忽略连字符、下划线和空格，因此 `Chip("OBC-1")` 构建的是同一个芯片。

### 调用

| 调用                    | 作用                                                                                             |
| :---------------------- | :----------------------------------------------------------------------------------------------- |
| `reset()`               | 把全部 8,192 个字节设为 `FF`，然后从中读回基址和指针。返回该芯片                                 |
| `adopt(ram)`            | 把 `ram` 复制进芯片，并从中推导出基址和指针。返回该芯片                                          |
| `read(address)`         | 返回一个字节。`$7FF0` 到 `$7FF4` 通过窗口读取；其他地址读取各自的字节                            |
| `write(address, value)` | 写入 `value` 的低 8 位。`$7FF0` 到 `$7FF6` 还会在重映射之下把该字节存到各自的偏移处。返回 `None` |

### 状态

| 属性      | 含义                                                        |
| :-------- | :---------------------------------------------------------- |
| `ram`     | 以 `bytearray` 表示的 8,192 个字节。索引 0 对应地址 `$6000` |
| `base`    | 窗口所覆盖的精灵表的偏移：`0x1800` 或 `0x1C00`              |
| `address` | 指针，0 到 127                                              |
| `shift`   | `$7FF4` 在共享字节中访问到的位位置：0、2、4 或 6            |
| `model`   | 规范型号名称                                                |

### 模块内容

| 名称                           | 内容                                                                                                                                                                                                                          |
| :----------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `snesobc1.MODELS`              | 以规范名称为键的 `Model` 记录                                                                                                                                                                                                 |
| `snesobc1.Model`               | 包含 `name`、`aliases` 和 `summary` 的记录。`build(ram=None)` 返回一个芯片                                                                                                                                                    |
| `snesobc1.models.lookup(name)` | 按与 `Chip` 相同的匹配规则，返回名称或别名所匹配的 `Model`。否则抛出 `UnknownModelError`                                                                                                                                      |
| `snesobc1.UnknownModelError`   | 未指定型号或名称不匹配任何型号时抛出。消息中列出现有的型号                                                                                                                                                                    |
| `snesobc1.OutOfRange`          | 由 `read` 和 `write` 在地址低于 `$6000` 或高于 `$7FFF` 时抛出                                                                                                                                                                 |
| `snesobc1.__version__`         | 已安装的版本                                                                                                                                                                                                                  |
| `snesobc1.chip`                | 这些地址背后的常量：`WINDOW_START`、`WINDOW_END`、`RAM_BYTES`、`BASE_HIGH`、`BASE_LOW`、`PACKED_OFFSET`、`FIRST_REGISTER`、`PACKED_REGISTER`、`BASE_REGISTER`、`POINTER_REGISTER`、`ADDRESS_MASK`、`PACKED_MASK`、`UNWRITTEN` |

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

窗口之外的地址会抛出 `OutOfRange`，而不是返回一个值。在卡带上，该地址由电路板上的其他部件译码。

### 读写寄存器

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

`$7FF5` 的第 0 位选择基址：0 对应 `0x1C00`，1 对应 `0x1800`。写入 `$7FF3` 的字节落在精灵 127 条目的最后一个字节。`$7FF5` 和 `$7FF6` 读回最后写入它们的字节。宽于 8 位的值只保留低 8 位。

### 命令行工具

所有工具都在仓库根目录下运行。

| 命令                                        | 参数                                                                      | 退出码                                                                             |
| :------------------------------------------ | :------------------------------------------------------------------------ | :--------------------------------------------------------------------------------- |
| `python3 snesobc1/doctor.py`                | 无                                                                        | 所有检查通过时为 0，否则为 1                                                       |
| `python3 -m conformance.build`              | `--sources DIR`、`--output PATH`、`--pinned FILE`、`--driver-source FILE` | 0 构建成功，1 编译器失败，2 选项错误、获取失败、缺少 `obc1.cpp` 或缺少标记         |
| `python3 -m conformance.exhaustive`         | `--driver PATH`                                                           | 0 无分歧，1 某次遍历出现分歧，2 没有驱动程序、驱动程序以非零码退出或选项错误       |
| `python3 -m conformance.speed`              | 无                                                                        | 0 达到或高于下限，1 低于下限                                                       |
| `python3 -m conformance.documents`          | `--check`、`--only SUBSTRING`                                             | 0 所有文档已验证，1 某个文档被拒绝、没有匹配项或选项错误                           |
| `python3 -m conformance.against_cartridges` | `CARTRIDGES OUTPUT`                                                       | 0 访问到了寄存器，1 一个也没访问到，2 参数少于两个、目录不存在或没有带该部件的卡带 |
| `python3 -m conformance.package`            | `WHEEL`                                                                   | 0 每个模块都已打包且不含测试，1 出现问题或文件不存在，2 没有参数                   |
| `python3 -m conformance.links`              | 无                                                                        | 0 每个地址都有响应，1 某个地址已失效                                               |
| `python3 -m conformance.quotes`             | 无                                                                        | 0 每条引文都在其引用的页面上，或文档不在本机，1 某条引文不在该页或记录中没有引文   |

安装后的副本还提供 `snesobc1-doctor`，它运行相同的检查。

## 芯片的功能

芯片拥有 8,192 个字节。其窗口顶部的七个地址并不读写它们所指的那个字节。

| 地址                              | 访问的内容                                        |
| :-------------------------------- | :------------------------------------------------ |
| `$7FF0` 到 `$7FF3`                | 位于 `base + pointer * 4` 的四个连续字节          |
| `$7FF4`                           | 位于 `base + 0x200 + pointer // 4` 的字节中的两位 |
| `$7FF5`                           | 第 0 位选择基址，`0x1800` 或 `0x1C00`             |
| `$7FF6`                           | 指针，以及 `$7FF4` 访问的那两位                   |
| `$6000` 到 `$7FFF` 之间的其他地址 | 各自的字节                                        |

## 两个容易出错的地方

**指针寄存器用一个字节完成两项工作。** 它的低 7 位选择窗口指向哪个精灵。它的低 2 位，也就是同样的那两位，还选择 `$7FF4` 访问共享字节中的哪一对位。指针移动一，两者都随之移动。

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

**`$7FF4` 是芯片内部的读-改-写。** 四个精灵共享一个字节，每个 2 位。在这里写入只改变 2 位，保留另外 6 位。

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

复位后每个字节都是 `FF`。通过指针 1 清零会清除第 2 和第 3 位。随后通过指针 2 清零会清除第 4 和第 5 位，并保留第一次的改动。如果模型写入整个字节，就会两次都打印 `0x00`，并抹掉另外三个精灵的位。

读取返回整个字节。要取出某个精灵的 2 位，右移 `chip.shift` 位，再与 3 做掩码。

## 复位并不像看上去那样

写入寄存器时，还会在重映射之下把该字节存到寄存器自身的偏移处。复位并不使用这些字节来恢复状态。它先把每个字节设为 `FF`，再从刚写入的字节中读取基址和指针，因此最终总是基址 `0x1800`、指针 127、移位 6。一致性遍历从 10 个起始状态检查这一点。

恢复已保存的镜像是另一个调用：

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

`Chip(model, ram=...)` 从保存的镜像中读出指针 9。`reset()` 丢弃该镜像，读出指针 127。

## 不显而易见的决定

- 内存是普通的 `bytearray`，而不是本系列中处理器成员所用的乱序内存。复位在任何读取之前就写入了每个字节，因此观察不到未写入的字节。
- [`conformance/build.py`](conformance/build.py) 从 snes9x 的 `obc1.cpp` 中按两个标记之间的范围提取两个 OBC1 函数，而不是编译整个文件。该文件的其余部分是一个内存映射器，构建它需要模拟器的大部分代码。
- 本包是一个部件，而不是带时钟的部件。它响应访问，没有需要单步执行的指令，因此没有 `step`、`run_for` 或周期计数器。

## 它是否正确

状态由基址（2 个之一）和指针（128 个之一）组成。这 256 种组合中的每一种都能在几次写入内到达，因此遍历会访问全部组合。

| 遍历     |  步数 | 对比的内容                                                                  |
| :------- | ----: | :-------------------------------------------------------------------------- |
| 所有状态 | 3,076 | 每个基址和指针，写入并读取全部五个窗口地址，然后逐字节对比全部 8,192 个字节 |
| 复位     |    50 | 从 10 个起始状态出发，验证复位忽略内存原有内容                              |

```bash
python3 -m conformance.build
python3 -m conformance.exhaustive
```

```
  every state: 3,076 steps agreed
  the reset: 50 steps agreed
3,126 steps, 0 walks disagreed
```

构建过程会获取 [snes9x](https://github.com/snes9xgit/snes9x) 在 [`conformance/pinned.json`](conformance/pinned.json) 中固定的提交，并用 [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp) 编译这两个函数。当固定的文件不再包含这些标记时，构建失败。测试还会让运行器指向一个给出错误应答的驱动程序，并确认它能报告分歧。

snes9x 是第二个实现，而不是对芯片的测量。与它一致只说明两个实现相符。

卡带自身的代码是寄存器地址的第二个来源。[`conformance/against_cartridges.py`](conformance/against_cartridges.py) 在不运行的情况下遍历这一款卡带两个发行版本中的驱动例程，并为每次访问的宽度加上标签：代码设定了宽度时为 known，镜像的一次运行用过该宽度时为 executed，snes-driver-python 记录的一次无头 MAME 0.289 运行在该指令处看到总线搬运该宽度时为 traced，以上都说不出时为 assumed。assumed 的访问按一个字节重放。[`conformance/cartridges.json`](conformance/cartridges.json) 保存了这一解读结果以及两个卡带的摘要，但不包含它们的任何字节。它沿每个分支的两条分路统计的 1,624 次访问中，known 183 次，traced 38 次，assumed 1,403 次。两个发行版本合计访问到全部七个寄存器。`$7FF4` 只通过 traced 的宽度被访问到：它是写往 `$7FF3` 的 16 位存储的高字节；每次存储之前的卡带字节，即带两字节立即数的 `ora #$0200` 或 `and #$FDFF`，无需模拟器即可证实这一宽度。

[`conformance/hardware.json`](conformance/hardware.json) 保存了本模型断言的每个值及其来源。只有打包偏移 `0x200` 来自文档：任天堂的 OAM 布局，即 128 个精灵、每个 4 字节。其他所有值都来自参考实现。没有任何厂商文档提到这个部件。[`conformance/divergences.json`](conformance/divergences.json) 记录了来源薄弱之处，[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出了 4 个未解决的问题，以及解决每个问题所需的条件。

`python3 -m conformance.speed` 通过窗口读取 20,000 次，重复 5 轮，低于每秒 500,000 次读取时失败。

## 参与开发

| 需求                             | 位置                                                                 |
| :------------------------------- | :------------------------------------------------------------------- |
| 所有门禁检查及其运行顺序         | [CONTRIBUTING.md](CONTRIBUTING.md)                                   |
| 面向编码代理的相同内容           | [AGENTS.md](AGENTS.md)                                               |
| 本仓库与本系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md)                                               |
| 缺陷报告                         | [GitHub Issues](https://github.com/gufranco/snes-obc1-python/issues) |
| 安全报告                         | [SECURITY.md](SECURITY.md)                                           |

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

每个模块旁边都有一个以它命名的测试文件。覆盖率是硬性门禁检查，要求语句和分支均达到 100%。`conformance/` 下的所有内容都以模块方式运行，因为脚本自身所在的目录会排在导入路径的最前面，那里的同名文件会遮蔽标准库中的同名模块。

## 参考资料

- snes9x，`obc1.cpp`，提交 `2971061cf07fdc6fc7d18883edf4e648eb16a6d2`，https://github.com/snes9xgit/snes9x 。遍历所对比的参考实现。它在构建时获取，从不随本仓库携带。
- _SNES Development Manual, Book I_，Nintendo of America Inc.。240 页，21,022,582 字节，SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。其中的 OAM 结构给出了打包偏移。该手册不可再分发，也不在本仓库中。`python3 -m conformance.documents` 从 https://archive.org/download/SNESDevManual/book1_text.pdf 将其下载到 git 忽略的 `docs/` 中，并拒绝任何其他文件。`--check` 验证已存在的副本。

## 引用本项目

[CITATION.cff](CITATION.cff) 会在每次发布时由写入包版本号的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。snes9x 是一个独立作品，适用其自身的许可证，在构建时获取，不随本仓库再分发。
