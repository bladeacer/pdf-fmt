# pdf-fmt
A small Python script to extract and format text content from PDF files.

## Setup

```bash
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

## Usage
Run the Python script directly or compile the executable.
Extraction results would be printed and copied to your system clipboard.

### Script
```bash
source ./.venv/bin/activate
python pdf-fmt.py /path/to/your_file.pdf
```

or if you are on Linux/MacOS
```bash
source ./.venv/bin/activate
sudo chmod +x ./pdf-fmt.py
./pdf-fmt.py /path/to/your_file.pdf
```

### Build as Executable
```bash
source ./.venv/bin/activate
pyinstaller --onefile --name pdf-fmt pdf-fmt.py
./dist/pdf-fmt /path/to/your_file.pdf
```

The compilation will take a while.
It will output the executable at the `dist/` directory.
> You can choose to add it to your system $PATH.

## Configuration
Modify `allowed_chars_regex` and `footer_regexes` entries in
[patterns.yaml](./patterns.yaml) file.

> The entries accept regex values

## License
GPLv3, See [license file](./LICENSE) for details.
