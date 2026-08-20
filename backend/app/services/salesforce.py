from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import SalesforceSession, decode_cursor, encode_cursor


OBJECT_CONFIG: dict[str, dict[str, Any]] = {
    "Account": {
        "label": "Account",
        "default_fields": ["Name", "Type", "Industry", "Phone", "Website", "BillingCity"],
    },
    "Opportunity": {
        "label": "Opportunity",
        "default_fields": ["Name", "StageName", "Amount", "CloseDate", "Probability", "Type", "LeadSource"],
    },
    "Lead": {
        "label": "Lead",
        "default_fields": ["FirstName", "LastName", "Company", "Email", "Phone", "Status", "LeadSource"],
    },
    "Contact": {
        "label": "Contact",
        "default_fields": ["FirstName", "LastName", "Email", "Phone", "Title", "Department", "AccountId"],
    },
    "Case": {
        "label": "Case",
        "default_fields": ["CaseNumber", "Subject", "Status", "Priority", "Origin", "Type", "ContactEmail"],
    },
}

SUPPORTED_FIELD_TYPES = {
    "string", "textarea", "email", "phone", "url", "boolean", "date", "datetime", "currency",
    "double", "int", "percent", "picklist", "multipicklist", "reference", "id", "combobox",
}
SF_ID_RE = re.compile(r"^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$")
_DESCRIBE_CACHE: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
_DESCRIBE_TTL_SECONDS = 300


