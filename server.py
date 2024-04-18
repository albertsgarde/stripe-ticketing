import os
from typing import TypeGuard

import stripe
from fastapi import FastAPI, Request
from googleapiclient import discovery
from pydantic import BaseModel
from stripe.checkout import Session

app = FastAPI()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class PaymentLinkConfig(BaseModel):
    id: str
    name: str


class Config(BaseModel):
    payment_links: list[PaymentLinkConfig]
    spreadsheet_id: str


webhook_secret = os.environ.get("AFTERPARTY_WEBHOOK_SECRET")
if not webhook_secret:
    raise ValueError("Missing webhook secret")

config_str = os.environ.get("AFTERPARTY_CONFIG")
if not config_str:
    raise ValueError("Missing config env var `AFTERPARTY_CONFIG`")
config = Config.model_validate_json(config_str)
payment_links = config.payment_links
spreadsheet_id = config.spreadsheet_id

stripe_api_key = os.environ.get("AFTERPARTY_STRIPE_API_KEY")
if not stripe_api_key:
    raise ValueError("Missing Stripe API key")
stripe.api_key = stripe_api_key


def get_info(
    session: Session, payment_links: list[PaymentLinkConfig]
) -> list[str] | None:
    if (
        session.mode == "payment"
        and session.status == "complete"
        and session.customer_details
    ):
        payment_link_id = session.payment_link

        name = session.customer_details.name
        name = name if name else "NA"
        email = session.customer_details.email
        email = email if email else "NA"
        category: str = next(
            payment_link.name
            for payment_link in payment_links
            if payment_link.id == payment_link_id
        )
        return [name, email, category]
    else:
        return None


def get_payment_link_sessions(payment_link: PaymentLinkConfig) -> list[Session]:
    session_list = Session.list(payment_link=payment_link.id, limit=100)
    sessions = [session for session in session_list]
    while session_list.has_more:
        session_list = Session.list(
            payment_link=payment_link.id,
            limit=100,
            starting_after=session_list.data[-1].id,
        )
        sessions.extend(session_list.data)
    sessions = [
        session
        for session in sessions
        if session.mode == "payment"
        and session.status == "complete"
        and session.customer_details
    ]
    return sessions


def not_none(x: list[str] | None) -> TypeGuard[list[str]]:
    return x is not None


def get_guests(payment_links: list[PaymentLinkConfig]) -> list[list[str]]:
    sessions = [
        session
        for payment_link in payment_links
        for session in get_payment_link_sessions(payment_link)
    ]
    result = list(
        filter(
            not_none,
            (get_info(session, payment_links) for session in sessions),
        )
    )
    result.sort(key=lambda x: x[0])
    return result


def update_sheet(spreadsheet_id: str, range: str, values: list[list[str]]) -> None:
    service = discovery.build(
        "sheets",
        "v4",
    )
    sheet = service.spreadsheets()
    range = f"Ark1!{range}"
    sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range=range,
        body={
            "range": range,
            "values": values,
            "majorDimension": "ROWS",
        },
        valueInputOption="USER_ENTERED",
    ).execute()


@app.post("/new_guest")
async def new_guest(request: Request):
    payload = await request.body()
    signature_header = request.headers["stripe-signature"]
    event = stripe.Webhook.construct_event(payload, signature_header, webhook_secret)
    if event.type == "checkout.session.completed":
        guests = get_guests(payment_links)
        update_sheet(spreadsheet_id, "A2:Z", guests)
    return {"status": "ok"}
