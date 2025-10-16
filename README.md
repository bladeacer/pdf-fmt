# pdf-fmt
A small Python script to extract and format text content from PDF files.

## Setup

```bash
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

## Usage
```
source ./.venv/bin/activate
python pdf-fmt.py /path/to/your_file.pdf
```

or if you are on Linux/MacOS
```
source ./.venv/bin/activate
sudo chmod +x ./pdf-fmt.py
./pdf-fmt.py /path/to/your_file.pdf
```

Extraction results would be printed and copied to your system clipboard.

## Configuration
Modify `allowed_chars_regex` and `footer_regexes` entries in
[patterns.yaml](./patterns.yaml) file.

> The entries accept regex values

## License
GPLv3, See [license file](./LICENSE) for details.
