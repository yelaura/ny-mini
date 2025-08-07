# Volleyball Roster Viewer by Team (with Ethnicity Codes)

This app displays a volleyball team roster from a Google Sheet, including an "Ethnicity" code based on answers to a registration question.

## Ethnicity Codes
- `C` — 100% Chinese
- `Y` — At least 50% Chinese
- `P` — Other Asian descent

## Setup (Streamlit Cloud)
1. Upload this repo to GitHub.
2. Go to https://streamlit.io/cloud and deploy from your GitHub repo.
3. Add your service account JSON as a secret like this:

```
GCP_SERVICE_ACCOUNT = "<your service account JSON in one line>"
```

4. Share your Google Sheet (with team rosters) to the service account email (read-only).