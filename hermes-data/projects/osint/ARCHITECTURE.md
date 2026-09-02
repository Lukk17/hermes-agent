# Architecture

## System Overview

```mermaid
flowchart TD
    subgraph User["User Input"]
        U[Chaotic input: URLs, IDs, names, links]
    end

    subgraph AI["AI Parser (this agent)"]
        P[Parse to structured Query]
    end

    subgraph Runner["osint runner"]
        subgraph Services["Parallel Services"]
            ES[email_service]
            PS[phone_service]
            PE[people_service]
            CS[company_service]
            DS[domain_service]
            BS[breach_service]
        end
        M[main.py orchestrator]
        A[ascend_client]
    end

    subgraph Sources["External Sources"]
        HIBP[HaveIBeenPwned]
        EPI[EPIEOS]
        HLDR[Holehe]
        PHINF[PhoneInfoga]
        MGR[Maigret / Sherlock]
        KRS[eKRS / CEIDG]
        CRT[crtsh]
        VT[VirusTotal]
        BLD[BuiltWith]
        BRC[BreachDirectory]
        SCR[Ascend Scrapper]
        WEB[Web Scraping]
        SH[Shodan]
        HT[Hunter.io]
        GH[GitHub API]
        LOC[Local Leak DBs]
    end

    subgraph Output["Output"]
        JSON[JSON Results]
        MD[Markdown Report]
    end

    U --> P
    P -->|Structured Query| M
    M -->|async dispatch| Services
    ES --> HIBP
    ES --> EPI
    ES --> HLDR
    PS --> PHINF
    PE --> MGR
    CS -->|via A| SCR
    CS --> WEB
    CS --> KRS
    DS -->|via A| SCR
    DS --> CRT
    DS --> VT
    DS --> BLD
    DS --> SH
    DS --> HT
    DS --> GH
    BS --> BRC
    BS --> LOC
    A --> SCR
    Services --> JSON
    JSON -->|AI renders| MD
```

## Query Flow

```mermaid
sequenceDiagram
    participant U as User
    participant AI as AI Parser
    participant CLI as main.py
    participant SVC as Services
    participant SRC as Sources

    U->>AI: "find info about Jan Kowalski, NIP 5252341234, jan@example.com"
    AI->>AI: Parse fields → Query model
    AI->>CLI: python3 src/main.py --input '{"name": "Jan Kowalski", "nip": "5252341234", "email": "jan@example.com"}'
    CLI->>SVC: Dispatch parallel queries
    SVC->>SRC: API calls, scraping
    SRC-->>SVC: Results
    SVC-->>CLI: Aggregated JSON
    CLI-->>AI: JSON results
    AI->>AI: Render markdown report
    AI-->>U: Markdown report
```

## Service Architecture

```mermaid
classDiagram
    class BaseService {
        +session: aiohttp.ClientSession
        +get(url, params) 
        +post(url, json)
        +get_text(url)
    }

    class EmailService {
        +check_hibp(email) 
        +check_epieos(email)
        +check_holehe(email)
    }

    class PhoneService {
        +check_phoneinfoga(phone)
    }

    class PeopleService {
        +search_sherlock(name)
        +search_maigret(name)
    }

    class CompanyService {
        +scrape_ceidg(nip)
        +scrape_ekrs(krs)
        +scrape_krs_online(nip)
    }

    class DomainService {
        +check_crt_sh(domain)
        +check_virustotal(domain)
        +check_builtwith(domain)
        +check_shodan(domain)
        +check_github_org(org)
    }

    class BreachService {
        +check_breachdirectory(email)
        +search_local_db(email)
    }

    BaseService <|-- EmailService
    BaseService <|-- PhoneService
    BaseService <|-- PeopleService
    BaseService <|-- CompanyService
    BaseService <|-- DomainService
    BaseService <|-- BreachService
```

## Input → Query Model

```mermaid
flowchart LR
    subgraph Inputs["Flexible User Input"]
        E[email]
        P[phone]
        N[name]
        L[location]
        NI[nip]
        KR[krs]
        CE[ceidg_url]
        LI[linkedin_url]
        D[domain]
        PL[plate]
        V[vin]
    end

    subgraph Parser["AI Parser"]
        PF[Parse fields]
        VF[Validate & fill]
    end

    subgraph Query["Query Model"]
        QM[Structured Query]
        QM --> email
        QM --> phone
        QM --> name
        QM --> location
        QM --> nip
        QM --> krs
        QM --> ceidg_url
        QM --> linkedin_url
        QM --> domain
        QM --> plate
        QM --> vin
    end

    E --> PF
    P --> PF
    N --> PF
    L --> PF
    NI --> PF
    KR --> PF
    CE --> PF
    LI --> PF
    D --> PF
    PL --> PF
    V --> PF
    PF --> VF
    VF --> QM
```

