from fastapi import APIRouter

from lan_ip import get_primary_lan_ipv4

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/lan-ipv4")
async def lan_ipv4():
    """IPv4 address of this host on the LAN (for building phone-friendly app URLs)."""
    return {"lan_ipv4": get_primary_lan_ipv4()}
