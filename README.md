# Economist Vocabulary Web App

This project turns your Economist word-frequency spreadsheets into a local SQLite database and a FastAPI web app with three main areas:

- `Level Test`: estimate the learner's current level with random words from different frequency bands
- `Learning`: multiple-choice practice for definitions now, plus synonym and sentence questions once you enrich each word
- `Dictionary`: browse by frequency band first, then A-Z

## Project structure

- `economist_vocab.py`: imports the five Excel files into SQLite and also keeps the terminal CLI
- `economist_vocab.db`: the SQLite database
- `app/main.py`: FastAPI web app
- `app/db.py`: database helpers and web tables
- `app/templates/`: HTML templates
- `app/static/style.css`: styles

## Step-by-step guide from zero

### 1. Open the project folder

```bash
cd /Users/lawrencecheng/Documents/New\ project
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 4. Import the Economist spreadsheets into SQLite

```bash
python3 economist_vocab.py import --reset
```

That loads these default workbook paths:

- `/Users/lawrencecheng/Desktop/The Economist/50~99 (3924).xlsx`
- `/Users/lawrencecheng/Desktop/The Economist/100~199 (3180).xlsx`
- `/Users/lawrencecheng/Desktop/The Economist/200~499 (3176).xlsx`
- `/Users/lawrencecheng/Desktop/The Economist/500~1999 (3000).xlsx`
- `/Users/lawrencecheng/Desktop/The Economist/2000~ (2330).xlsx`

### 5. Start the web server

```bash
uvicorn app.main:app --reload
```

Or use the included launcher:

```bash
./start_web.sh
```

### 6. Open the site in your browser

Use:

```text
http://127.0.0.1:8000
```

If the browser shows `ERR_CONNECTION_REFUSED`, it means the web server is not running yet. Go back to Terminal and start it with:

```bash
cd /Users/lawrencecheng/Documents/New\ project
./start_web.sh
```

Keep that Terminal window open while using the website.

## What each part does

### 1. Level Test

- Route: `/test`
- creates a test session
- samples words across frequency bands
- asks definition multiple-choice questions
- estimates your strongest frequency band

### 2. Learning

- Route: `/learning`
- creates a learning session
- always supports definition questions
- supports synonym and sentence questions when enrichment data exists
- updates learning progress in the database

### 3. Dictionary

- Route: `/dictionary`
- browse by band first
- then choose a letter
- then open a word page
- each word page lets you add:
  - personal notes
  - English definition
  - synonyms
  - one correct example sentence
  - wrong sentence options for future multiple-choice practice

### 4. Bulk Import

- Route: `/bulk-import`
- export an Excel template with:
  - lemma
  - frequency band
  - word type
  - Chinese definitions
  - current enrichment fields
- fill in English definitions and example sentences in Excel
- upload the file back to import many words at once

Useful CLI commands if you prefer Terminal:

```bash
python3 economist_vocab.py export-enrichment-template exports/template.xlsx --band-rank 50 --limit 300 --missing-only
python3 economist_vocab.py import-enrichment exports/template.xlsx
```

## Automatic enrichment with OpenAI API

If you want the app to generate English definitions, synonyms, and example sentences automatically:

### 1. Add your API key

Create a `.env` file in this project folder:

```bash
cp .env.example .env
```

Then edit `.env` and set:

```text
OPENAI_API_KEY=your_real_key_here
OPENAI_MODEL=gpt-5
```

### 2. Install the OpenAI Python package

```bash
python3 -m pip install openai
```

### 3. Generate a batch

From the web app:

- open `/bulk-import`
- use `Generate With OpenAI`

Or from Terminal:

```bash
python3 economist_vocab.py generate-enrichment-ai --band-rank 50 --limit 20
```

Start with small runs like `10` or `20` words so you can review quality and cost before scaling up.

## How to enrich the data for better learning questions

Your Excel files already support a strong dictionary and definition test. They do not yet contain enough synonym and example-sentence data for high-quality learning questions.

So the workflow is:

1. import the spreadsheets
2. open `/dictionary`
3. choose a band and a word
4. add:
   - synonyms, one per line
   - one correct example sentence
   - three wrong sentence options, one per line
5. save the word
6. those words become richer in `/learning`

## Useful terminal commands

Show database stats:

```bash
python3 economist_vocab.py stats
```

Look up one word in the terminal:

```bash
python3 economist_vocab.py search abduction
```

Run the terminal quiz version:

```bash
python3 economist_vocab.py quiz --limit 10 --mode mixed
```

## Notes on the source data

- duplicate words across frequency bands are merged into one study card
- the best frequency band kept for each word is the smallest band number
- each original workbook row is still preserved in `source_entries`
- rows with invalid non-text words are skipped during import
- synonym and sentence questions depend on your added enrichment data
