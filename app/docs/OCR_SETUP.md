# LUMA Google Vision OCR Setup

## Required Files

Place the Google Cloud service account key here:

```text
secrets/google-vision-key.json
```

Do not commit this file. The `secrets/` folder is ignored by Git.

## Environment

Set this in `.env`:

```env
GOOGLE_APPLICATION_CREDENTIALS=./secrets/google-vision-key.json
```

## Install

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

Open:

```text
http://localhost:5000/ocr
```

## Health Check

```powershell
curl.exe "http://localhost:5000/ocr/health"
```

Expected response:

```json
{
  "success": true,
  "engine": "google_vision",
  "credentials_path": "./secrets/google-vision-key.json",
  "credentials_exists": true
}
```

## OCR Test

```powershell
curl.exe -X POST "http://localhost:5000/ocr" -F "file=@test.jpg"
```

Python smoke tests:

```powershell
python scripts\test_google_vision_ocr.py
python scripts\test_ocr_http.py
```

The response uses this shape:

```json
{
  "success": true,
  "engine": "google_vision",
  "filename": "test.jpg",
  "text": "extracted text",
  "text_length": 123
}
```

## Common Errors

`Could not automatically determine credentials`

Check that `.env` is loaded and `GOOGLE_APPLICATION_CREDENTIALS` points to `./secrets/google-vision-key.json`.

`File not found`

Check that the key exists at the project root under `secrets/google-vision-key.json`.

`403 Permission denied`

Enable Cloud Vision API in Google Cloud Console and grant the service account Vision permissions.

`400 form-data file field is required`

Send the image as multipart form-data with the field name `file`.
