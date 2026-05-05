# Web Application for Regex Pattern Matching and Replacement

This project is a full-stack web application that lets users upload CSV or Excel files, describe text replacement tasks in natural language, and apply regex-based replacements to the uploaded data.

The application uses a Django REST Framework backend for file processing and data operations, a React + Vite frontend for the user interface, and the OpenAI API to convert natural language instructions into regex replacement plans.

## Main Features

- Upload `.csv`, `.xls`, and `.xlsx` files.
- Preview uploaded data in a table.
- Describe replacement tasks in natural language.
- Use OpenAI to generate a regex replacement plan.
- Apply replacements to one column, multiple columns, or all columns.
- Undo and redo replacement operations.
- Download the processed file.
- Preserve the original download format where possible:
  - CSV uploads download as CSV.
  - XLSX uploads download as XLSX.
  - XLS uploads download as XLSX.
- Handle invalid files, empty files, invalid regex, missing columns, and OpenAI errors.
- Store uploaded datasets temporarily and clean them after use.

## Live Demo

- Frontend: https://ai-regex-pattern-matching-and-repla.vercel.app
- Backend API: https://ai-regex-backend.onrender.com/api

## Demo Flow

1. Upload an Excel file.
2. Confirm that the data appears in the preview table.
3. Enter a natural language request:

```text
Replace Ethan with Siheng in the NAME and EMAIL columns.
```

4. Apply the replacement.
5. Confirm the updated data in the preview table.
6. Use Undo and Redo.
7. Download the processed file.

## Tech Stack

### Backend

- Django
- Django REST Framework
- pandas
- openpyxl
- xlrd
- OpenAI Python SDK
- SQLite

### Frontend

- React
- Vite
- Axios
- Tailwind CSS

## Application Workflow

1. The user uploads a CSV or Excel file.
2. The frontend sends the file to the Django backend.
3. The backend reads the file with pandas.
4. The full dataset is temporarily saved as JSON.
5. SQLite stores dataset metadata such as filename, row count, column count, upload time, and storage path.
6. The frontend displays a preview of the uploaded data.
7. The user enters a natural language instruction, for example:

```text
Replace Ethan with Siheng in the NAME and EMAIL columns.
```

8. The backend sends the instruction and available columns to OpenAI.
9. OpenAI returns a structured replacement plan, such as:

```json
{
  "columns": ["NAME", "EMAIL"],
  "regex": "Ethan",
  "replacement": "Siheng"
}
```

10. The backend applies the regex replacement using Python's `re` module.
11. The updated data is saved and returned as a new preview.
12. The user can undo, redo, or download the processed file.

## Project Structure

```text
AI-Regex-Pattern-Matching-and-Replacement/
  backend/
    config/
      settings.py
      urls.py
      asgi.py
      wsgi.py
    processor/
      llm.py
      models.py
      storage.py
      urls.py
      views.py
      migrations/
    manage.py
    requirements.txt
    .env.example

  frontend/
    src/
      App.jsx
      api.js
      main.jsx
      styles.css
    index.html
    package.json
    tailwind.config.js
    vite.config.js
```

## Local Setup and Running Instructions

### Prerequisites

Install:

- Python 3.11 or later
- Node.js 18 or later
- npm

You also need an OpenAI API key.

## Backend Setup

Open a terminal in the project root:

```powershell
cd backend
```

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```powershell
copy .env.example .env
```

Edit `backend/.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Run database migrations:

```powershell
python manage.py migrate
```

Start the backend server:

```powershell
python manage.py runserver 127.0.0.1:8000
```

The backend will run at:

```text
http://127.0.0.1:8000
```

## Frontend Setup

Open a second terminal in the project root:

```powershell
cd frontend
```

Install frontend dependencies:

```powershell
npm install
```

Start the Vite development server:

```powershell
npm run dev -- --host 127.0.0.1
```

Open the frontend in your browser:

```text
http://127.0.0.1:5173
```

## Environment Variables

### Backend

Required in `backend/.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
DJANGO_SECRET_KEY=replace-this-with-a-secure-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend

