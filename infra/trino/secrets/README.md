# Trino connector secrets

Place Google service-account JSON key files here for the Google Sheets
(`gsheets`) connector.

This directory is mounted read-only into the Trino container at
`/etc/trino/secrets`. When adding a Google Sheets data source, set the
credentials path to the in-container path, for example:

```
/etc/trino/secrets/my-service-account.json
```

## Getting a key file

1. Enable the Google Sheets API for a Google Cloud project.
2. Create a service account and download its key in JSON format.
3. Copy that JSON file into this directory.
4. Share your metadata sheet and any data sheets with the service
   account's email address (found inside the JSON as `client_email`).

Key files (`*.json`) are git-ignored so credentials are never committed.
