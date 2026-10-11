# vaaniAI – Speech Sound Screening (Hindi / English)

A web app for screening children's speech sounds in Hindi, English, or mixed Hindi–English word lists, based on the literature review gap: Hindi and Hinglish resources are scarce and clinicians are in short supply.

A parent or clinician adds a child, the child says a list of words into the microphone, and the app stores each recording, checks its quality, and produces an overview. The overview can come from automatic phoneme comparison or from the adult marking each word correct or incorrect.

## Stack

| Layer | Technology | Where |
|---|---|---|
| Frontend | React (Vite), MediaRecorder | `frontend/` |
| Backend | Flask, SQLAlchemy (Python) | `backend/` |
| Database | MySQL on Amazon RDS (SQLite for local dev) | `DATABASE_URL` |
| Cloud | AWS EC2, S3 (recordings), CloudWatch (logs) | `S3_BUCKET`, `CLOUDWATCH_LOG_GROUP` |
| Security / DevOps | JWT, bcrypt, GitHub Actions | `.github/workflows/ci.yml` |

## Run locally

```bash
# 1. Backend (Python 3.10+)
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python wsgi.py                      # http://localhost:5000

# 2. Frontend (Node 18+), in a second terminal
cd frontend
npm install
npm run dev                         # http://localhost:5173  (proxies /api to Flask)
```

Open http://localhost:5173, create an account, add a child, start a screening. Browsers only allow microphone access on `localhost` or HTTPS.

For a single-process setup, run `npm run build` in `frontend/` and open http://localhost:5000: Flask serves the built app.

Tests: `cd backend && python -m pytest`

## How the pieces connect

- The React app calls `/api/...`. In development Vite proxies this to Flask; in production Flask serves both.
- Sign-in returns a JWT (`Authorization: Bearer ...`). Passwords are hashed with bcrypt. Every child, assessment and recording is checked against the signed-in user.
- `MediaRecorder` captures audio; `src/recorder.js` converts it to 16 kHz mono WAV in the browser (small uploads, no server codecs needed) and uploads it to `POST /api/assessments/<id>/recordings`.
- The backend checks quality (silent, too short, clipped), stores the WAV in S3 (or `audio_store/` locally), and saves a row in the database.

## Plain HTML/CSS/JS login page

`login-page/` (`login.html`, `login.css`, `login.js`) is the same sign-in / create-account page without React. Flask serves it at http://localhost:5000/login/. It calls the same `/api/auth/login` and `/api/auth/register` endpoints, stores the token under the same key, and redirects to the main app at `/`, so either login page works with the rest of the app.

## Analyzer modes

- `ANALYZER=quality` (default): signal checks only. Pronunciation is judged by the adult listening and tapping Correct / Not quite on the results page.
- `ANALYZER=wav2vec2`: loads `facebook/wav2vec2-lv-60-espeak-cv-ft`, recognises phonemes, aligns them against the target word's expected phonemes (`backend/app/words.py`) and lists substitutions, omissions and additions. Install `torch` and `transformers` first. **This path is not covered by the automated tests and has not been validated on Hindi-English child speech**, so check its output against a clinician's judgement before relying on it. The review's own conclusion is that no model trained on Hindi-English code-switched child speech exists yet; fine-tuning one is the natural next step.

## Deploy to AWS

1. RDS: create a MySQL instance, create database `ssd`, put the URL in `DATABASE_URL`.
2. S3: create a private bucket; give the EC2 instance role `s3:PutObject/GetObject/DeleteObject` on it and `logs:CreateLogStream/PutLogEvents/CreateLogGroup` for CloudWatch.
3. EC2: clone to `/opt/ssd-screener`, create the venv, copy `backend/.env.example` to `backend/.env` and fill it in, install `deploy/ssd.service`, and put nginx with HTTPS (needed for the microphone) in front of `127.0.0.1:8000`.
4. GitHub Actions: add secrets `EC2_HOST` and `EC2_SSH_KEY`. Pushes to `main` run tests, build the frontend and deploy over SSH. (The deploy job has not been run against a real server.)

## Before real-world use

- The word list and expected phonemes are a starting point and need review by a speech-language pathologist, including Hindi targets such as dental vs retroflex stops and aspirated consonants.
- This is a screening aid, not a diagnosis. The app says so, and the risk bands (85% / 60%) are placeholders to be set from clinical data.
- Recordings are children's voices. Get guardian consent, keep the S3 bucket private, and follow India's DPDP Act requirements for children's data.
- Add Flask-Migrate before changing the schema, and rate limiting on the login endpoint.
