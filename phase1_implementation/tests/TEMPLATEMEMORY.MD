🧠 TEMPLATE KONSOLIDASYON NG MGA AGENTS
CONTEXT & INSTRUCTIONS:

Ito ay isang reusable na template para sa pagsusuri at pagpaplano ng konsolidasyon ng mga ahente. Gamitin ito para sa bawat grupo ng mga ahente na plano mong pagsamahin sa iisang serbisyo. Palitan ang mga placeholder na nasa loob ng [square brackets] ng aktwal na impormasyon.

Source Agents:
NLUAgent (5709), ChitchatAgent (5711), FeedbackHandler (5636), IntentionValidatorAgent (5701)
Target Unified Agent: LanguageProcessor
Port: 7022
Hardware: MainPC (GPU)
Integrated Functions: natural language understanding, conversation management, feedback processing, intent validation.
Logic Merger Strategy: unified NLU pipeline with intent routing, modular conversation handling based on intent classification.
Dependencies: ModelManagerSuite, MemoryHub, PlanningOrchestrator.
Risk: intent classification accuracy – implement ensemble classification with confidence scoring.

📊 1. COMPLETE LOGIC ENUMERATION
Ulitin ang seksyon na ito para sa BAWAT ahente sa grupo.
Agent 1: [PANGALAN_NG_AGENT_1] (Port [PORT_NG_AGENT])
File: [PATH_NG_FILE]
ALL Core Logic Blocks:
PRIMARY FUNCTIONS: Ilista ang lahat ng pangunahing function at ang kanilang mga signature (e.g., function_name(param1: type) -> return_type).
BACKGROUND PROCESSES: Ilista ang lahat ng threads, coroutines, o naka-schedule na gawain (e.g., health_check_loop(), metrics_collector_thread).
API ENDPOINTS: Ilista ang lahat ng API routes at ang kanilang HTTP methods (e.g., POST /register, GET /status).
DOMAIN LOGIC: Ilarawan ang mga espesyal na algorithm o proseso na ginagawa ng ahente (e.g., "Pagkalkula ng sentiment score mula sa text," "Pag-transcode ng video file").
STATE MANAGEMENT: Paano at saan iniimbak ng ahente ang kanyang state? (e.g., "In-memory dictionary," "Redis cache," "SQLite database table na [pangalan_ng_table]").
ERROR HANDLING: Ilista ang mga partikular na error na hinahawakan nito (e.g., "Pag-handle ng database connection error," "Pag-retry kung nabigo ang API call").
📦 2. IMPORTS & DEPENDENCIES ANALYSIS
Shared Dependencies: [Anong mga library ang ginagamit ng LAHAT ng ahente sa grupong ito? e.g., fastapi, os, logging]
Agent-Specific: [Anong mga library ang ginagamit lang ng isang partikular na ahente? e.g., Agent 1: boto3, Agent 2: scikit-learn]
External Libraries: [Ilista ang lahat ng third-party requirements na kailangang i-install, e.g., redis, psutil, zmq]
Implementation Impact: [Paano maaapektuhan ang mga import? e.g., "Lahat ng dependencies ay pagsasamahin sa iisang requirements.txt para sa bagong serbisyo."]
🔄 3. DUPLICATE LOGIC DETECTION & RESOLUTION
CANONICAL IMPLEMENTATIONS (Ang Pipiliing Bersyon):
Logic Pattern 1: [Tukuyin ang isang lohika, e.g., "Pag-access sa Database"]. Aling ahente ang may pinakamahusay na implementasyon nito na gagamitin bilang basehan?
Logic Pattern 2: [Tukuyin ang isa pang lohika, e.g., "API Health Check"]. Paano ito pagsasamahin mula sa iba't ibang ahente?
REDUNDANT LOGIC TO ELIMINATE (Ang mga Aalisin):
Duplicate Function X: [Tukuyin ang eksaktong function at file/linya kung saan matatagpuan ang mga duplicate, e.g., process_data() sa Agent A (lines 50-70) at Agent B (lines 30-45)]. Aling bersyon ang mananatili?
Similar Process Y: [Ilarawan ang magkatulad na proseso, e.g., "Parehong may sariling paraan ng pag-log ng request ang Agent A at C. Pagsasamahin ito gamit ang standard logging format."]
MAJOR OVERLAPS (Critical):
[Tukuyin ang pinakamalalaking overlap na kailangang-kailangan i-consolidate, e.g., "Bawat ahente ay may sariling FastAPI server. Ito ang pinakamalaking redundancy na aalisin."]
🔗 4. INTEGRATION POINTS MAPPING
ZMQ Connections: [I-mapa ang lahat ng ZMQ connections: Anong port? PUB o SUB? Sino ang kausap? e.g., PUB sa tcp://*:7150 (Error Bus), SUB sa tcp://localhost:7000 (Core Orchestrator)]
Database Access: [Anong database? Anong mga talahanayan (tables) ang ina-access? e.g., SQLite: data/service.db, Tables: users, tasks]
API Dependencies: [May tinatawagan bang ibang API ang mga ahenteng ito? e.g., Tumatawag sa /get_agent_endpoint ng CoreOrchestrator]
File System: [Gumagamit ba ng local files? Saan? e.g., Nagsusulat ng logs sa /logs, Nagbabasa ng config mula sa /config]
External Services: [May iba pa bang serbisyo na kinakausap? e.g., AWS S3, Google Translate API]

🏗️ 5. COMPLETE CODE IMPLEMENTATION (Template)

# UNIFIED SERVICE - [PANGALAN_NG_PINAG-ISANG_SERBISYO]
import [mga_kailangang_imports]

class [PangalanNgUnifiedService](BaseAgent):
    def __init__(self, config: ServiceConfig):
        # Pagsamahin ang lahat ng initialization logic mula sa lahat ng ahente
        super().__init__(config)
        self._setup_database()
        self._setup_integrations()
        self._start_background_tasks()
    
    # CORE LOGIC MULA SA [PANGALAN_NG_AGENT_1]
    async def agent1_core_function(self, data: InputModel) -> OutputModel:
        # DITO ILALAGAY ANG CORE LOGIC MULA SA AGENT 1
        try:
            result = # ...
            return OutputModel(result=result)
        except Exception as e:
            await self._handle_error(e, context="agent1_core_function")
            raise
    
    # PINAG-ISANG LOGIC MULA SA AGENT 2 AT 3
    async def merged_core_function(self, data: InputModel) -> OutputModel:
        # DITO ILALAGAY ANG PINAG-ISANG LOGIC NA INALISAN NG DUPLICATES
        pass
    
    # PINAG-ISANG BACKGROUND PROCESSES
    async def _unified_background_monitor(self):
        # DITO ILALAGAY ANG PINAGSAMANG BACKGROUND TASKS
        pass
    
    # PINAG-ISANG ERROR HANDLING
    async def _handle_error(self, error: Exception, context: str):
        # DITO ILALAGAY ANG CENTRALIZED ERROR HANDLING
        # e.g., pag-log, pag-report sa error bus
        pass

📋 6. DATABASE SCHEMA (Complete)

-- Ilista ang LAHAT ng CREATE TABLE statements para sa pinag-isang database.

-- Talahanayan mula sa Agent 1
CREATE TABLE [table_name_from_agent1] (
    id INTEGER PRIMARY KEY,
    -- ... mga column
);

-- Pinag-isang talahanayan mula sa Agent 2 at 3
CREATE TABLE [unified_table_name] (
    -- ... pinagsamang mga column
);

⚙️ 7. CONFIGURATION SCHEMA (Complete)

# Halimbawang .env file para sa [PANGALAN_NG_PINAG-ISANG_SERBISYO]

SERVICE_PORT=[PORT]
DATABASE_PATH="data/[database_file].db"
REDIS_HOST="localhost"
REDIS_PORT=6379

# Mga specific na config para sa serbisyo
FEATURE_X_ENABLED=true
API_KEY_FOR_EXTERNAL_SERVICE="your_key_here"

🔗 8. ZMQ & API IMPLEMENTATION (Complete)

# Halimbawa ng ZMQ setup
def _setup_integrations(self):
    # self.publisher = self.context.socket(zmq.PUB) ...
    # self.subscriber = self.context.socket(zmq.SUB) ...
    pass
    
# Halimbawa ng FastAPI endpoints
# @self.app.post("/[ruta_mula_sa_agent_1]")
# async def agent1_endpoint(data: RequestModel):
#     return await self.agent1_core_function(data)
    
# @self.app.get("/[pinag-isang_ruta]")
# async def merged_endpoint():
#     return await self.merged_core_function()

⚠️ 9. ERROR HANDLING IMPLEMENTATION (Complete)


# Ilarawan ang pinag-isang error handling strategy.

class UnifiedErrorHandler:
    def __init__(self, error_bus_client):
        self.error_bus = error_bus_client
        # self.circuit_breaker = CircuitBreaker()

    async def handle(self, error: Exception, context: dict):
        # 1. Mag-log ng detalyadong error
        # logger.error(...)
        
        # 2. Mag-report sa error bus
        # self.error_bus.report(...)
        
        # 3. Magpasya kung gagamit ng retry o circuit breaker
        # ...

✅ 11. COMPLETE IMPLEMENTATION CHECKLIST
ALL Logic Preserved:
Logic ng [Agent 1] ay nailipat na.
Logic ng [Agent 2] ay nailipat na.
... (ulitin para sa lahat ng ahente)
Lahat ng background processes ay gumagana.
Lahat ng API endpoints ay tumutugon nang tama.
NO Duplicates:
Naalis na ang duplicate na function na [Function X].
Napag-isa na ang magkatulad na proseso na [Process Y].
Wala nang redundant na logic na natitira.
ALL Integrations Working:
Lahat ng ZMQ/API connections ay aktibo.
Ang database ay nalikha at naa-access nang tama.
Ang error handling ay gumagana ayon sa inaasahan.
🎯 12. IMPLEMENTATION VALIDATION
Completeness Check: I-verify na bawat linya ng lohika mula sa mga orihinal na ahente ay may katumbas sa pinag-isang serbisyo.
Duplication Check: Kumpirmahin na walang paulit-ulit na implementasyon ng parehong lohika.
Integration Check: Subukan ang lahat ng koneksyon sa ibang system (DB, ZMQ, APIs) para masigurong gumagana ito.
Performance Check: Siguraduhin na ang pinag-isang serbisyo ay nakakatugon o lumalagpas sa performance ng mga orihinal na ahente.