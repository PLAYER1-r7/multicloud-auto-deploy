# PDF Generation Guide

This guide documents how to generate a consolidated PDF from the design documents in the `docs/` directory.
It covers the one-time environment setup, the tools used, the changes made to the pipeline scripts,
and troubleshooting steps for known errors.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [One-Time Environment Setup](#one-time-environment-setup)
3. [Running the Script](#running-the-script)
4. [Pipeline Overview](#pipeline-overview)
5. [Document Structure](#document-structure)
6. [Script Files](#script-files)
7. [Changes Made](#changes-made)
8. [Known Limitations](#known-limitations)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| pandoc | 3.1.3 | Markdown → PDF conversion |
| xelatex | TeX Live 2023 | LaTeX engine (Unicode/CJK support) |
| Noto CJK fonts | system | Japanese text rendering |
| tlmgr | TeX Live 2023 | Package manager for missing LaTeX packages |

Install Debian base packages (already present in the dev container):

```bash
sudo apt-get install -y \
  pandoc \
  texlive-xetex \
  texlive-latex-extra \
  texlive-lang-cjk \
  fonts-noto-cjk
```

---

## One-Time Environment Setup

The Debian TeX Live 2023 packages do not include every needed `.sty` file.
Use `tlmgr` in **user mode** with the TeX Live 2023 historic archive to install the missing packages.

### Step 1 — Initialize tlmgr user tree

```bash
tlmgr --usermode init-usertree
```

### Step 2 — Point tlmgr at the TL2023 archive

```bash
tlmgr --usermode option repository \
  https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2023/tlnet-final/
```

### Step 3 — Install missing packages

```bash
tlmgr --usermode install lm soul zapfding
```

| Package | Provides | Reason |
|---------|----------|--------|
| `lm` | `lmodern.sty` | Latin Modern font support |
| `soul` | `soul.sty` | Strikethrough / underline macros |
| `zapfding` | `pzdr.tfm` | ZapfDingbats font metrics |

### Step 4 — Verify installation

```bash
kpsewhich lmodern.sty   # → ~/texmf/tex/latex/lm/lmodern.sty
kpsewhich soul.sty      # → ~/texmf/tex/generic/soul/soul.sty
kpsewhich pzdr.tfm      # → ~/texmf/fonts/tfm/public/zapfding/pzdr.tfm
```

> **Important — do NOT install `ctex`, `l3kernel`, `l3backend`, or `l3packages`.**
> The Debian-packaged TeX Live 2023 contains an older version of `expl3`.
> Installing the CTAN versions of these packages creates a version mismatch that
> breaks XeLaTeX with:
> ```
> ! LaTeX3 Error: Mismatched LaTeX support files detected.
> ```
> If you accidentally install them, remove them:
> ```bash
> rm -rf ~/texmf/tex/latex/l3kernel \
>         ~/texmf/tex/latex/l3backend \
>         ~/texmf/tex/latex/l3packages
> mktexlsr ~/texmf
> ```

### Step 5 — Rebuild the filename database

```bash
mktexlsr ~/texmf
```

---

## Running the Script

> **The design documents (`docs/AI_AGENT_*.md`) only exist on the `main` branch.**
> You must be on `main` before running the script.

```bash
# Ensure you are on main
git checkout main

# Generate the PDF
bash scripts/generate-pdf-documentation.sh

# Output file
ls -lh multicloud-auto-deploy-documentation.pdf
```

Expected output file: `multicloud-auto-deploy-documentation.pdf` (~720 KB, ~120 pages).

---

## Pipeline Overview

```
docs/AI_AGENT_*.md
README.md, CONTRIBUTING.md, CHANGELOG.md
services/*/README.md
        │
        ▼
generate-pdf-documentation.sh
  ├─ Pre-processing (bash sed/awk)
  │    • Remove emoji characters
  │    • Normalise bullet list markers
  │    • Insert LaTeX page-break markers
  │    • Skip Mermaid diagrams (not rendered)
  ├─ Concatenate into single Markdown file (tmp)
  └─ pandoc
       --pdf-engine=xelatex
       --template=scripts/custom-latex-template.tex
       --include-in-header=scripts/latex-header.tex
       --lua-filter=scripts/table-columns.lua
       --highlight-style=tango --listings
        │
        ▼
  multicloud-auto-deploy-documentation.pdf
```

---

## Document Structure

The PDF is assembled from the following parts in order:

| Part | Source file | Description |
|------|-------------|-------------|
| Front matter | `README.md` | Project overview |
| 01 | `docs/AI_AGENT_01_OVERVIEW.md` | System overview |
| 02 | `docs/AI_AGENT_02_LAYOUT.md` | Repository layout |
| 03 | `docs/AI_AGENT_03_ARCHITECTURE.md` | Architecture |
| 04 | `docs/AI_AGENT_04_API.md` | API reference |
| 05 | `docs/AI_AGENT_05_INFRA.md` | Infrastructure |
| 06 | `docs/AI_AGENT_06_CICD.md` | CI/CD pipeline |
| 07 | `docs/AI_AGENT_07_STATUS.md` | Current status |
| 08 | `docs/AI_AGENT_08_RUNBOOKS.md` | Runbooks |
| 09 | `docs/AI_AGENT_09_SECURITY.md` | Security |
| 10 | `docs/AI_AGENT_10_TASKS.md` | Task backlog |
| 11 | `docs/AI_AGENT_11_WORKSPACE_MIGRATION.md` | Workspace migration |
| Services | `services/*/README.md` | Per-service READMEs |
| End matter | `CONTRIBUTING.md`, `CHANGELOG.md` | Contribution guide, changelog |

---

## Script Files

### `scripts/generate-pdf-documentation.sh`

Orchestrates the entire pipeline.  Key pandoc invocation (lines ~482–499):

```bash
pandoc "${INPUT_FILES[@]}" \
  --pdf-engine=xelatex \
  --template="$PROJECT_ROOT/scripts/custom-latex-template.tex" \
  --lua-filter="$LUA_FILTER" \
  --include-in-header="$LATEX_HEADER" \
  --highlight-style=tango \
  --listings \
  --variable documentclass=report \
  --variable fontsize=11pt \
  --variable papersize=a4 \
  --variable geometry:margin=2.5cm \
  --variable lmodern=false \
  --output "$OUTPUT_FILE"
```

### `scripts/latex-header.tex`

Custom LaTeX preamble injected via `--include-in-header`.
Handles Japanese font setup and Unicode character mappings.

### `scripts/custom-latex-template.tex`

Patched version of pandoc's default LaTeX template (`pandoc -D latex`).
Contains workarounds for missing packages.

### `scripts/table-columns.lua`

Lua filter for pandoc that normalises table column widths.

---

## Changes Made

### 1. `scripts/generate-pdf-documentation.sh`

**Problem:** Script pointed to non-existent doc files.  
**Fix:** Updated source file list to use the actual `docs/AI_AGENT_*.md` filenames.

**Problem:** Default pandoc template tried to load `lmodern.sty`.  
**Fix:** Added `--variable lmodern=false` to skip the lmodern block in the template.

**Problem:** Pandoc default template used.  
**Fix:** Added `--template=scripts/custom-latex-template.tex` to use the patched template.

---

### 2. `scripts/latex-header.tex`

**Problem:** Header used `\usepackage{xeCJK}` which requires `ctexhook.sty` (part of `ctex`).
Installing `ctex` via tlmgr causes an `expl3` version mismatch with Debian's TeX Live.

**Fix:** Replaced `xeCJK` with `fontspec` + Noto CJK JP fonts:

```latex
% BEFORE (caused ctexhook.sty error)
\usepackage{xeCJK}
\setCJKmainfont{Noto Serif CJK JP}

% AFTER (works without ctex)
\usepackage{fontspec}
\setmainfont{Noto Serif CJK JP}
\setsansfont{Noto Sans CJK JP}
\setmonofont{Noto Sans Mono CJK JP}[Scale=0.9]
```

**Problem:** Unicode arrows and Japanese punctuation inside code blocks caused
XeLaTeX errors (`Missing character` or `cannot map`).

**Fix:** Added `literate=` mappings to `\lstset`:

```latex
\lstset{
  ...
  literate=
    {→}{{->}}2
    {←}{{<-}}2
    {↑}{{{\textasciicircum}}}1
    {↓}{{v}}1
    {…}{{\ldots}}3
    {—}{{---}}3
    {–}{{--}}2
    {「}{{[}}1
    {」}{{]}}1
    {。}{{.}}1
    {、}{{,}}1
}
```

**Problem:** `\hypersetup` was called before `hyperref` was loaded.  
**Fix:** Wrapped the call in `\AtBeginDocument{}`:

```latex
\AtBeginDocument{
  \hypersetup{
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue,
    pdftitle={Multicloud Auto Deploy Documentation},
    pdfauthor={AI Agent}
  }
}
```

---

### 3. `scripts/custom-latex-template.tex`

This is a copy of `pandoc -D latex` with the following patches applied:

#### Patch A — Disable lmodern (line ~112)

```latex
% BEFORE
$if(lmodern)$
\usepackage{lmodern}
$endif$

% AFTER
% \usepackage{lmodern}  % disabled — not installed in this environment
```

The `lmodern` block was removed entirely; the `--variable lmodern=false` flag also
prevents it from being triggered, giving belt-and-suspenders protection.

#### Patch B — Replace soul.sty usage (line ~294)

```latex
% BEFORE
\usepackage{soul}
\newcommand{\st}[1]{\st{#1}}   % strikethrough

% AFTER
% soul.sty fallback — use italic for strikethrough if soul is unavailable
\newcommand{\st}[1]{\textit{#1}}
```

> `soul` is now installed via tlmgr, so the real `\st` command is available.
> This patch acts as a safety net.

#### Patch C — Replace bookmark.sty with hyperref (line ~406)

```latex
% BEFORE
\IfFileExists{bookmark.sty}{\usepackage{bookmark}}{\usepackage{hyperref}}

% AFTER
\usepackage{hyperref}
```

`bookmark.sty` was not installed; the conditional was replaced with a direct
`hyperref` load.

#### Patch D — Stub out pzdr font load (line ~408–410)

```latex
% Added to prevent XeLaTeX from trying to load pzdr.tfm via the dingbat path
\font\XeTeXLink@font=cmr10 at 1sp\relax
```

> `zapfding` is now installed via tlmgr, so `pzdr.tfm` is found correctly.
> This stub is a safety net for environments where `zapfding` is absent.

---

## Known Limitations

| Issue | Details |
|-------|---------|
| Mermaid diagrams not rendered | Architecture diagrams in `AI_AGENT_03_ARCHITECTURE.md` are skipped; `mermaid-filter` requires Node.js and `@mermaid-js/mermaid-cli` |
| Special glyphs missing | `►` (U+25BA) and `⭐` (U+2B50) are not in the Noto CJK glyph set and appear as blank boxes |
| Develop branch has no docs | `docs/AI_AGENT_*.md` files exist only on `main`; running from `develop` produces a near-empty PDF |
| Table of contents depth | Report class generates Part / Chapter / Section levels; subsection numbering may differ from the Markdown source |

---

## Troubleshooting

### `lmodern.sty not found`

```
! LaTeX Error: File `lmodern.sty' not found.
```

**Solution A** — Install via tlmgr:
```bash
tlmgr --usermode install lm
mktexlsr ~/texmf
```

**Solution B** — Pass `--variable lmodern=false` to pandoc (skips the `lmodern` block
in the template without requiring the file).

---

### `ctexhook.sty not found`

```
! LaTeX Error: File `ctexhook.sty' not found.
```

**Cause:** `\usepackage{xeCJK}` in `latex-header.tex` implicitly loads `ctex`.

**Solution:** Remove `\usepackage{xeCJK}` and use `fontspec` with Noto fonts directly
(see [Changes Made → latex-header.tex](#2-scriptslatex-headertex)).
Do **not** install `ctex` via tlmgr — it triggers an `expl3` version conflict.

---

### `expl3` version mismatch

```
! LaTeX3 Error: Mismatched LaTeX support files detected.
(LaTeX3)        Loading 'expl3' aborted!
```

**Cause:** `ctex`, `l3kernel`, `l3backend`, or `l3packages` were installed via tlmgr,
conflicting with the versions shipped in Debian's `texlive-latex-extra`.

**Solution:**
```bash
rm -rf ~/texmf/tex/latex/l3kernel \
        ~/texmf/tex/latex/l3backend \
        ~/texmf/tex/latex/l3packages \
        ~/texmf/tex/latex/ctex
mktexlsr ~/texmf
```

---

### `pzdr.tfm not found`

```
kpathsea: Running mktexmf pzdr
! I can't find file `pzdr'.
```

**Solution A** — Install `zapfding`:
```bash
tlmgr --usermode install zapfding
mktexlsr ~/texmf
```

**Solution B** — Add a stub to the custom template (see Patch D above).

---

### `soul.sty not found`

```
! LaTeX Error: File `soul.sty' not found.
```

**Solution A** — Install `soul`:
```bash
tlmgr --usermode install soul
mktexlsr ~/texmf
```

**Solution B** — The custom template already includes a fallback `\newcommand{\st}`
that renders strikethrough as italic text without requiring `soul.sty`.

---

### Unicode characters in code blocks

```
Missing character: There is no → in font [...]
```

**Cause:** Listing environments in XeLaTeX do not automatically map Unicode characters.

**Solution:** Add `literate=` mappings to `\lstset` in `latex-header.tex`
(see [Changes Made → latex-header.tex](#2-scriptslatex-headertex)).

---

### `\hypersetup` called before hyperref is loaded

```
! Undefined control sequence \hypersetup
```

**Solution:** Wrap `\hypersetup{...}` in `\AtBeginDocument{...}` in `latex-header.tex`.

---

### Empty or minimal PDF output

**Symptom:** Generated PDF has only a cover page or is < 50 KB.

**Cause:** Running the script from the `develop` branch, where `docs/AI_AGENT_*.md`
files do not exist. The script silently skips missing files.

**Solution:**
```bash
git checkout main
bash scripts/generate-pdf-documentation.sh
```

---

## Quick Reference

```bash
# Full setup + generation from scratch
git checkout main
tlmgr --usermode init-usertree
tlmgr --usermode option repository \
  https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2023/tlnet-final/
tlmgr --usermode install lm soul zapfding
mktexlsr ~/texmf
bash scripts/generate-pdf-documentation.sh
ls -lh multicloud-auto-deploy-documentation.pdf
```
