# PDF Toolkit

A small local web app for working with PDFs on your own computer:

- **Sign** – place a signature on a PDF form and download the signed copy.
- **Compress** – shrink PDF file size.

**Everything runs locally.** Files are processed on your machine by a small Python server bound to `127.0.0.1`. Nothing is uploaded to a cloud service.

## Requirements

- macOS or Linux (Windows should work with small changes to the commands below)
- Python 3

## Installation

```bash
git clone https://github.com/rotemalul/JS.git
cd JS/pdf-toolkit

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
./run.sh
```

Then open in your browser:

- Sign: <http://127.0.0.1:5050/sign>
- Compress: <http://127.0.0.1:5050/>

To stop the app, press `Ctrl+C` in the terminal.

## Where your files go

While working, the app keeps files in these folders inside `pdf-toolkit/`:

| Folder | Contents |
|---|---|
| `sign_jobs/` | Original and signed PDFs, page previews |
| `compressed/` | Compressed PDFs |
| `uploads/` | Uploaded files |

They stay on your computer and are excluded from git by `.gitignore`. Delete them whenever you like.

## Legal note

A signature image placed on a PDF is a simple electronic signature. It is **not** a certified/qualified digital signature backed by a certificate authority. Check whether that is sufficient for your document.

This software is provided as-is, without warranty of any kind.

---

## בעברית בקצרה

כלי מקומי לחתימה וכיווץ של קובצי PDF. הכל רץ על המחשב שלך, שום קובץ לא עולה לענן.

התקנה והפעלה: מריצים את הפקודות בסעיפים **Installation** ו-**Running** למעלה, ופותחים בדפדפן את <http://127.0.0.1:5050/sign>.
