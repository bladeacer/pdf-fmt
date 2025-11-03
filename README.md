<p align="center">
    <a href="https://github.com/bladeacer/pdf-fmt/releases/latest">
        <img src="https://img.shields.io/github/v/release/bladeacer/pdf-fmt?style=for-the-badge&sort=semver&logo=semantic-release" referrerpolicy="noreferrer">
    </a>
    <a href="https://github.com/bladeacer/pdf-fmt/blob/master/LICENSE">
        <img src="https://img.shields.io/github/license/bladeacer/pdf-fmt?style=for-the-badge" referrerpolicy="noreferrer">
    </a>
    <a href="https://github.com/bladeacer/pdf-fmt/actions">
        <img src="https://img.shields.io/github/actions/workflow/status/bladeacer/pdf-fmt/release.yml?style=for-the-badge&logo=github" referrerpolicy="noreferrer">
    </a>
</p>

# pdf-fmt

A PDF Text Extractor, Processor, and Formatter.

`pdf-fmt` is a powerful utility designed to extract text from PDF
documents and then clean, filter, and structure the output.

It is useful for converting raw PDF dumps into clean, formatted text.

Note that `pdf-fmt` is **under active development**, you might encounter bugs
and issues.

### Features

* Raw text extraction
  * Copy to clipboard and/or write to file
