import asyncio
import logging
from pysnmp.hlapi.asyncio import *

logger = logging.getLogger(__name__)

class AsyncSNMPClient:
    def __init__(self):
        pass

    async def get(self, target_ip, oid, port=161, community='public', version=2, v3_user=None, v3_auth=None, v3_priv=None):
        if version == 3 and v3_user:
            auth_proto = usmHMACMD5AuthProtocol if v3_auth else usmNoAuthProtocol
            priv_proto = usmDESPrivProtocol if v3_priv else usmNoPrivProtocol
            auth_data = UsmUserData(
                v3_user,
                v3_auth if v3_auth else None,
                v3_priv if v3_priv else None,
                authProtocol=auth_proto,
                privProtocol=priv_proto
            )
        else:
            # Version mapping: 1 -> 0 (v1), 2 -> 1 (v2c)
            mp_model = 1 if version == 2 else 0
            auth_data = CommunityData(community, mpModel=mp_model)
        
        errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
            SnmpEngine(),
            auth_data,
            await UdpTransportTarget.create((target_ip, port)),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        if errorIndication:
            return {"error": str(errorIndication)}
        elif errorStatus:
            return {"error": f"{errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"}
        else:
            result = []
            for varBind in varBinds:
                result.append(f"{varBind[0].prettyPrint()} = {varBind[1].prettyPrint()}")
            return {"result": result}

    async def walk(self, target_ip, oid, port=161, community='public', version=2, v3_user=None, v3_auth=None, v3_priv=None):
        if version == 3 and v3_user:
            auth_proto = usmHMACMD5AuthProtocol if v3_auth else usmNoAuthProtocol
            priv_proto = usmDESPrivProtocol if v3_priv else usmNoPrivProtocol
            auth_data = UsmUserData(
                v3_user,
                v3_auth if v3_auth else None,
                v3_priv if v3_priv else None,
                authProtocol=auth_proto,
                privProtocol=priv_proto
            )
        else:
            mp_model = 1 if version == 2 else 0
            auth_data = CommunityData(community, mpModel=mp_model)

        results = []

        async for errorIndication, errorStatus, errorIndex, varBinds in walk_cmd(
            SnmpEngine(),
            auth_data,
            await UdpTransportTarget.create((target_ip, port)),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False
        ):
            if errorIndication:
                return {"error": str(errorIndication)}
            elif errorStatus:
                return {"error": f"{errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"}
            else:
                for varBind in varBinds:
                    results.append(f"{varBind[0].prettyPrint()} = {varBind[1].prettyPrint()}")

        return {"result": results}
