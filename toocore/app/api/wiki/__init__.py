from fastapi import APIRouter

from .wiki_endpoint import wikiRou

rouWiki = APIRouter()


rouWiki.include_router(wikiRou, prefix="/wiki", tags=["wiki"])
