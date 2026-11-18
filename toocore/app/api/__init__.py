from fastapi import APIRouter

from .acc import rouAcc
from .ai import rouAI
from .embedding import rouBI
from .injection import rouOcr
from .inv import invRou
from .t4 import rouT4
from .too import rouToo
from .wiki import rouWiki

rou = APIRouter()

rou.include_router(rouWiki, prefix="/wiki", tags=["wiki"])
rou.include_router(rouToo, prefix="/too", tags=["too"])
rou.include_router(rouOcr, prefix="/ocr", tags=["ocr"])

rou.include_router(rouAcc, prefix="/acc", tags=["acc"])
rou.include_router(rouAI,  prefix="/ai", tags=["ai"])

rou.include_router(invRou, prefix="/inv")
rou.include_router(rouT4, prefix="/t4", tags=["t4"])
rou.include_router(rouBI, prefix="/bi", tags=["bi"])
