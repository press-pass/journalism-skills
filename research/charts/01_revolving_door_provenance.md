# Chart 1 — Provenance

**Claim:** For each Member listed, the bar height equals the number of distinct people (first+last) appearing in the Senate-LDA `senate_lobbyist` table during 2024–2026 Q1 whose `covered_position` text resolves to that Member via the rules in `skills/lda-revolving-door/scripts/extract_members.py`.

**Reproducer:** `python3 skills/lda-revolving-door/scripts/extract_members.py && python3 skills/lda-chart/scripts/chart_revolving_door.py`

## Numbers in the chart

| Rank | Member | Bioguide | Active lobbyists | Distinct clients | Filings |
|---|---|---|---:|---:|---:|
| 1 | John Cornyn | C001056 | 20 | 345 | 1085 |
| 2 | Patty Murray | M001111 | 20 | 148 | 724 |
| 3 | Bill Cassidy | C001075 | 17 | 159 | 746 |
| 4 | David Vitter | V000127 | 17 | 107 | 258 |
| 5 | Susan Collins | C001035 | 17 | 101 | 254 |
| 6 | Mitch Mcconnell | M000355 | 17 | 94 | 320 |
| 7 | Kay Granger | G000377 | 16 | 134 | 573 |
| 8 | Thad Cochran | C000567 | 15 | 238 | 990 |
| 9 | John Boehner | B000589 | 15 | 184 | 674 |
| 10 | Ted Cruz | C001098 | 15 | 152 | 302 |
| 11 | Kay Hutchison | H001016 | 15 | 116 | 362 |
| 12 | Roger Wicker | W000437 | 15 | 106 | 229 |
| 13 | Dianne Feinstein | F000062 | 15 | 89 | 225 |
| 14 | Richard Shelby | S000320 | 14 | 224 | 720 |
| 15 | Ron Wyden | W000779 | 14 | 177 | 623 |
| 16 | Tim Scott | S001184 | 14 | 174 | 736 |
| 17 | Harry Reid | R000146 | 14 | 151 | 562 |
| 18 | Joni Ernst | E000295 | 14 | 119 | 249 |
| 19 | Lisa Murkowski | M001153 | 14 | 108 | 442 |
| 20 | Robert Portman | P000449 | 14 | 72 | 220 |

## Spot-check filings (top 5 members, 3 filings each)


### C001056
- `5782ce7c-a2de-45f7-9087-55b73bbd0ab4` (2026) — **LAURA KEMPER** for *NEUSPERA MEDICAL* — covered_position: "Counsel, Sen. John Cornyn; Deputy Assistant Secretary for Legislation, U.S. Department of Health and Human Services; Counselor to the Secretary, U.S. Department"
- `a34842bd-8424-4c77-9ddc-54e4498b398b` (2026) — **LAURA KEMPER** for *SKY MARKETING CORPORATION* — covered_position: "Counsel, Sen. John Cornyn; Deputy Assistant Secretary for Legislation, U.S. Department of Health and Human Services; Counselor to the Secretary, U.S. Department"
- `7933a23f-b78e-4d9d-b5e2-6c32244e8b77` (2026) — **MADISON SMITH** for *EVOLUTION METALS & MINING TECHNOLOGIES* — covered_position: "Majority Staff Director, Senate Finance Subcommittee on International Trade, Customs, and Global Competitiveness; Legislative Assistant, Senator John Cornyn; Se"

### M001111
- `66beb3af-fa6d-486c-9486-c37dd61a3324` (2026) — **PAGE PHILLIPS STRICKLER** for *COWLITZ PUBLIC UTILITY DISTRICT* — covered_position: "SW Washington Director for Sen. Patty Murray"
- `bb80e632-d444-42ce-93f9-e1c802e99321` (2026) — **KENDRA ISAACSON** for *EQUITABLE* — covered_position: "Pensions Policy Director and Senior Tax Counsel, Sen. Patty Murray"
- `4b790d2b-c9a2-47c0-958a-a1218587d1f0` (2026) — **KENDRA ISAACSON** for *INVESTMENT ADVISER ASSOCIATION (IAA)* — covered_position: "Pensions Policy Director and Senior Tax Counsel, Sen. Patty Murray"

### C001075
- `b6f5f85f-4876-472f-ba1c-944c3ecefcc0` (2026) — **ROBERT BUTORA** for *RIVER REGION PSYCHIATRY ASSOCIATES* — covered_position: "Health Policy Advisor, Senator Bill Cassidy; Senior Health Policy Advisor, Representative Leonard Lance, Health Legislative Assistant, Representative Michael Bu"
- `7e2820a4-30cb-4c35-8c67-eb5c9ac19753` (2026) — **CURTIS PHILIP** for *RECORDING INDUSTRY ASSOCIATION OF AMERICA* — covered_position: "Deputy Chief of Staff, Rep. Lamar Smith/Professional Staff member, House Science Cmte; Legislative Director, Rep. Louie Gohmert; Legislative Counsel, Rep. Bill "
- `6b6b217c-51f9-4f07-bf10-5a1575c1d269` (2026) — **ALEC DERISP** for *AMERICA'S ESSENTIAL HOSPITALS* — covered_position: "Senior Legislative Assistant, Congressman Troy Balderson; Healthcare and Oversight Counsel, Committee on Aging; Health Policy Fellow, Senator Bill Cassidy"

### V000127
- `4d38d146-485b-4076-a4dc-6c7fc880d4ca` (2026) — **TRAVIS JOHNSON** for *CYCLOPS DEFENSE* — covered_position: "Deputy Chief of Staff, Senator David Vitter; Staff Director, Senate Banking Subcommittee on Economic Policy; Legislative Director, Rep John Shadegg; Sr. Legisla"
- `69b8861f-1c10-4825-acf0-ee440299ba58` (2026) — **EDGAR ABRAMS** for *TIKTOK USDS JOINT VENTURE LLC* — covered_position: "Chief of Staff to US Senator Dean Heller; Chief of Staff to US Congressman Dean Heller; Communications Director to US Senator David Vitter; Communications Direc"
- `823a5b55-21cf-4773-954b-33194f18f024` (2026) — **JOHN STEITZ** for *DRAX BIOMASS INC.* — covered_position: "Dep. Chief of Staff, Legislative Director, Senior LA, Sen. John Kennedy; Senior PSM and PSM, Sen. Small Business Committee; LA and LC, Sen. David Vitter."

### C001035
- `d0b0be23-a259-4d49-935a-a8edbbbfb909` (2026) — **MICHAEL DIROMA** for *ETHOSENERGY* — covered_position: "Deputy Assistant Secretary of the Treasury for Legislative Affairs (International Affairs); Tax Counsel, Senator Susan M. Collins"
- `91d475f4-bc6a-4e89-ae32-b2a844521880` (2026) — **MICHAELA CAMPBELL** for *CONGRESSIONAL FIRE SERVICES INSTITUTE* — covered_position: "Legislative Correspondent, Sen. Susan Collins"
- `b3dc498d-a9d5-417c-a7ee-d6533a249906` (2026) — **ROWAN BOST** for *RENCO MANUFACTURING* — covered_position: "Legislative Aide, Office of Senator Susan Collins; Legislative Correspondent, Office of Senator Susan Collins; Intern, Office of Senator Susan Collins; Senate P"
