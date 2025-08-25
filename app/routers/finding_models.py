"""Remaining Finding Model routes (will be further cleaned up)."""

# ruff: noqa: B008

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from app.vite_manifest import get_vite_asset_path

router = APIRouter()
templates = Jinja2Templates(directory="templates")
# Ensure shared template globals are set (e.g., vite asset helper used by base.html)
templates.env.globals["vite_asset"] = get_vite_asset_path
