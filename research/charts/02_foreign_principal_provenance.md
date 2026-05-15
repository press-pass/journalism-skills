# Chart 2 — Provenance

Each cell is `COUNT(DISTINCT filing_uuid)` from a join of `senate_foreign_entity` × `senate_activity` filtered to top 12 countries × top 12 issues.

Reproducer: `python3 skills/lda-chart/scripts/chart_foreign_issues.py`

## Cell values

| country | Trade (domestic/foreign) | Energy/Nuclear | Taxation/Internal Revenue Code | Defense | Health Issues | Manufacturing | Budget/Appropriations | Environment/Superfund | Transportation | Science/Technology | Natural Resources | Foreign Relations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GB (United Kingdom) | 50 | 30 | 57 | 33 | 40 | 14 | 33 | 10 | 7 | 20 | 17 | 13 |
| CA (Canada) | 20 | 39 | 32 | 28 | 19 | 22 | 27 | 49 | 28 | 13 | 49 | 1 |
| NL (Netherlands) | 41 | 11 | 43 | 10 | 8 | 20 | 12 | 15 | 25 | 15 | 6 | 1 |
| JP (Japan) | 33 | 23 | 21 | 16 | 27 | 26 | 18 | 15 | 10 | 14 | 3 | 3 |
| DE (Germany) | 29 | 20 | 16 | 20 | 11 | 21 | 9 | 6 | 16 | 12 | 0 | 1 |
| CH (Switzerland) | 42 | 38 | 36 | 13 | 20 | 17 | 19 | 24 | 25 | 4 | 7 | 14 |
| KR (South Korea) | 60 | 40 | 24 | 15 | 6 | 28 | 5 | 6 | 3 | 18 | 5 | 5 |
| CN (China) | 44 | 13 | 9 | 11 | 6 | 15 | 4 | 0 | 7 | 13 | 3 | 2 |
| FR (France) | 25 | 25 | 24 | 16 | 15 | 10 | 14 | 15 | 8 | 3 | 6 | 5 |
| AU (Australia) | 10 | 21 | 5 | 25 | 9 | 6 | 11 | 2 | 3 | 4 | 28 | 3 |
| IL (Israel) | 4 | 4 | 4 | 28 | 12 | 5 | 16 | 3 | 10 | 9 | 4 | 4 |
| VG (Brit. Virgin Is.) | 15 | 6 | 3 | 4 | 2 | 4 | 2 | 0 | 3 | 10 | 5 | 2 |

## Spot checks (3 sample filings per high-traffic cell)


### South Korea × Trade (domestic/foreign) (cell = 60)
- `63da6510-1c24-4ce3-8c6e-64cd42643a2b` (2025) — client *HANWHA Q CELLS AMERICA INC.* — foreign entity *HANWHA CORPORATION*
- `63da6510-1c24-4ce3-8c6e-64cd42643a2b` (2025) — client *HANWHA Q CELLS AMERICA INC.* — foreign entity *HANWHA OCEAN*
- `63da6510-1c24-4ce3-8c6e-64cd42643a2b` (2025) — client *HANWHA Q CELLS AMERICA INC.* — foreign entity *HANWHA AEROSPACE*

### United Kingdom × Taxation/Internal Revenue Code (cell = 57)
- `d30aa281-3f6d-4d0d-82da-08c63fda672c` (2022) — client *RAI SERVICES COMPANY* — foreign entity *BRITISH AMERICAN TOBACCO P.L.C.*
- `d2e2b434-a0aa-454e-bd38-8c15bb377597` (2022) — client *FCA US LLC* — foreign entity *SFS UK 1 LIMITED*
- `ee84630e-fdca-4aec-9ccb-2b6cc0c4d0e4` (2023) — client *FCA US LLC* — foreign entity *FCA FOREIGN SALES HOLDCO LTD.*

### United Kingdom × Trade (domestic/foreign) (cell = 50)
- `ea189c1d-4911-4e4a-8d1a-626c7ba61dec` (2022) — client *TNC (US) HOLDINGS, INC. (FORMERLY NIELSEN)* — foreign entity *NIELSEN HOLDINGS PLC*
- `586fbced-d5ce-44df-842f-a7cc5d9bc42d` (2024) — client *RENK HOLDINGS, INC.* — foreign entity *HORSTMAN HOLDINGS, LTD.*
- `d188a60f-ea94-4d49-8637-661933eb58bf` (2024) — client *FCA US LLC* — foreign entity *FCA FOREIGN SALES HOLDCO LTD.*

