# Flask Gmail Backend

This Flask service reads unread Gmail messages using IMAP, generates a placeholder AI reply, sends it using SMTP over SSL, skips self-sent emails, and marks processed messages as read.

## Environment Variables

- `EMAIL_USER`: Gmail address
- `EMAIL_PASS`: Gmail App Password

## Run

```bash
pip install -r requirements.txt
python app.py
```

## Endpoints

- `GET /health`
- `POST /process-unread-emails`