## Data Flow

```mermaid
flowchart TD
    subgraph Input_Query["Input Query"]
        Q[Query Model]
    end

    subgraph Parallel_Execution["Parallel Execution"]
        E1[email_service]
        E2[phone_service]
        E3[people_service]
        E4[company_service]
        E5[domain_service]
        E6[breach_service]
    end

    subgraph Result_Aggregation["Result Aggregation"]
        R[Raw Results Dict]
    end

    subgraph Output_Render["Output Rendering"]
        JSON[JSON]
        MD[Markdown Report]
    end

    Q --> E1
    Q --> E2
    Q --> E3
    Q --> E4
    Q --> E5
    Q --> E6
    E1 --> R
    E2 --> R
    E3 --> R
    E4 --> R
    E5 --> R
    E6 --> R
    R --> JSON
    R -->|AI render| MD
```

## Source Categories

```
┌─────────────────────────────────────────────────────────────┐
│                     SOURCE CATEGORIES                       │
├──────────────┬──────────────┬───────────────┬───────────────┤
│   Email      │   Phone      │   People      │   Company     │
│              │              │               │               │
│ HIBP         │ PhoneInfoga  │ Maigret       │ eKRS          │
│ EPIEOS       │ Truecaller   │ Sherlock      │ CEIDG         │
│ Holehe       │ NumVerify    │ Pipl          │ KRS-online    │
│ Hunter.io    │ OSINT Ind.   │ Spokeo        │ Rejestr.io    │
│ Clearbit     │              │ BeenVerified  │ e-Sąd         │
│ FullContact  │              │ Instant CM    │ iMSiG         │
├──────────────┼──────────────┼───────────────┼───────────────┤
│   Domain     │   Breach     │   Code        │   Geo         │
│              │              │               │               │
│ crt.sh       │ BreachDir.   │ GitHub        │ Google Maps   │
│ VirusTotal   │ LeakCheck    │ GitLab        │ Sentinel Hub  │
│ BuiltWith    │ DeHashed     │ DockerHub     │ Mapillary     │
│ Shodan       │ Snusbase     │ npm           │ Overpass TM   │
│ SecurityTr.  │ IntelX       │ PyPI          │ Wigle.net     │
│ Censys       │ GhostProject │ Bitbucket     │ FlightRadar   │
│ Hunter.io    │ Local DBs    │ Thingiverse   │ MarineTraffic │
├──────────────┴──────────────┴───────────────┴───────────────┤
│                     Polish Specific                         │
│                                                              │
│ eKRS, CEIDG, eKW, REGON, GUS, CEPiK, KRD, BIG, SUDOP, KIO,  │
│ e-Zamówienia, TERYT, NASK WHOIS, Biała Lista VAT           │
└─────────────────────────────────────────────────────────────┘
```

## CLI Interface

```mermaid
flowchart LR
    subgraph CLI["CLI Usage"]
        CMD1[python3 src/main.py --query "email@example.com"]
        CMD2[python3 src/main.py --query "5252341234" --type nip]
        CMD3[python3 src/main.py --query "Jan Kowalski" --type person --location Warsaw]
        CMD4[python3 src/main.py --query "https://linkedin.com/in/jankowski" --type linkedin]
        CMD5[python3 src/main.py --input '{"email": "x", "nip": "y"}']
    end
```

## Async Parallel Execution

```mermaid
flowchart TD
    subgraph Main["main.py"]
        Q[Query Input]
        S[Service Dispatcher]
    end

    subgraph Parallel["asyncio.gather"]
        T1[T1: email_service]
        T2[T2: phone_service]
        T3[T3: people_service]
        T4[T4: company_service]
        T5[T5: domain_service]
        T6[T6: breach_service]
    end

    subgraph Sources1["Email Sources"]
        H[HIBP]
        EP[EPIEOS]
        HL[Holehe]
    end

    subgraph Sources2["Phone Sources"]
        PI[PhoneInfoga]
        NU[NumVerify]
    end

    Q --> S
    S --> T1
    S --> T2
    S --> T3
    S --> T4
    S --> T5
    S --> T6
    T1 --> H
    T1 --> EP
    T1 --> HL
    T2 --> PI
    T2 --> NU
    T3 --> M[Maigret]
    T4 -->|ascend_client| SCR[Web Scrape]
    T5 --> CRT[crt.sh]
    T5 --> VT[VirusTotal]
    T5 --> SH[Shodan]
    T6 --> BD[BreachDirectory]
    T6 --> LOC[Local DB]
```
