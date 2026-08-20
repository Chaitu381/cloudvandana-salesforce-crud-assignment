import json
from urllib.parse import parse_qs

import httpx
import pytest

from app.services.salesforce import SalesforceApi


def describe_payload():
    names = [
        ("Id", "id", False, False),
        ("Name", "string", True, True),
        ("Type", "picklist", True, True),
        ("Industry", "picklist", True, True),
        ("Phone", "phone", True, True),
        ("Website", "url", True, True),
        ("BillingCity", "string", True, True),
        ("CreatedDate", "datetime", False, False),
    ]
    return {
        "label": "Account",
        "fields": [
            {
                "name": name,
                "label": name,
                "type": kind,
                "createable": create,
                "updateable": update,
                "nillable": name != "Name",
                "defaultedOnCreate": False,
                "calculated": False,
                "deprecatedAndHidden": False,
                "picklistValues": [],
                "referenceTo": [],
            }
            for name, kind, create, update in names
        ],
    }


@pytest.mark.asyncio
async def test_list_records_returns_exactly_twenty_with_cursor(settings, sf_session):
    def handler(request: httpx.Request):
        if request.url.path.endswith("/sobjects/Account/describe"):
            return httpx.Response(200, json=describe_payload())
        if request.url.path.endswith("/query"):
            records = [
                {"Id": f"001000000000{i:03d}AAA", "Name": f"A{i}", "Type": None, "Industry": None, "Phone": None, "Website": None, "CreatedDate": "2026-08-20T10:00:00.000+0000"}
                for i in range(21)
            ]
            return httpx.Response(200, json={"records": records})
        return httpx.Response(404)

    api = SalesforceApi(settings, sf_session, transport=httpx.MockTransport(handler))
    result = await api.list_records("Account", ["Name", "Type", "Industry", "Phone", "Website"])
    assert len(result["records"]) == 20
    assert result["hasMore"] is True
    assert result["nextCursor"]


@pytest.mark.asyncio
async def test_create_rejects_non_createable_field(settings, sf_session):
    def handler(request: httpx.Request):
        if request.url.path.endswith("/sobjects/Account/describe"):
            return httpx.Response(200, json=describe_payload())
        return httpx.Response(500)

    api = SalesforceApi(settings, sf_session, transport=httpx.MockTransport(handler))
    with pytest.raises(Exception):
        await api.create_record("Account", {"Id": "001000000000000AAA"})


@pytest.mark.asyncio
async def test_refresh_and_retry(settings, sf_session):
    calls = {"query": 0}

    def handler(request: httpx.Request):
        if request.url.path.endswith("/sobjects/Account/describe"):
            return httpx.Response(200, json=describe_payload())
        if request.url.path.endswith("/query"):
            calls["query"] += 1
            if calls["query"] == 1:
                return httpx.Response(401, json=[{"message": "expired", "errorCode": "INVALID_SESSION_ID"}])
            return httpx.Response(200, json={"records": []})
        if request.url.path.endswith("/services/oauth2/token"):
            return httpx.Response(200, json={"access_token": "new-access", "instance_url": sf_session.instance_url})
        return httpx.Response(404)

    api = SalesforceApi(settings, sf_session, transport=httpx.MockTransport(handler))
    await api.list_records("Account", ["Name", "Type", "Industry", "Phone", "Website"])
    assert api.refreshed is True
    assert api.session.access_token == "new-access"

@pytest.mark.asyncio
async def test_requires_five_to_ten_fields(settings, sf_session):
    def handler(request: httpx.Request):
        if request.url.path.endswith("/sobjects/Account/describe"):
            return httpx.Response(200, json=describe_payload())
        return httpx.Response(500)

    api = SalesforceApi(settings, sf_session, transport=httpx.MockTransport(handler))
    with pytest.raises(Exception):
        await api.list_records("Account", ["Name", "Phone", "Website", "Industry"])


@pytest.mark.asyncio
async def test_delete_validates_salesforce_id(settings, sf_session):
    api = SalesforceApi(settings, sf_session, transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    with pytest.raises(Exception):
        await api.delete_record("Account", "not-an-id")