### Canada × Environment/Superfund (cell = 49)
- `c11f2f69-43ec-479c-926d-cde940df0332` (2022) — client *GHGSAT INC.* — foreign entity *INVESTISSEMENT-QUEBEC*
- `92dfd29c-f1b5-4d4c-a3c2-2eefaf642933` (2022) — client *ORIGIN MATERIALS OPERATING, INC.* — foreign entity *ORIGIN MATERIALS CANADA HOLDING LIMITED*
- `92dfd29c-f1b5-4d4c-a3c2-2eefaf642933` (2022) — client *ORIGIN MATERIALS OPERATING, INC.* — foreign entity *ORIGIN MATERIALS CANADA PIONEER LIMITED*

### Canada × Natural Resources (cell = 49)
- `73aecf03-0c92-440e-923c-8b6221314e73` (2026) — client *U.S. GOLDMINING INC.* — foreign entity *GOLDMINING INC.*
- `38f19251-8428-43b1-81a1-70da802407f3` (2022) — client *WATEREUSE* — foreign entity *TAZA DEVELOPMENT CORP*
- `90686b78-ffc3-4f99-a5ca-6683607ebde6` (2025) — client *ACLARA TECHNOLOGIES INC.* — foreign entity *ACLARA RESOURCES INC.*

### China × Trade (domestic/foreign) (cell = 44)
- `94c50936-34e6-4f6f-b4fd-61fe518d8d08` (2023) — client *LIMITED LIABILITY COMPANY ARCTIC LNG 2* — foreign entity *CEPR LIMITED*
- `8061d143-bb77-4069-9be5-67336c3f1f76` (2024) — client *GOTION INC.* — foreign entity *GOTION HI TECH COMPANY LTD*
- `2a21aa8c-97f2-420d-bd7b-1e1ec96e6e27` (2024) — client *PIRELLI TIRE, LLC* — foreign entity *CHINA NATIONAL CHEMICAL CORPORATION LIMITED (THROUGH ITS 100% OWNERSHIP OF CHINA NATIONAL TIRE & RUBBER CORPORATION LTD.)*

### Netherlands × Taxation/Internal Revenue Code (cell = 43)
- `ac36e91a-c05f-4adc-a655-5b7e9b1b7616` (2024) — client *FCA US LLC* — foreign entity *STELLANTIS N.V.*
- `39df0803-b09a-4afc-ae41-503846a756c4` (2022) — client *FCA US LLC* — foreign entity *STELLANTIS N.V.*
- `9068dfda-94ea-4865-b89a-af0014b4ff51` (2023) — client *NACERO, INC.* — foreign entity *GLOBAL CLEANTECH CAPITAL*

### Switzerland × Trade (domestic/foreign) (cell = 42)
- `f6060d4d-ea7a-4af5-8a47-b79294182519` (2025) — client *ABB, INC.* — foreign entity *ABB ASEA BROWN BOVERI, LTD.*
- `b735190b-179d-4b7a-8e59-cca1c1d02e4c` (2025) — client *ABB, INC.* — foreign entity *ABB, LTD.*
- `a5cc2371-4945-452a-acf3-b6c2c8e020fe` (2025) — client *BARRY CALLEBAUT USA LLC* — foreign entity *BARRY CALLEBAUT AG*

### Netherlands × Trade (domestic/foreign) (cell = 41)
- `bce655df-5151-4f2f-884b-9d7fc333ccfb` (2026) — client *PNA HOLDINGS INC* — foreign entity *PON HOLDINGS BV*
- `39df0803-b09a-4afc-ae41-503846a756c4` (2022) — client *FCA US LLC* — foreign entity *STELLANTIS N.V.*
- `ac36e91a-c05f-4adc-a655-5b7e9b1b7616` (2024) — client *FCA US LLC* — foreign entity *STELLANTIS N.V.*

### United Kingdom × Health Issues (cell = 40)
- `dcac5c1c-c647-4baf-ae01-7782fa0579d1` (2026) — client *RECKITT BENCKISER LLC* — foreign entity *RECKITT PLC*
- `1eb9ef94-d72c-49cc-8f2b-6dbc3f68f5ad` (2022) — client *HIKMA PHARMACEUTICALS USA INC.* — foreign entity *HIKMA PHARMACEUTICALS PLC*
- `48bd0020-68fe-40d0-b282-5e482c2f9053` (2022) — client *CORNERSTONE GOVERNMENT AFFAIRS (ON BEHALF OF RUSP COALITION)* — foreign entity *ORCHARD THERAPEUTICS PLC (SHOWING OWNERSHIP PERCENTAGE IN ORCHARD THERAPEUTICS NORTH AMERICA, INC.)*
