from fastapi import APIRouter

from .wiki_endpoint import wikiRou

rouAI = APIRouter()


rouAI.include_router(wikiRou, prefix="/wiki", tags=["ai-wiki"])