class SalesforceApiError(Exception):
    def __init__(self, status_code: int, message: str, code: str | None = None, fields: list[str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.fields = fields or []


class SalesforceApi:
    def __init__(self, settings: Settings, session: SalesforceSession, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.session = session
        self.refreshed = False
        self._transport = transport

    @property
    def base_api_url(self) -> str:
        return f"{self.session.instance_url}/services/data/{self.settings.sf_api_version}"

    async def _refresh_access_token(self) -> None:
        if not self.session.refresh_token:
            raise SalesforceApiError(401, "Salesforce session expired. Please sign in again.", "INVALID_SESSION_ID")

        data = {
            "grant_type": "refresh_token",
            "client_id": self.settings.sf_client_id,
            "refresh_token": self.session.refresh_token,
        }
        if self.settings.sf_client_secret:
            data["client_secret"] = self.settings.sf_client_secret

        async with httpx.AsyncClient(timeout=self.settings.api_timeout_seconds, transport=self._transport) as client:
            response = await client.post(self.settings.oauth_token_url, data=data)
        if response.status_code >= 400:
            raise SalesforceApiError(401, "Salesforce session expired. Please sign in again.", "INVALID_SESSION_ID")

        payload = response.json()
        self.session.access_token = payload["access_token"]
        self.session.instance_url = payload.get("instance_url", self.session.instance_url).rstrip("/")
        if payload.get("refresh_token"):
            self.session.refresh_token = payload["refresh_token"]
        self.refreshed = True

    @staticmethod
    def _error_from_response(response: httpx.Response) -> SalesforceApiError:
        message = f"Salesforce request failed ({response.status_code})"
        code = None
        fields: list[str] = []
        try:
            payload = response.json()
            item = payload[0] if isinstance(payload, list) and payload else payload
            if isinstance(item, dict):
                message = item.get("message", message)
                code = item.get("errorCode") or item.get("error")
                fields = item.get("fields") or []
                if not message and item.get("error_description"):
                    message = item["error_description"]
        except ValueError:
            pass
        mapped = 401 if response.status_code == 401 else 400 if response.status_code in {400, 404} else 403 if response.status_code == 403 else 502
        return SalesforceApiError(mapped, message, code, fields)

    def _request_url(self, path: str) -> str:
        return path if path.startswith("https://") else f"{self.base_api_url}{path}"

    async def request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self.session.access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=self.settings.api_timeout_seconds, transport=self._transport) as client:
            response = await client.request(method, self._request_url(path), headers=headers, params=params, json=json)
        if response.status_code == 401 and self.session.refresh_token:
            await self._refresh_access_token()
            headers["Authorization"] = f"Bearer {self.session.access_token}"
            async with httpx.AsyncClient(timeout=self.settings.api_timeout_seconds, transport=self._transport) as client:
                response = await client.request(method, self._request_url(path), headers=headers, params=params, json=json)
        if response.status_code >= 400:
            raise self._error_from_response(response)
        return response

    @staticmethod
    def ensure_object(object_name: str) -> None:
        if object_name not in OBJECT_CONFIG:
            raise HTTPException(status_code=404, detail="Unsupported Salesforce object")

    async def describe(self, object_name: str) -> dict[str, Any]:
        self.ensure_object(object_name)
        user_key = self.session.user_id or hashlib.sha256(self.session.access_token.encode("utf-8")).hexdigest()[:16]
        cache_key = (self.session.instance_url, user_key, object_name)
        cached = _DESCRIBE_CACHE.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        response = await self.request("GET", f"/sobjects/{object_name}/describe")
        raw = response.json()
        fields: list[dict[str, Any]] = []
        for field in raw.get("fields", []):
            ftype = field.get("type")
            if ftype not in SUPPORTED_FIELD_TYPES or field.get("deprecatedAndHidden"):
                continue
            fields.append({
                "name": field.get("name"),
                "label": field.get("label") or field.get("name"),
                "type": ftype,
                "createable": bool(field.get("createable")),
                "updateable": bool(field.get("updateable")),
                "nillable": bool(field.get("nillable")),
                "defaultedOnCreate": bool(field.get("defaultedOnCreate")),
                "calculated": bool(field.get("calculated")),
                "length": field.get("length"),
                "precision": field.get("precision"),
                "scale": field.get("scale"),
                "referenceTo": field.get("referenceTo") or [],
                "picklistValues": [
                    {"label": p.get("label"), "value": p.get("value")}
                    for p in field.get("picklistValues", []) if p.get("active")
                ],
            })

        available = {f["name"] for f in fields}
        defaults = [name for name in OBJECT_CONFIG[object_name]["default_fields"] if name in available]
        if len(defaults) < 5:
            for field in fields:
                if field["name"] not in defaults and field["name"] not in {"Id", "CreatedDate"}:
                    defaults.append(field["name"])
                if len(defaults) >= 5:
                    break
        defaults = defaults[:10]

        result = {
            "name": object_name,
            "label": raw.get("label") or OBJECT_CONFIG[object_name]["label"],
            "fields": fields,
            "defaultFields": defaults,
        }
        _DESCRIBE_CACHE[cache_key] = (time.monotonic() + _DESCRIBE_TTL_SECONDS, result)
        return result

    async def _field_map(self, object_name: str) -> dict[str, dict[str, Any]]:
        desc = await self.describe(object_name)
        return {field["name"]: field for field in desc["fields"]}

    async def validate_selected_fields(self, object_name: str, fields: list[str]) -> list[str]:
        self.ensure_object(object_name)
        clean = list(dict.fromkeys([f.strip() for f in fields if f.strip()]))
        if not 5 <= len(clean) <= 10:
            raise HTTPException(status_code=400, detail="Select between 5 and 10 fields")
        fmap = await self._field_map(object_name)
        invalid = [name for name in clean if name not in fmap]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unavailable field(s): {', '.join(invalid)}")
        return clean

    @staticmethod
    def _fields_hash(fields: list[str]) -> str:
        return hashlib.sha256(",".join(fields).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _soql_datetime(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Pagination cursor contains an invalid date") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed = parsed.astimezone(timezone.utc)
        return parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    async def list_records(self, object_name: str, fields: list[str], cursor: str | None = None) -> dict[str, Any]:
        selected = await self.validate_selected_fields(object_name, fields)
        query_fields = list(dict.fromkeys(["Id", *selected, "CreatedDate"]))
        where = ""
        if cursor:
            payload = decode_cursor(self.settings, cursor)
            if payload.get("object") != object_name or payload.get("fieldsHash") != self._fields_hash(selected):
                raise HTTPException(status_code=400, detail="Pagination cursor does not match the current object/fields")
            created = payload.get("createdDate")
            record_id = payload.get("id")
            if not created or not record_id or not SF_ID_RE.match(record_id):
                raise HTTPException(status_code=400, detail="Pagination cursor is malformed")
            # createdDate comes only from our encrypted cursor and is emitted by Salesforce.
            created_literal = self._soql_datetime(str(created))
            where = f" WHERE (CreatedDate < {created_literal} OR (CreatedDate = {created_literal} AND Id < '{record_id}'))"

        soql = f"SELECT {', '.join(query_fields)} FROM {object_name}{where} ORDER BY CreatedDate DESC, Id DESC LIMIT 21"
        response = await self.request("GET", "/query", params={"q": soql})
        items = response.json().get("records", [])
        has_more = len(items) > 20
        page = items[:20]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(self.settings, {
                "object": object_name,
                "fieldsHash": self._fields_hash(selected),
                "createdDate": self._soql_datetime(str(last.get("CreatedDate"))),
                "id": last.get("Id"),
            })

        records = []
        for item in page:
            records.append({"Id": item.get("Id"), **{field: item.get(field) for field in selected}})
        return {"records": records, "nextCursor": next_cursor, "hasMore": has_more}

    @staticmethod
    def validate_record_id(record_id: str) -> None:
        if not SF_ID_RE.match(record_id):
            raise HTTPException(status_code=400, detail="Invalid Salesforce record ID")

    async def get_record(self, object_name: str, record_id: str, fields: list[str]) -> dict[str, Any]:
        self.ensure_object(object_name)
        self.validate_record_id(record_id)
        selected = await self.validate_selected_fields(object_name, fields)
        query_fields = list(dict.fromkeys(["Id", *selected]))
        soql = f"SELECT {', '.join(query_fields)} FROM {object_name} WHERE Id = '{record_id}' LIMIT 1"
        response = await self.request("GET", "/query", params={"q": soql})
        records = response.json().get("records", [])
        if not records:
            raise HTTPException(status_code=404, detail="Record not found")
        item = records[0]
        return {"Id": item.get("Id"), **{field: item.get(field) for field in selected}}

    async def _validate_payload(self, object_name: str, payload: dict[str, Any], mode: str) -> dict[str, Any]:
        fmap = await self._field_map(object_name)
        permission = "createable" if mode == "create" else "updateable"
        bad = [name for name in payload if name not in fmap or not fmap[name].get(permission)]
        if bad:
            raise HTTPException(status_code=400, detail=f"Field(s) cannot be {mode}d: {', '.join(bad)}")
        return payload

    async def create_record(self, object_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_object(object_name)
        clean = await self._validate_payload(object_name, payload, "create")
        response = await self.request("POST", f"/sobjects/{object_name}", json=clean)
        data = response.json()
        return {"id": data.get("id"), "success": bool(data.get("success", True))}

    async def update_record(self, object_name: str, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_object(object_name)
        self.validate_record_id(record_id)
        clean = await self._validate_payload(object_name, payload, "update")
        await self.request("PATCH", f"/sobjects/{object_name}/{record_id}", json=clean)
        return {"id": record_id, "success": True}

    async def delete_record(self, object_name: str, record_id: str) -> dict[str, Any]:
        self.ensure_object(object_name)
        self.validate_record_id(record_id)
        await self.request("DELETE", f"/sobjects/{object_name}/{record_id}")
        return {"id": record_id, "success": True}


def raise_http_for_salesforce(error: SalesforceApiError) -> None:
    detail: dict[str, Any] = {"message": error.message}
    if error.code:
        detail["code"] = error.code
    if error.fields:
        detail["fields"] = error.fields
    raise HTTPException(status_code=error.status_code, detail=detail)
