# MD Mermaid 转换器

[English](README.md) | [中文](README_zh.md)

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

一个强大的工具，用于将 Markdown 文件中的 Mermaid 图表渲染为 PNG/SVG 图片，并替换代码块为图片链接，提供 CLI 和 GUI 双界面。

## 功能特性

- 🎨 将 Mermaid 代码块渲染为 PNG/SVG 图片
- 🖥️ 命令行和图形界面双模式
- 🌐 图形界面支持中英双语
- 📁 灵活的输出方式：单文件或集中存储
- 🔄 智能缓存：基于内容哈希，仅重新渲染变更的图表
- 💾 三种渲染模式：
  - **导出模式**：仅生成图片，不修改 Markdown
  - **替换模式**：用图片链接替换 Mermaid 代码块
  - **保留模式**：保留源代码，在后面追加图片链接
- 🛡️ 支持自动备份，保护原始文件
- 📋 配置管理，保存常用设置

## 系统要求

安装 Mermaid CLI：

```bash
npm install -g @mermaid-js/mermaid-cli
```

## 快速开始

### 应该使用哪个界面？

**CLI（命令行）** - 适合：
- 🤖 自动化脚本和 CI/CD 流程
- 📦 批量处理大型项目
- 👨‍💻 专业开发者工作流
- ♻️ 可重复、可脚本化的操作

**GUI（图形界面）** - 适合：
- 👤 日常使用和一次性转换
- 🔧 喜欢可视化工具的用户
- ⚡ 快速配置和测试
- 🎯 不需要命令行经验

---

### 命令行界面

**基础用法**（追加图片，保留源码）：
```bash
python convert_mermaid.py -i document.md --render --keep-source
```

**替换代码块**为图片：
```bash
python convert_mermaid.py -i document.md --render
```

**仅导出**（不修改 Markdown）：
```bash
python convert_mermaid.py -i docs --recursive --export --format svg
```

**递归处理**，使用单文件图片目录：
```bash
python convert_mermaid.py -i docs --recursive --render --keep-source --images-dir per-file
```

### 图形界面

对于喜欢图形界面的用户：

```bash
python converter_gui.py
```

图形界面提供：
- 配置管理（保存/加载/删除配置）
- 可视化路径选择（文件夹或多文件）
- 实时输出日志
- 试运行模式
- 语言切换（中文/English）

## 输出选项

### 集中存储
使用 `--out-dir` 将所有图片放在一个文件夹：
```bash
python convert_mermaid.py -i docs --out-dir images/mermaid
```

### 单文件存储
使用 `--images-dir` 为每个文件创建图片文件夹：
- `--images-dir per-file`：在每个 Markdown 旁创建 `[文件名]_images` 文件夹
- `--images-dir .`：保存在同一目录
- `--images-dir images`：在每个文件旁创建 `images` 子文件夹

## 命令行选项

```
-i, --input PATH          输入 Markdown 文件或文件夹（必需）
-r, --recursive           递归处理子文件夹
-o, --out-dir PATH        集中输出目录
--images-dir DIR          单文件图片目录（相对于每个 MD 文件）
-f, --format FORMAT       输出格式：png（默认）或 svg
--render                  更新 Markdown 并添加图片链接
--export                  仅导出图片，不修改 Markdown
--keep-source             渲染时保留 Mermaid 源码（追加模式）
--backup                  修改文件前创建时间戳备份
--force                   强制重新渲染已存在的图片
--dry-run                 显示计划操作但不执行
```

## 项目结构

```
md-mermaid-converter/
├── convert_mermaid.py   # CLI 实现
├── converter_gui.py     # GUI 实现
├── profiles.json        # 保存的 GUI 配置
├── i18n.json           # 国际化字符串
├── settings.json       # 用户偏好设置（语言）
└── examples/           # 示例文件和演示文件夹
    ├── test_diagrams.md
    └── demo_tree/
```

## 使用示例

### 示例 1：文档项目
```bash
# 处理所有文档，保留源码，使用单文件图片文件夹
python convert_mermaid.py -i docs --recursive --render --keep-source --images-dir per-file --backup
```

### 示例 2：导出供外部使用
```bash
# 将所有图表导出为 SVG 到集中文件夹
python convert_mermaid.py -i notes --recursive --export --format svg --out-dir output/diagrams
```

### 示例 3：清理文档
```bash
# 用图片替换所有 Mermaid 块（更清晰的文档）
python convert_mermaid.py -i README.md --render --format png --backup
```

## GUI 配置

项目包含两个预配置：

- **default**：单文件处理，内联图片
- **demo**：递归处理 demo_tree 文件夹

你可以在 GUI 中保存自己的配置以便快速重用。

## 故障排除

**Windows 上找不到 mmdc：**
- 确保 `%APPDATA%\npm` 在你的 PATH 中
- 或设置环境变量：`MERMAID_CLI=C:\path\to\mmdc.cmd`

**图表渲染失败：**
- 检查错误日志中的 Mermaid 语法
- 在 [Mermaid Live Editor](https://mermaid.live) 上测试图表
- 更新 mermaid-cli：`npm update -g @mermaid-js/mermaid-cli`

**图片未更新：**
- 使用 `--force` 标志绕过缓存并重新渲染

## 技术亮点

- ✅ 全代码库类型提示
- ✅ 完整的文档字符串（Google 风格）
- ✅ 智能错误处理，使用特定异常
- ✅ 跨平台路径处理
- ✅ 基于内容的缓存（SHA-1 哈希）
- ✅ 模块化设计，职责清晰分离

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 更新日志

### v0.1.0 (2025-10-21)
- 初始发布
- CLI 和 GUI 界面
- 三种渲染模式（导出、替换、保留源码）
- 基于内容哈希的智能缓存
- 双语支持（中文/English）
- 配置管理
