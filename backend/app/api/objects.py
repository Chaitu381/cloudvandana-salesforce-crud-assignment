from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.security import get_session_from_request, set_session_cookie
from app.services.salesforce import OBJECT_CONFIG, SalesforceApi, SalesforceApiError, raise_http_for_salesforce

router = APIRouter(prefix="/api/objects", tags=["salesforce"])


class RecordPayload(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


def get_api(request: Request, settings: Settings) -> SalesforceApi:
    session = get_session_from_request(request, settings)
    return SalesforceApi(settings, session)


def persist_refresh(response: Response, api: SalesforceApi, settings: Settings) -> None:
    if api.refreshed:
        set_session_cookie(response, settings, api.session)


@router.get("")
async def list_objects():
    return [{"name": name, "label": config["label"]} for name, config in OBJECT_CONFIG.items()]


@router.get("/{object_name}/metadata")
async def metadata(object_name: str, request: Request, response: Response, settings: Settings = Depends(get_settings)):
    api = get_api(request, settings)
    try:
        result = await api.describe(object_name)
        persist_refresh(response, api, settings)
        return result
    except SalesforceApiError as exc:
        raise_http_for_salesforce(exc)


@router.get("/{object_name}/records")
async def records(
    object_name: str,
    request: Request,
    response: Response,
    fields: str,
    cursor: str | None = None,
    settings: Settings = Depends(get_settings),
):
    api = get_api(request, settings)
    try:
        result = await api.list_records(object_name, fields.split(","), cursor)
        persist_refresh(response, api, settings)
        return result
    except SalesforceApiError as exc:
        raise_http_for_salesforce(exc)


@router.get("/{object_name}/records/{record_id}")
async def record_detail(
    object_name: str,
    record_id: str,
    request: Request,
    response: Response,
    fields: str,
    settings: Settings = Depends(get_settings),
):
    api = get_api(request, settings)
    try:
        result = await api.get_record(object_name, record_id, fields.split(","))
        persist_refresh(response, api, settings)
        return result
    except SalesforceApiError as exc:
        raise_http_for_salesforce(exc)


@router.post("/{object_name}/records", status_code=201)
async def create_record(
    object_name: str,
    payload: RecordPayload,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
):
    api = get_api(request, settings)
    try:
        result = await api.create_record(object_name, payload.values)
        persist_refresh(response, api, settings)
        return result
    except SalesforceApiError as exc:
        raise_http_for_salesforce(exc)


@router.patch("/{object_name}/records/{record_id}")
async def update_record(
    object_name: str,
    record_id: str,
    payload: RecordPayload,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
):
    api = get_api(request, settings)
    try:
        result = await api.update_record(object_name, record_id, payload.values)
        persist_refresh(response, api, settings)
        return result
    except SalesforceApiError as exc:
        raise_http_for_salesforce(exc)


@router.delete("/{object_name}/records/{record_id}")
async def delete_record(
    object_name: str,
    record_id: str,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
):
    api = get_api(request, settings)
    try:
        result = await api.delete_record(object_name, record_id)
        persist_refresh(response, api, settings)
        return result
    except SalesforceApiError as exc:
        raise_http_for_salesforce(exc)
