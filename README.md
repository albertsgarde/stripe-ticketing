# Stripe ticketing system
## Local
Create `.env` file with contents:
```
AFTERPARTY_STRIPE_API_KEY=<your stripe api key>
AFTERPARTY_CONFIG={"spreadsheet_id": "<your spreadsheet ID>","payment_links": [{"id": "<first payment link ID>","name":"Standard ticket"},...]}
PORT=<any port you like>
```
The Stripe key only needs permission for the "Checkout Sessions" resource, so I would recommend to use one that only has that permission.
The `payment_links` array should contain all the payment links whose usage should be registered.
The `name` field is the name of the ticket type that will be displayed in the sheet.

Create a directory `credentials` with a file `key.json` which is the key for the GCP service account you wish to use.

Then run
```
docker build -t ticketing .
docker run --env-file .env -p 8000:<same port as before> -v <path to project dir>/credentials:/credentials --env GOOGLE_APPLICATION_CREDENTIALS=credentials/key.json ticketing
```
