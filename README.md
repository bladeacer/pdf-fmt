# pdf-fmt

A small Python script to extract and format text content from PDF files,
with filter rules and other niceties.
> Note that this is not an OCR, use with an actual OCR if you need to extract text
> from images.

## Prerequisites

For converting non-PDF files (like `.docx`, `.pptx`, `.odt`) to PDF before
extraction, one of the following **system dependencies** must be installed and
accessible in your `$PATH`:

* **LibreOffice CLI** (`soffice` or similar)
* **Pandoc**

To use the script installer, you would need
[Git](https://git-scm.com/install/linux) and [Python](https://www.python.org/downloads/).

For building the executable, you would need [the following `nuitka` requirements](https://github.com/Nuitka/Nuitka).

---

## Usage

The script either runs from the activated `.venv`, as a compiled executable or
downloaded from the releases page.
Extraction results will be printed and copied to your system clipboard.

* To disable this behaviour, modify [the configuration file](#configuration).
* Alternatively, you can also set if the extractions should be written to an
output file.

> If you see PyMuPDF errors or find that large sections of text are missing, your
> input file contains non-text content that the extractor cannot parse. Consider
> using an OCR tool to convert the image-based text before processing it
> with pdf-fmt.

`pdf-fmt`'s core logic is located in [this Python file](./pdf-fmt.py).

### Download (recommended)

You can download the executable for your operating system at
[the releases page](https://github.com/bladeacer/pdf-fmt/releases/latest).

> If you wish to get an updated version of the executable, download the newer
> latest version and remove the old executable file.


## Installation: Run as a Script

**WARNING: Always check the contents of any script downloaded from
the internet before running it.**

The installation uses platform-specific setup scripts (`.ps1` for Windows, `.sh`
for Linux) to clone the repository, set up a Python virtual environment,
and install dependencies.

### Windows PowerShell

Run these commands in an elevated PowerShell terminal:

```powershell
# Download the script to a file
Invoke-RestMethod -Uri 'https://raw.githubusercontent.com/bladeacer/pdf-fmt/refs/heads/main/scripts/install.ps1' -OutFile install.ps1

# **Review the file contents**
Get-Content install.ps1

# Execute the script
.\install.ps1
````

### Linux

Run these commands in a Bash or Zsh terminal:

```bash
# 1. Download the script to a file
curl -o install.sh https://raw.githubusercontent.com/bladeacer/pdf-fmt/refs/heads/main/scripts/install.sh

# 2. Review the file contents (use your favourite file reader)
cat install.sh

# 3. Grant execute permissions and run the script
sudo chmod +x install.sh
./install.sh
```

### What the Scripts Do

Both platform scripts execute the following core installation steps, which set
up a contained Python virtual environment (`.venv`) to manage dependencies:

```bash
# This example assumes the use of Linux
# Venv activation is triggered differently on each OS
git clone --depth 1 https://github.com/bladeacer/pdf-fmt
python -m venv .venv

source ./.venv/bin/activate

python -m pip install uv
uv pip install -r requirements.txt
```

To update, run the scripts again.

### Build as Executable

Requires running the script installer or [the above commands](#what-the-scripts-do).

```bash
source ./.venv/bin/activate
python -m nuitka --onefile --standalone --output-dir=dist pdf-fmt.py

./dist/pdf-fmt /path/to/your_file.pdf
```

The compilation will take a while. It will output the executable to the `dist/` directory.

> You can choose to add it to your system `$PATH`.

---

## Configuration

All rules are defined in the [**`pdf-fmt.yaml`**](./pdf-fmt.yaml) file, which
uses the following categories:

* `filters`: Regex rules for allowing/excluding characters and filtering
* out headers/footers. Includes spelling enforcement.
* `conversion`: Lists supported non-PDF formats (requires LibreOffice or Pandoc).
* `formatting`: Controls line wrapping (using `min_chars_per_line` and
`max_chars_per_line`), capitalization enforcement, indentation formatting, and
page separators.
* `actions`: Defines post-extraction steps, such as copying to the
  clipboard or writing to an output file.

`pdf-fmt` will look for the configuration file under the following locations.

* `$PDF_FMT_CONFIG_PATH` environment variable
* Default configuration directory
  * `APPDATA` if you are on Windows
  * `$XDG_CONFIG_HOME` or `~/.config` if you are on Linux
* The current working directory of the script

## Contributing

Create your own fork or clone the repository. The below example shows cloning
the repository.

Do note that this repository has its own [Code of Conduct](./CODE_OF_CONDUCT.md)
and [Contributing Guide](./CONTRIBUTING.md).

### Setup

```bash
git clone https://github.com/bladeacer/pdf-fmt
sudo chmod +x scripts/dev.sh
./scripts/dev.sh
```

### Testing the GitHub Action

Makes use of [act](https://github.com/nektos/act).

```bash
curl -o act.sh https://raw.githubusercontent.com/bladeacer/pdf-fmt/refs/heads/main/scripts/act.sh
sudo chmod +x act.sh
./act.sh
```

---

## License

GPLv3, See [license file](./LICENSE) for details.

## Credits
Existing PDF tooling for inspiration, LibreOffice CLI, GitHub for hosting
and CI.

The code of conduct was adopted from the
[Contributor Covenant](https://www.contributor-covenant.org/)

The contributing guide was adopted from [conduct](https://github.com/sindresorhus/conduct)
