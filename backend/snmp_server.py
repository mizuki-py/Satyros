import asyncio
import logging
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv
from core.config import SNMP_TRAP_PORT
from pysnmp.smi import builder, view, compiler, rfc1902

logger = logging.getLogger(__name__)

class AsyncSNMPServer:
    def __init__(self, host='0.0.0.0', port=SNMP_TRAP_PORT, callback=None):
        self.host = host
        self.port = port
        self.callback = callback
        self.snmpEngine = None
        
        self.mibBuilder = builder.MibBuilder()
        try:
            compiler.add_mib_compiler(self.mibBuilder)
            self.mibBuilder.load_modules('SNMPv2-MIB')
        except Exception as e:
            logger.warning(f"Failed to load MIBs: {e}")
        self.mibViewController = view.MibViewController(self.mibBuilder)

    def _trap_callback(self, snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
        # Callback for when a trap is received
        resolved_varbinds = []
        for name, val in varBinds:
            try:
                varBind = rfc1902.ObjectType(rfc1902.ObjectIdentity(name), val).resolve_with_mib(self.mibViewController)
                resolved_varbinds.append(f'{varBind[0].prettyPrint()} = {varBind[1].prettyPrint()}')
            except Exception:
                resolved_varbinds.append(f'{name.prettyPrint()} = {val.prettyPrint()}')
                
        msg = ", ".join(resolved_varbinds).replace('\r', '').replace('\n', ' ')
        
        source_ip = "Unknown IP"
        try:
            transportDomain, transportAddress = snmpEngine.message_dispatcher.get_transport_info(stateReference)
            source_ip = transportAddress[0]
        except Exception:
            try:
                # Fallback for older pysnmp
                transportDomain, transportAddress = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)
                source_ip = transportAddress[0]
            except Exception:
                pass
        
        if self.callback:
            self.callback(source_ip, msg)
        else:
            logger.info(f"Trap Received from {source_ip}: {msg}")

    async def start(self, v3_user=None, v3_auth=None, v3_priv=None, community=None):
        try:
            if self.snmpEngine:
                self.snmpEngine.transportDispatcher.closeDispatcher()
            self.snmpEngine = engine.SnmpEngine()
            
            config.addTransport(
                self.snmpEngine,
                udp.domainName,
                udp.UdpTransport().openServerMode((self.host, self.port))
            )
            
            # Allow SNMPv1 / v2c traps with specified community
            if community:
                config.addV1System(self.snmpEngine, 'my-area', community)

            # Optional SNMPv3 Configuration
            if v3_user:
                auth_proto = config.usmHMACMD5AuthProtocol if v3_auth else config.usmNoAuthProtocol
                priv_proto = config.usmDESPrivProtocol if v3_priv else config.usmNoPrivProtocol
                
                config.addV3User(
                    self.snmpEngine,
                    v3_user,
                    auth_proto,
                    v3_auth if v3_auth else None,
                    priv_proto,
                    v3_priv if v3_priv else None
                )

            # Register trap callback
            ntfrcv.NotificationReceiver(self.snmpEngine, self._trap_callback)

            # pysnmp v5+ ties into the current asyncio loop automatically when we openServerMode with asyncio transport
            # We just need to keep the loop running.
            logger.info(f"SNMP Trap server started at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start SNMP server: {e}")
            raise

    async def stop(self):
        # We need to unregister transport
        try:
            self.snmpEngine.transportDispatcher.closeDispatcher()
            logger.info("SNMP Trap server stopped")
        except Exception as e:
            pass