* Extensive configuration schema
  * See [configuration](#configuration)
* Supports numerous formats
  * See [handling non-PDF formats](#handling-non-pdf-formats)
* Image extraction
  * Bring your own OCR
  * Under development
* and many others to come...

### Why I made this

There are plenty of PDF tooling out there, but they seems to be geared towards
OCR and generally do not help with extracting and processing the output text.

Personally, I use it to collate lecture slides for note taking and knowledge
management. I hope that it would be useful for you as well.

### What `pdf-fmt` is not

This is **not an OCR** (Optical Character Recognition) tool. It only processes
selectable text (with your cursor) found in the PDF structure.

If your file contains images of text, you can use the image extraction feature
before passing the output images to your OCR. This feature is currently under development.

### Handling non PDF formats

For converting non-PDF files (like `.docx`, `.pptx`, `.odt`) to PDF before
extraction, either **dependency** needs to be installed and accessible in your `$PATH`:

* [**LibreOffice's CLI** \(`soffice` or similar\)](https://www.libreoffice.org/)
* [**Pandoc**](https://pandoc.org/)

# Quick Start

## Download from Release Page (Recommended)

For **Windows and Linux users**, You can get the compiled binary
[the latest release](https://github.com/bladeacer/pdf-fmt/releases/latest).

After downloading, Open PowerShell or the terminal on Linux.

On Windows, run:

```ps1
cd Downloads
mv pdf-fmt-x64-0.6.1.exe pdf-fmt.exe
./pdf-fmt.exe
```

For Windows users, remember to [set execution policy](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-executionpolicy).

On Linux, run:

```bash
cd Downloads
mv pdf-fmt-x64-0.6.1 pdf-fmt
chmod +x ./pdf-fmt
./pdf-fmt
```

You can also choose to do the following after this step:

* Adding it to your system `$PATH`
* Set an alias pointing to the binary or renaming it manually
* Creating the [configuration file](#configuration)

## About Downloaded Binaries

* Choose the binary **corresponding to your operating system**
* macOS is not supported.

If you wish to get an updated version of the executable, download the newer
latest version and remove the old executable file.
> If you wish to use `pdf-fmt` on macOS, you can use the script installer or
> compile from source instead.

### About Versioning

The version number might be different from the one in the above example.

* We encourage using the latest version, especially when major new features are added

## Script Installer

You can use `pdf-fmt` via the script installer,
which sets up a isolated
[Python Virtual Environment](https://docs.python.org/3/library/venv.html)
to manage all dependencies.

## Prerequisites

* You would need to have [Git](https://git-scm.com/install) and
[Python 3.10 or above](https://www.python.org/downloads/) installed
  * To confirm, run `which git` and `which python` in a Linux/macOS terminal
  * For Windows users, run `where git` and `where python` in Command Prompt

If you **only downloading the compiled binaries**, you can ignore this part.

These prerequisites also apply to compiling from source.

* Other prerequisites are documented in the section on [compiling from source](#compile-from-source)

### Reviewing the scripts

* The script will prompt for confirmation before starting the installation

**Before running scripts, please review their contents by opening the URL they
call in a browser.** E.g. `https://raw.githubusercontent.com/...`

* Alternatively, you can view them [here](./scripts/)

### Windows

[Set execution policy to RemoteSigned.](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-executionpolicy)

Then, open PowerShell.

```ps1
Invoke-RestMethod -Uri 'https://raw.githubusercontent.com/bladeacer/pdf-fmt/refs/heads/main/scripts/install.ps1' -OutFile install.ps1
Get-Content install.ps1

.\install.ps1
```

### Linux or macOS

Open a terminal.

```bash
curl -o install.sh https://raw.githubusercontent.com/bladeacer/pdf-fmt/refs/heads/main/scripts/install.sh
cat install.sh

chmod +x install.sh
./install.sh
```

## Using the Script Installer

The installer places the Python script inside your new `.venv` folder.
Activate the environment and run the script:

For Linux or macOS

```bash
source .venv/bin/activate
chmod +x ./pdf-fmt.py
./pdf-fmt.py
```

For Windows

```ps1
.venv\Scripts\activate
pdf-fmt
```

The output is printed to the terminal and **copied to your clipboard** by default.

To update the script, run **`git pull`** in the repository the script creates
under the `pdf-fmt` directory.

## Compile from Source

Requires running the script installer or the following commands. This example
assumes the use of Linux. See the [script usage example](#using-the-script-installer)
on how to activate virtual environment for each OS.

It is recommended to use [py-env](https://github.com/pyenv/pyenv) to manage
different versions of Python. It is also recommended to install [ccache](https://github.com/ccache/ccache)
for compiled binaries to be cached. You would also need [the following `nuitka` requirements](https://github.com/Nuitka/Nuitka).

### Pyenv setup

After installing pyenv, follow its instructions on configuring with `pyenv init`.

Then, run the following immediately after you change directory into the cloned repository.

```bash
pyenv install 3.11
pyenv local 3.11
```

You can use any other target Python version, though `pdf-fmt` primarily supports
Python 3.10 or above.

### Linux/macOS

```bash
# Either clone the repository or change directory to it if you have used the
# script installer prior
git clone --depth 1 https://github.com/bladeacer/pdf-fmt
cd pdf-fmt
chmod +x ./scripts/compile.sh
./scripts/compile.sh
```

The [script](./scripts/compile.sh) creates a separate virtual environment for
compiling from source. It would output the binary to the `build/` directory once
compiling is done.
> Compilation too slow? Increase the number specified in the jobs count.
> **Only do this if you have sufficient CPU cores and hardware.**
> Remove the `--low-memory` flag at your own risk.
>
> If the compilation takes up too much memory, it will crash and exit without completing.

Compilation logs will be found at `nuitka-build.log`.
Crash reports would be found at `nuitka-crash-report.xml`.

Alternatively, you can call [this script on Linux or macOS](./scripts/compile.sh).

## Configuration

The configuration options available are documented in the
[`pdf-fmt.yaml`](./pdf-fmt.yaml) file.

* **`filters`**: Regex rules for character exclusion and pattern-based filtering
  * excluding footers matching a regex pattern.
  * includes optional spelling enforcement (UK or US English).
* **`conversion`**: Lists supported non-PDF formats (see
[handling non\-PDF formats](#handling-non-pdf-formats)).
* **`formatting`**: Controls line re-wrapping, indentation conversion
  * converting single-space indents to Markdown lists
  * enforcing capitalisation at the start of each line.
* **`actions`**: Defines post-extraction behaviour
  * copying to the system clipboard and/or write to an output file.

For extensive customisation, you can consider create your own
configuration file. If you do, ensure that it is named `pdf-fmt.yaml`.

### Where to place the configuration file

`pdf-fmt` will look for the configuration file under the following locations.

* `$PDF_FMT_CONFIG_PATH` environment variable
* Default configuration directory
  * `APPDATA` if you are on Windows
  * `$XDG_CONFIG_HOME` or `~/.config` if you are on Linux
* The current working directory of the script

### Development status

Note: the configuration schema in this repository reflects the development branch.

The released binaries might not support some options yet. These are indicated
with `[DEV]`.

## Supported platforms

This table documents the currently supported platforms for `pdf-fmt` and
highlights platforms where we are seeking community confirmation of functionality.

* Primarily, we aim to support the latest, most widely used version of each platform
* This means that LTS or stable versions of a platform are sometimes preferred
when testing for compatibility

We welcome your contributions! Please help us by:

* Opening a pull request (PR) to confirm that `pdf-fmt` works on your platform,
noting any specific setup caveats or workarounds.
* Creating an issue if you encounter problems with the installer script or
compiling from source.

| Platform | Display Protocol | C Standard Library | Known to work? | Comments |
| :--- | :--- | :--- | :--- | :--- |
| **Alpine Linux x64 (musl-based)** | X11 | `musl` | Untested | Contributions are welcome |
| **Arch Linux x64** | Wayland | `glibc` | Untested | Contributions are welcome |
| **Arch Linux x64** | X11 | `glibc` | Untested | Contributions are welcome |
| **Debian 13 x64 (glibc)** | Wayland | `glibc` | Untested | Contributions are welcome |
| **Debian 13 x86 (glibc)** | X11 | `glibc` | Untested | Contributions are welcome |
| **EndeavourOS x64 (Arch-based)** | Wayland | `glibc` | Partial | Script works out of the box. Contributions are welcome for binary/compiling from source |
| **EndeavourOS x64 (Arch-based)** | X11 | `glibc` | Yes | Binary/script/compiling from source works. |
| **Fedora 42 x64 (RPM-based)** | Wayland | `glibc` | Partial | Binary works out of the box. Contributions are welcome for script/compiling from source |
| **Fedora 42 x64 (RPM-based)** | X11 | `glibc` | Untested | Contributions are welcome |
| **FreeBSD 14 x64** | X11 | `BSD libc` | Untested | Contributions are welcome |
| **NetBSD 10 x64** | X11 | `BSD libc` | Untested | Contributions are welcome |
| **OpenBSD 7.8 x64** | X11 | `BSD libc` | Untested | Contributions are welcome |
| **Ubuntu 24.04 LTS x64 (Debian-based)** | Wayland | `glibc` | Untested | Contributions are welcome |
| **Ubuntu 24.04 LTS x64 (Debian-based)** | X11 | `glibc` | Untested | Contributions are welcome |
| **macOS 14 (Sonoma)** | N/A | `libSystem` (BSD `libc`) | Untested | Contributions are welcome |
| **Windows 10 x86** | N/A | `MSVCRT` (via `MSVC`/`MinGW`) | Untested | Contributions are welcome |
| **Windows 11 x64** | N/A | `MSVCRT` (via `MSVC`/`MinGW`) | Partial | Binary works out of the box. Contributions are welcome for script/compiling from source |

### Note: Linux users

To check the C Standard Library used on Linux, run `ldd --version`.

To check the Display Protocol currently used on Linux, run `echo $XDG_SESSION_TYPE`.

You may need to install [patchelf](https://github.com/NixOS/patchelf)

* See [Compile from source](#compile-from-source) for more details.

## Supported Python Versions

| Python Version | Known to work? | Comments |
| --- | --- | --- |
| 3.10 | Yes | Compiling from source, script works. |
| 3.11 | Yes | Compiling from source, script works. Used in GitHub Actions. |
| 3.12 | Untested | WIP |
| 3.13 | Partial | Compiling from source, script works. |

## Contributing

Create your own fork or clone the repository. The below example shows cloning
this repository with the use of Linux.

Do note that this repository has its own [Code of Conduct](./CODE_OF_CONDUCT.md)
and [Contributing Guide](./CONTRIBUTING.md).

### Setup

```bash
git clone https://github.com/bladeacer/pdf-fmt
chmod +x scripts/setup.sh
./scripts/dev.sh
```

## Benchmarks

TBC

### A note on Compatibility

The script, compiled binaries and compiling from source should work for all major
operating systems that support `Git`, `Python`,
[`pdfminer.six`](https://github.com/pdfminer/pdfminer.six) and
[`pyperclip`](https://github.com/asweigart/pyperclip).

> Note: These dependencies are slightly larger than their C equivalents, though this
> is a calculated trade off.

## Tests

### Unit Tests

TBC

### Test GitHub Action

Using [act](https://github.com/nektos/act).

```bash
curl -o act.sh https://raw.githubusercontent.com/bladeacer/pdf-fmt/refs/heads/main/scripts/act.sh
chmod +x act.sh
./act.sh
```

## License

GPLv3, See [license file](./LICENSE) for details.

### License Notice

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.

## Credits

Existing PDF tooling for inspiration, LibreOffice CLI.
Nuitka for compilation, GitHub for hosting and CI.

My friend Potato for testing the Windows binary.

The code of conduct was adopted from the
[Contributor Covenant](https://www.contributor-covenant.org/).

The contributing guide was adopted from [conduct](https://github.com/sindresorhus/conduct).
