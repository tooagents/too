from fastapi import APIRouter

from .too import rouToo
from .t4 import rouT4
from .inv import invRou
from .ai import rouAI
from .embedding import rouBI
from .acc import rouAcc
from .injection import rouOcr

rou = APIRouter()

rou.include_router(rouOcr, prefix="/ocr", tags=["ocr"])
rou.include_router(rouToo, prefix="/too", tags=["too"])

rou.include_router(rouAcc, prefix="/acc", tags=["acc"])
rou.include_router(rouAI,  prefix="/ai", tags=["ai"])

rou.include_router(invRou, prefix="/inv")
rou.include_router(rouT4, prefix="/t4", tags=["t4"])
rou.include_router(rouBI, prefix="/bi", tags=["bi"])
