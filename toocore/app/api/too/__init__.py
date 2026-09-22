from fastapi import APIRouter

from .too_proxy import agentRou
from .too_mcp_callback import mcpRou
from .too1_new_user_provision import newUserRou
from .too2_me import meRou
from .too3_be import beRou
from .too4_client import clientRou
from .too5_note import noteRou
from .too_test import testRou

rouToo = APIRouter()

rouToo.include_router(agentRou)
rouToo.include_router(mcpRou)
rouToo.include_router(newUserRou)
rouToo.include_router(meRou)
rouToo.include_router(beRou)
rouToo.include_router(clientRou)
rouToo.include_router(noteRou)
rouToo.include_router(testRou)