Optional for local development:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

If this is not set, the frontend uses:

```text
http://127.0.0.1:8000/api
```

## API Endpoints

### Upload File

```text
POST /api/upload/
```

Accepts a multipart file upload with form field name:

```text
file
```

Returns:

- `dataset_id`
- filename
- columns
- row count
- column count
- preview rows

### Natural Language Replacement

```text
POST /api/natural-language-replace/
```

Request body:

```json
{
  "dataset_id": "dataset-id",
  "natural_language": "Replace Ethan with Siheng in the NAME and EMAIL columns."
}
```

The backend calls OpenAI, generates a regex plan, applies the replacement, and returns the updated preview.

### Undo

```text
POST /api/datasets/<dataset_id>/undo/
```

Restores the previous dataset state.

### Redo

```text
POST /api/datasets/<dataset_id>/redo/
```

Reapplies the next dataset state after undo.

### Download Processed File

```text
GET /api/download/<dataset_id>/
```

Downloads the current processed dataset.

### Delete Dataset

```text
DELETE /api/datasets/<dataset_id>/
```

Deletes the temporary dataset JSON, history JSON, and SQLite metadata.

The frontend also uses:

```text
POST /api/datasets/<dataset_id>/
```

This is used with `navigator.sendBeacon` when the browser tab is closed.

## Data Storage Design

The project separates metadata from full dataset contents.

### SQLite

SQLite stores metadata only:

- dataset id
- original filename
- temporary storage path
- upload time
- last modified time
- row count
- column count

### Temporary JSON Files

The full uploaded dataset is stored temporarily as JSON:

```text
backend/data/datasets/<dataset_id>.json
```

Undo and redo history is stored as:

```text
backend/data/history/<dataset_id>.json
```

These files are ignored by Git.

## Temporary Data Cleanup

Temporary datasets are removed in three ways:

1. When the user uploads a new file in the same session.
2. When the browser tab or page is closed.
3. When the backend sees expired datasets during upload.

This keeps the local temporary storage from growing indefinitely.

## Error Handling

The backend handles:

- unsupported file formats
- empty files
- unreadable CSV or Excel files
- files with no rows
- files with no columns
- missing dataset ids
- missing columns
- invalid regex patterns
- missing OpenAI API key
- OpenAI API failures
- invalid or incomplete LLM output
- missing temporary dataset files

The frontend displays user-readable messages returned by the API.

## Notes and Comments

- The app currently previews the first 50 rows for performance.
- The full dataset is still processed and downloaded, not just the preview rows.
- If the user does not specify a column in the natural language request, the backend asks the LLM to apply the replacement to all columns.
- XLS uploads are downloaded as XLSX because `openpyxl` writes modern Excel files.
- Temporary local file storage is suitable for local development and demos. For production, use durable storage such as S3, Render Disk, or another persistent object store.
- The manual regex replacement API is still present for debugging, but the UI focuses on natural language replacement.
- `backend/.env`, `backend/data/`, `backend/db.sqlite3`, `frontend/node_modules/`, and `frontend/dist/` are intentionally ignored by Git.

## Deployment Notes

### Backend on Render

Set these environment variables in Render:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Suggested build command:

```text
pip install -r requirements.txt && python manage.py migrate
```

Suggested start command:

```text
gunicorn config.wsgi:application
```

If using the included `render.yaml`, Render should use `backend/` as the service root directory.

Set these Render environment variables after the backend URL is known:

```env
DJANGO_ALLOWED_HOSTS=your-render-service.onrender.com
CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
```

For the current deployment:

```env
DJANGO_ALLOWED_HOSTS=ai-regex-backend.onrender.com
CORS_ALLOWED_ORIGINS=https://ai-regex-pattern-matching-and-repla.vercel.app
```

### Frontend on Vercel

Set this environment variable in Vercel:

```env
VITE_API_BASE_URL=https://your-render-backend-url/api
```

For the current deployment:

```env
VITE_API_BASE_URL=https://ai-regex-backend.onrender.com/api
```

Build command:

```text
npm run build
```

Output directory:

```text
dist
```
