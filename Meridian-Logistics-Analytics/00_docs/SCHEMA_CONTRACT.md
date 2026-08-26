# Meridian Global Logistics — Schema Contract v1.0

**Status: FROZEN.** Every downstream artefact (generator, KPI dictionary, DAX library, TMDL model,
SQL track, curriculum modules) must conform to this document exactly. Any change requires a new
revision and a note in `00_docs/ADR/`.

Company fiction: **Meridian Global Logistics (MGL)** — an ocean carrier with an inland transport
arm, contract warehousing, and an air & LCL forwarding desk. Fictional; SCAC `MGLU`.

---

## 0. Conventions

| Rule | Detail |
|---|---|
| Surrogate keys | `int32`, column name `<Table>Key` without the `Dim` prefix, e.g. `CustomerKey`. Values `1..N`. |
| Unknown member | Every dimension has key `-1`, code `#NA`, name `Unknown`. Facts use `-1` rather than null for FKs. |
| Business keys | Retained on the dimension as `<Thing>Code` or `<Thing>No` (text). Never used as a relationship key. |
| Date keys in facts | `int32` in `yyyymmdd` form, column suffix `DateKey`. Time-of-day, where needed, is a separate `datetime64[ns]` column suffixed `Ts` (UTC). |
| Money | Two columns per amount: `<x>_doc` (document currency) and `<x>_usd` (converted at the transaction-date rate). Facts carrying money also carry `CurrencyKey`. |
| Weight / volume | `weight_kg` (`float32`), `volume_cbm` (`float32`), `chargeable_weight_kg` (`float32`). |
| Booleans | `int8`, values `0`/`1`, prefix `is_`. Never text. |
| Text casing | Dimension attributes are clean Title Case **except** where a landmine is specified. |
| Row order | Facts are written sorted by their primary date key ascending. |
| File layout | `02_data/raw/<TableName>/` — facts Hive-partitioned `year=YYYY/month=MM/part-000.parquet`; dimensions a single `part-000.parquet` plus a mirror CSV in `02_data/reference/`. |
| Compression | Parquet, snappy. |
| Seed | `SEED = 20260824`, `rng = np.random.default_rng(SEED)`. One master RNG, spawned per table via `rng.spawn()` so tables are independently reproducible. |
| Calendar | 2023-01-01 → 2026-08-31 inclusive for all transactional facts. `DimDate` extends to 2026-12-31. |

### Scale dial

| `scale` | FactContainerMove | Total fact rows | Use |
|---|---|---|---|
| `dev` | 260,000 | ~1.00 M | daily drills, fast refresh |
| `prod` | 1,420,000 | ~5.48 M | **default** — the portfolio dataset |
| `stress` | 6,500,000 | ~25.1 M | Week 5 performance work |

All other fact volumes scale proportionally from the `prod` figures below.

---

## 1. Dimensions (19)

### 1.1 `DimDate` — 1,461 rows (2023-01-01 → 2026-12-31)

`DateKey`(int32 yyyymmdd, PK) · `Date`(date) · `Year`(int16) · `Quarter`(int8) · `QuarterName`("Q1") ·
`Month`(int8) · `MonthName` · `MonthShort` · `MonthYear`("Aug 2026") · `MonthYearSort`(int32 yyyymm) ·
`Day`(int8) · `DayName` · `DayShort` · `DayOfWeek`(int8, Mon=1) · `DayOfYear`(int16) ·
`ISOWeek`(int8) · `ISOYear`(int16) · `ISOWeekLabel`("2026-W34") · `ISOWeekSort`(int32) ·
`FiscalYear`(int16, FY starts 1 Oct) · `FiscalQuarter`(int8) · `FiscalMonth`(int8) · `FiscalYearLabel`("FY26") ·
`IsWeekend`(int8) · `IsMonthEnd`(int8) · `IsQuarterEnd`(int8) ·
`YearOffset`(int16, 0 = current year rel. 2026-08-31) · `MonthOffset`(int16) · `WeekOffset`(int16) · `DayOffset`(int32) ·
`IsCurrentYear`(int8) · `IsCurrentMonth`(int8) · `IsLunarNewYearWindow`(int8) · `IsPeakSeason`(int8, Aug–Oct)

Mark as date table on `Date`. Sort columns: `MonthName`→`Month`, `MonthYear`→`MonthYearSort`, `DayName`→`DayOfWeek`, `ISOWeekLabel`→`ISOWeekSort`.

### 1.2 `DimTime` — 1,440 rows (minute grain)

`TimeKey`(int32, `HHMM` as int) · `Time`(time) · `Hour`(int8) · `Minute`(int8) · `Hour12Label`("11 PM") ·
`ShiftName`(A 06:00–14:00 / B 14:00–22:00 / C 22:00–06:00) · `ShiftKey`(int8) · `IsNightShift`(int8) ·
`HalfHourBucket`("14:30") · `PortWorkingWindow`(int8, 1 if 06:00–22:00)

### 1.3 `DimLocation` — 420 rows

`LocationKey`(PK) · `LocationCode`(UN/LOCODE, 5 char, e.g. `INNSA`) · `LocationName` ·
`LocationType`(Seaport | Inland Depot | CFS | Airport | Warehouse | Rail Terminal) ·
`CountryCode`(ISO-2) · `CountryName` · `Region`(South Asia | East Asia | SE Asia | N Europe | Mediterranean | N America West | N America East | Middle East | LatAm East | LatAm West | Oceania | Africa) ·
`TradeRegion`(Asia | Europe | Americas | MEA | Oceania) · `SubRegion` ·
`Latitude`(float32) · `Longitude`(float32) · `TimezoneOffset`(float32) ·
`IsGateway`(int8) · `IsTranshipmentHub`(int8) · `AnnualTeuCapacityM`(float32) ·
`BerthCount`(int16) · `CraneCount`(int16) · `IataCode`(3 char, airports only, else `#NA`) ·
`IsBondedFacility`(int8) · `CustomsRegime`(Free Trade Zone | Bonded | Domestic | #NA)

Must include real UN/LOCODEs for at least: INNSA, INMAA, INMUN, INCOK, INPAV, CNSHA, CNNGB, CNYTN, CNTAO, HKHKG, SGSIN, MYPKG, MYTPP, VNSGN, THLCH, IDJKT, KRPUS, JPYOK, JPUKB, TWKHH, NLRTM, DEHAM, BEANR, GBFXT, GBLGP, FRLEH, ESVLC, ESALG, ITGOA, GRPIR, TRAMB, EGPSD, EGSUZ, AEJEA, AEKLF, SAJED, OMSLL, USLAX, USLGB, USOAK, USSEA, USNYC, USSAV, USHOU, USCHS, CAVAN, CAMTR, MXZLO, PABLB, BRSSZ, BRRIG, CLSAI, PECLL, ZADUR, MAPTM, AUSYD, AUMEL, NZAKL.

### 1.4 `DimCustomer` — 3,200 current members, 4,180 rows with SCD2 history

`CustomerKey`(PK, surrogate — one per version) · `CustomerCode`(`CUS0001`, durable business key) ·
`CustomerName` · `CustomerSegment`(BCO | NVOCC | Freight Forwarder | 3PL | SME Direct) ·
`IndustryVertical`(Retail | Automotive | Chemicals | Electronics | FMCG | Pharma | Agriculture | Machinery | Textiles | Metals | Energy) ·
`SizeTier`(Global Key Account | National | Mid-Market | SME) ·
`ParentCustomerCode` · `ParentCustomerName` ·
`HqCountryCode` · `HqCountryName` · `HqRegion` · `SalesRegion` ·
`AccountManager` · `AccountManagerEmail` ·
`CreditTier`(A | B | C | D) · `PaymentTermsDays`(int16, 0/15/30/45/60) ·
`ContractType`(Long-Term Contract | Named Account Tariff | Spot) ·
`OnboardedDate`(date) ·
`ScdValidFrom`(date) · `ScdValidTo`(date, `9999-12-31` for current) · `IsCurrent`(int8) · `ScdVersion`(int8)

SCD2 triggers: `AccountManager`, `CreditTier`, `SizeTier`, `ContractType`. ~30% of customers get 1–2 changes over the period.

### 1.5 `DimCarrier` — 180 rows

`CarrierKey`(PK) · `CarrierCode`(SCAC-style 4 char) · `CarrierName` ·
`CarrierType`(Ocean Carrier | Road Haulier | Rail Operator | Airline | Barge Operator | Drayage) ·
`IsOwnFleet`(int8, 1 for Meridian's own) · `HomeCountryCode` · `HomeCountryName` ·
`AllianceName`(Meridian Own | Alliance North | Alliance Pacific | Independent | #NA) ·
`ContractRateBasis`(Fixed | Index-Linked | Spot) · `PreferredTier`(Tier 1 | Tier 2 | Tier 3) ·
`OnTimeTargetPct`(float32) · `IsActive`(int8)

### 1.6 `DimVessel` — 240 rows

`VesselKey`(PK) · `ImoNumber`(7-digit, valid check digit) · `VesselName` · `CallSign` ·
`VesselClass`(Feeder | Feedermax | Handysize | Panamax | Post-Panamax | Neo-Panamax | ULCV) ·
`NominalTeuCapacity`(int32, 1,100–23,900) · `ReeferPlugCount`(int16) ·
`FlagCountryCode` · `FlagCountryName` · `YearBuilt`(int16) · `DeadweightTonnes`(int32) ·
`LoaMetres`(float32) · `BeamMetres`(float32) · `MaxDraughtMetres`(float32) ·
`ServiceSpeedKnots`(float32) · `FuelType`(VLSFO | LNG Dual-Fuel | Methanol Dual-Fuel | MGO) ·
`HasScrubber`(int8) · `EexiRating`(A–E) · `IsOwnedTonnage`(int8) · `OperatorCarrierCode`

### 1.7 `DimVoyage` — 6,800 rows

`VoyageKey`(PK) · `VoyageNo`(`2025W34E-MG12`) · `VesselKey`(FK) · `ServiceKey`(FK) ·
`Direction`(Headhaul | Backhaul) · `Leg`(Eastbound | Westbound | Northbound | Southbound) ·
`VoyageStartDateKey`(int32) · `VoyageEndDateKey`(int32) · `PortCallCount`(int8) ·
`RotationString`(e.g. `CNSHA-CNNGB-SGSIN-INNSA-AEJEA`) ·
`AllocatedTeuCapacity`(int32) · `IsBlankSailing`(int8) · `VoyageStatus`(Completed | In Progress | Planned | Cancelled)

### 1.8 `DimService` — 44 rows

`ServiceKey`(PK) · `ServiceCode`(`AE7`, `TP9`) · `ServiceName` ·
`TradeLane`(Asia–N Europe | Asia–Mediterranean | Transpacific East | Transpacific West | Asia–ISC | ISC–Europe | Intra-Asia | Asia–MEA | Europe–LatAm | Asia–LatAm | Transatlantic) ·
`OriginRegion` · `DestinationRegion` · `LoopDurationDays`(int16) · `VesselsDeployed`(int8) ·
`ServiceFrequency`(Weekly | Fortnightly) · `NominalTransitDays`(int16) · `IsAllianceService`(int8) · `IsActive`(int8)

### 1.9 `DimEquipment` — 60 rows

`EquipmentKey`(PK) · `IsoSizeTypeCode`(`22G1`, `45G1`, `45R1`, `L5G1`, `22T1`, `22U1`) ·
`EquipmentTypeCode`(20DV | 40DV | 40HC | 45HC | 20RF | 40RH | 20TK | 40OT | 40FR | 20FR) ·
`EquipmentTypeName` · `LengthFt`(int8) · `HeightFt`(text `8'6"`/`9'6"`) ·
`TeuFactor`(float32: 1.0 / 2.0 / 2.25) · `FfeFactor`(float32: 0.5 / 1.0 / 1.125) ·
`MaxPayloadKg`(int32) · `TareWeightKg`(int32) · `InternalCbm`(float32) ·
`IsReefer`(int8) · `IsTank`(int8) · `IsOpenTop`(int8) · `IsFlatRack`(int8) · `IsSpecialEquipment`(int8) ·
`OwnershipType`(Owned | Leased Long-Term | Leased Short-Term | Shipper-Owned) ·
`FreeDaysDemurrage`(int8: dry 5, reefer 3, special 4) · `FreeDaysDetention`(int8: dry 5, reefer 3, special 4) ·
`DailyDemurrageTier1Usd`/`Tier2`/`Tier3`(float32) · `DailyDetentionTier1Usd`/`Tier2`/`Tier3`(float32)

Tier bands: dry — tier 1 days 1–5 past free time, tier 2 days 6–10, tier 3 day 11+. Reefer — 1–3, 4–8, 9+.

### 1.10 `DimCommodity` — 900 rows

`CommodityKey`(PK) · `HsCode6`(6-digit) · `HsCode4` · `HsCode2` ·
`HsChapterName` · `HsHeadingName` · `CommodityName` ·
`CommodityGroup`(Consumer Goods | Industrial | Raw Materials | Perishable | Chemical | Automotive | Project Cargo) ·
`IsDangerousGoods`(int8) · `ImdgClass`(1–9 or `#NA`) · `UnNumber`(`UN1234` or `#NA`) ·
`IsTemperatureControlled`(int8) · `RequiredTempC`(float32, nullable) ·
`IsHighValue`(int8) · `AvgDensityKgPerCbm`(float32) · `TypicalStuffFactorTeu`(float32)

### 1.11 `DimIncoterm` — 12 rows (11 + Unknown)

`IncotermKey`(PK) · `IncotermCode`(EXW FCA FAS FOB CFR CIF CPT CIP DAP DPU DDP) · `IncotermName` ·
`IncotermGroup`(E | F | C | D) · `ModeApplicability`(Any Mode | Sea and Inland Waterway) ·
`SellerRiskEndsAt` · `WhoPaysMainCarriage`(Buyer | Seller) · `WhoInsures`(Buyer | Seller | Not Required) ·
`IsSeaOnly`(int8) · `SortOrder`(int8)

### 1.12 `DimChargeType` — 48 rows

`ChargeTypeKey`(PK) · `ChargeCode`(`OFR`,`BAF`,`THC`,`DEM`,`DET`,`CGS`,`DOC`,`ISPS`,`VGM`,`LSS`,`PSS`,`CAF`,`EBS`,`WRS`,`AMS`,`ENS`,`CFS`,`DRY`,`RAI`,`WHS`,`PIC`,`AIR`,`FSC`,`SSC`,`CUS`,`INS`, …) ·
`ChargeName` · `ChargeCategory`(Base Freight | Fuel Surcharge | Terminal | Detention & Demurrage | Documentation | Security | Inland | Warehousing | Customs | Insurance | Equipment | Other) ·
`RevenueOrCost`(Revenue | Cost | Both) · `IsAccessorial`(int8) · `IsPassThrough`(int8) ·
`IsSurcharge`(int8) · `IsDemurrageOrDetention`(int8) · `ChargeBasis`(Per Container | Per B/L | Per TEU | Per KG | Per CBM | Per Day | Per Shipment | Flat) ·
`AppliesToMode`(Ocean | Air | Road | Rail | Warehouse | All) · `IsCreditNoteEligible`(int8) · `SortOrder`(int16)

### 1.13 `DimMilestone` — 42 rows (DCSA-aligned)

`MilestoneKey`(PK) · `EventCode`(GTIN GTOT LOAD DISC STUF STRP PICK DROP INSP CUSR RSEA AVPU AVDO WAYP ARRI DEPA RAIO RAII CONF ISSU SURR APPR REJE …) ·
`EventName` · `EventJourney`(Equipment | Transport | Shipment) ·
`EventClassifier`(Planned | Actual | Estimated) · `MilestoneSequence`(int8, 1–20) ·
`MilestoneGroup`(Origin | Main Carriage | Transhipment | Destination | Documentation) ·
`IsCustomerVisible`(int8) · `IsSlaMilestone`(int8) · `EdifactMessageType`(IFTSTA | CODECO | COPARN | IFTMIN | IFTMBF | BAPLIE | #NA)

### 1.14 `DimMode` — 8 rows

`ModeKey`(PK) · `ModeCode`(FCL LCL AIR ROA RAI BAR MMD `#NA`) · `ModeName` ·
`ModeGroup`(Ocean | Air | Land | Multimodal) · `IsConsolidated`(int8) ·
`ChargeableWeightRule`(Ocean 1:1000 | Air 1:6000 | Air 1:5000 | Actual Weight | #NA) ·
`TypicalTransitDaysBand` · `Co2GramsPerTonneKm`(float32) · `SortOrder`(int8)

### 1.15 `DimWarehouse` — 26 rows

`WarehouseKey`(PK) · `WarehouseCode`(`WH-INNSA-01`) · `WarehouseName` · `LocationKey`(FK) ·
`WarehouseType`(Distribution Centre | Bonded Warehouse | CFS | Cross-Dock | Cold Store | Hazmat Store) ·
`GrossAreaSqm`(int32) · `StorageAreaSqm`(int32) · `PalletPositions`(int32) · `RackingType` ·
`DockDoorCount`(int16) · `HasTemperatureZones`(int8) · `TempZoneCount`(int8) ·
`ShiftPattern`(2-Shift | 3-Shift | Day Only) · `WmsSystem`(MERIDIAN-WMS | Client WMS | Legacy) ·
`IsAutomated`(int8) · `CommissionedYear`(int16) · `OperatingModel`(Dedicated | Multi-User)

### 1.16 `DimSku` — 12,000 rows

`SkuKey`(PK) · `SkuCode`(`SKU-000001`) · `SkuDescription` · `CustomerCode`(owning customer) ·
`CommodityKey`(FK) · `ProductCategory` · `ProductSubCategory` ·
`UnitOfMeasure`(EA | CTN | PAL | KG | LTR) · `UnitsPerCarton`(int16) · `CartonsPerPallet`(int16) ·
`UnitWeightKg`(float32) · `UnitVolumeCbm`(float32) · `UnitCostUsd`(float32) · `UnitPriceUsd`(float32) ·
`AbcClassStatic`(A | B | C — the *seeded* class; the DAX-derived one may differ, which is a Week-4 exercise) ·
`IsHazardous`(int8) · `RequiresColdChain`(int8) · `ShelfLifeDays`(int16, nullable) ·
`StorageType`(Ambient | Chilled | Frozen | Hazmat | Bulk) · `IsActive`(int8)

### 1.17 `DimEmployee` — 1,800 rows

`EmployeeKey`(PK) · `EmployeeCode`(`EMP00001`) · `EmployeeName` · `WarehouseKey`(FK) ·
`RoleName`(Picker | Packer | Forklift Operator | Receiver | Checker | Team Lead | Supervisor) ·
`ShiftKey`(int8, FK to DimTime.ShiftKey) · `ShiftName` ·
`EmploymentType`(Permanent | Agency | Seasonal) · `HireDate`(date) ·
`TenureBand`(<6m | 6–12m | 1–2y | 2–5y | 5y+) · `IsCertifiedForklift`(int8) · `IsActive`(int8)

### 1.18 `DimCurrency` — 22 rows

`CurrencyKey`(PK) · `CurrencyCode`(ISO-3) · `CurrencyName` · `CurrencySymbol` ·
`DecimalPlaces`(int8) · `IsReportingCurrency`(int8, USD=1) · `RegionUsed`

### 1.19 `DimScenario` — 4 rows

`ScenarioKey`(PK) · `ScenarioCode`(ACT BUD FCT PLN) · `ScenarioName`(Actual | Budget | Forecast | Plan) · `SortOrder`(int8)

---

## 2. Facts (11)

### 2.1 `FactBooking` — 420,000 rows · transaction grain: one booking line

Keys: `BookingKey`(PK int64) · `BookingNo`(degenerate, `BKG25000001`) ·
`BookingDateKey` · `RequestedDepartureDateKey` · `ConfirmedDepartureDateKey`(-1 if never confirmed) · `CutoffDateKey` ·
`CustomerKey`(SCD2-resolved to the version valid at booking date) · `LocationKeyOrigin` · `LocationKeyDestination` ·
`CarrierKey` · `VoyageKey`(-1 if unassigned) · `ServiceKey` · `EquipmentKey` · `ModeKey` ·
`CommodityKey` · `IncotermKey` · `CurrencyKey` · `QuoteKey`(int64, degenerate)

Measures: `ContainerCount`(int16) · `TeuBooked`(float32) · `FfeBooked`(float32) ·
`WeightKgBooked`(float32) · `VolumeCbmBooked`(float32) ·
`QuotedRatePerContainer_doc`/`_usd`(float32) · `QuotedTotal_doc`/`_usd`(float32) ·
`RolloverCount`(int8, 0–3) · `LeadTimeDays`(int16, booking→requested departure) ·
`IsConfirmed` · `IsRolled` · `IsCancelled` · `IsNoShow` · `IsSpotBooking` · `IsReeferBooking` · `IsDangerousGoods` · `IsShipperOwnedEquipment`(all int8) ·
`BookingStatus`(Confirmed | Rolled | Cancelled | No-Show | Pending)

Distribution targets: 78% Confirmed · 9% Rolled · 8% Cancelled · 3% No-Show · 2% Pending.
Rollover ratio rises to ~19% inside the congestion window (§3.3).

### 2.2 `FactShipment` — 360,000 rows · transaction grain: one house bill of lading

Keys: `ShipmentKey`(PK int64) · `HouseBlNo` · `MasterBlNo` · `BookingKey`(FK) ·
`ShipmentDateKey`(= actual departure) · `EtaDateKey` · `AtaDateKey` · `DeliveryDateKey` ·
`CustomerKey` · `LocationKeyOrigin` · `LocationKeyDestination` · `LocationKeyPol` · `LocationKeyPod` ·
`CarrierKey` · `VoyageKey` · `ServiceKey` · `ModeKey` · `EquipmentKey` · `CommodityKey` ·
`IncotermKey` · `CurrencyKey` · `WarehouseKey`(-1 unless warehousing attached)

Measures: `ContainerCount`(int16) · `Teu` · `Ffe` · `GrossWeightKg` · `VolumeCbm` ·
`ChargeableWeightKg`(float32 — air per `DimMode.ChargeableWeightRule`, ocean LCL via 1:1000) ·
`RevenueTons`(float32, LCL) · `PieceCount`(int32) ·
`Revenue_doc`/`_usd` · `DirectCost_doc`/`_usd` · `GrossProfit_usd` · `GrossMarginPct`(float32) ·
`PlannedTransitDays`(int16) · `ActualTransitDays`(int16) · `TransitVarianceDays`(int16) ·
`DistanceKm`(float32) · `Co2Tonnes`(float32) ·
`IsOnTime`(int8, actual arrival ≤ ETA + 1 day) · `IsInFull`(int8) · `IsDamaged`(int8) · `IsDocumentationClean`(int8) ·
`IsPerfectOrder`(int8, = OnTime AND InFull AND NOT Damaged AND DocumentationClean) ·
`IsTranshipped`(int8) · `TranshipmentCount`(int8) · `ShipmentStatus`(Delivered | In Transit | At Destination | Cancelled)

### 2.3 `FactShipmentMilestone` — 360,000 rows · **accumulating snapshot**: one row per shipment

`ShipmentKey`(PK/FK) · `HouseBlNo` · `CustomerKey` · `ServiceKey` · `ModeKey` · `LocationKeyPol` · `LocationKeyPod`

14 date-key columns, each `int32` with `-1` where the milestone has not occurred:
`BookingConfirmedDateKey` · `EmptyPickupDateKey` · `StuffingDateKey` · `GateInOriginDateKey` ·
`CustomsExportClearedDateKey` · `VesselLoadDateKey` · `VesselDepartureDateKey` ·
`TranshipmentDischargeDateKey` · `TranshipmentLoadDateKey` · `VesselArrivalDateKey` ·
`VesselDischargeDateKey` · `CustomsImportClearedDateKey` · `GateOutDestinationDateKey` · `EmptyReturnDateKey`

Derived lag measures (`int16`, `-1` when either end is missing):
`LagBookingToGateIn` · `LagGateInToLoad` · `LagLoadToDeparture` · `LagDepartureToArrival` ·
`LagArrivalToDischarge` · `LagDischargeToGateOut` · `LagGateOutToEmptyReturn` · `LagTotalDoorToDoor` ·
`MilestonesCompleted`(int8 0–14) · `CurrentMilestoneKey`(FK) · `IsJourneyComplete`(int8)

### 2.4 `FactContainerMove` — 1,420,000 rows · transaction grain: one equipment event

Keys: `ContainerMoveKey`(PK int64) · `ContainerNo`(11-char ISO 6346 with valid check digit) ·
`ShipmentKey`(-1 for empty repositioning moves with no commercial shipment) ·
`EventDateKey` · `EventTs`(datetime) · `TimeKey` ·
`MilestoneKey`(FK) · `LocationKey` · `EquipmentKey` · `CarrierKey` · `VoyageKey` ·
`CustomerKey` · `ModeKey` · `MoveSequence`(int8 within container journey)

Measures: `Teu`(float32) · `Ffe`(float32) · `GrossWeightKg`(float32) ·
`DwellHours`(float32, hours since the previous event at this location; `-1` for the first event) ·
`MoveCostUsd`(float32) · `CraneMoves`(int8) ·
`IsLaden`(int8) · `IsEmpty`(int8) · `IsRepositioning`(int8) · `IsTranshipmentMove`(int8) ·
`IsGateEvent`(int8) · `IsVesselEvent`(int8) · `IsRailEvent`(int8) · `IsInspection`(int8) ·
`FreeTimeDaysUsed`(float32) · `IsPastFreeTime`(int8) · `DemurrageDays`(float32) · `DetentionDays`(float32)

Empty/laden mix target: 68% laden / 32% empty overall, with empty share reaching ~41% on backhaul legs.

### 2.5 `FactPortCall` — 96,000 rows · transaction grain: one vessel call at one terminal

Keys: `PortCallKey`(PK) · `VoyageKey` · `VesselKey` · `LocationKey` · `ServiceKey` · `CarrierKey` ·
`PromisedEtaDateKey`(**the originally published ETA — never revised**) · `RevisedEtaDateKey` ·
`AtaDateKey` · `AtdDateKey` · `BerthDateKey` · `CallSequence`(int8)

Measures: `PromisedEtaTs` · `AtaTs` · `AtdTs` · `BerthTs` · `UnberthTs`(datetime) ·
`ArrivalDelayHours`(float32, signed) · `DepartureDelayHours`(float32) ·
`WaitingForBerthHours`(float32) · `BerthOccupancyHours`(float32) · `TurnaroundHours`(float32) ·
`TotalMoves`(int32) · `DischargeMoves`(int32) · `LoadMoves`(int32) · `RestowMoves`(int16) ·
`CranesDeployed`(int8) · `CraneHoursGross`(float32) · `CraneHoursNet`(float32) ·
`MovesPerCraneHourGross`(float32) · `MovesPerCraneHourNet`(float32) · `MovesPerHourBerth`(float32) ·
`TeuDischarged`(float32) · `TeuLoaded`(float32) · `SlotCapacityTeu`(int32) · `SlotsUsedTeu`(float32) ·
`BunkerConsumedTonnes`(float32) · `PortCostUsd`(float32) ·
`IsOnTimeArrival`(int8, `abs(ATA − PromisedETA) ≤ 24h` — the ±1 calendar-day industry rule) ·
`IsOmitted`(int8) · `IsExtraCall`(int8) · `CallStatus`(Completed | Omitted | Planned)

### 2.6 `FactFreightCharge` — 1,180,000 rows · transaction grain: one charge line

Keys: `ChargeLineKey`(PK int64) · `ShipmentKey`(FK) · `InvoiceNo`(degenerate) · `ChargeLineNo`(int16) ·
`ChargeDateKey` · `InvoiceDateKey` · `ChargeTypeKey` · `CustomerKey` · `CarrierKey` ·
`LocationKey` · `ModeKey` · `EquipmentKey` · `CurrencyKey` · `ContainerNo`(nullable, `#NA`)

Measures: `Quantity`(float32) · `UnitRate_doc`(float32) ·
`Amount_doc`(float32) · `Amount_usd`(float32) · `FxRateUsed`(float32) ·
`RevenueAmount_usd`(float32, 0 for cost lines) · `CostAmount_usd`(float32, 0 for revenue lines) ·
`TaxAmount_usd`(float32) · `ChargeableDays`(float32, D&D lines only) · `TierApplied`(int8 0–3) ·
`IsRevenue`(int8) · `IsCost`(int8) · `IsCreditNote`(int8) · `IsDisputed`(int8) · `IsWaived`(int8) ·
`IsDemurrage`(int8) · `IsDetention`(int8) · `IsSurcharge`(int8) · `SettlementStatus`(Invoiced | Paid | Disputed | Written Off | Credited)

Credit notes are **negative** `Amount_usd` with `IsCreditNote = 1`. 0.3% of lines. They are legitimate and
must survive Power Query cleaning.

### 2.7 `FactTransportLeg` — 320,000 rows · transaction grain: one truck or rail movement

Keys: `TransportLegKey`(PK) · `ShipmentKey`(-1 for empty repositioning) · `TripNo`(degenerate) ·
`PlannedPickupDateKey` · `ActualPickupDateKey` · `PlannedDeliveryDateKey` · `ActualDeliveryDateKey` ·
`CarrierKey` · `LocationKeyOrigin` · `LocationKeyDestination` · `EquipmentKey` · `ModeKey` ·
`CustomerKey` · `WarehouseKey` · `CurrencyKey` · `ContainerNo`

Measures: `DistanceKm`(float32) · `LoadedKm`(float32) · `EmptyKm`(float32) ·
`PlannedDurationHours`(float32) · `ActualDurationHours`(float32) ·
`GateInWaitMinutes`(float32) · `TurnTimeMinutes`(float32, drayage gate-in→gate-out) ·
`DetentionAtSiteHours`(float32) ·
`FreightCostUsd`(float32) · `FuelSurchargeUsd`(float32) · `TollsUsd`(float32) · `AccessorialUsd`(float32) · `TotalCostUsd`(float32) ·
`RevenueUsd`(float32) · `FuelLitres`(float32) · `Co2Kg`(float32) ·
`WeightKg`(float32) · `Teu`(float32) · `DropCount`(int8) · `DeliveryAttempts`(int8) ·
`IsOnTimePickup`(int8, ±2h window) · `IsOnTimeDelivery`(int8, ±4h window) ·
`IsFirstAttemptSuccess`(int8) · `IsEmptyRepositioning`(int8) · `IsBackhaulUtilised`(int8) ·
`IsSubcontracted`(int8) · `LegStatus`(Completed | In Progress | Cancelled | Failed)

`DeadheadPct` is a DAX measure, **not** a stored column: `DIVIDE(SUM(EmptyKm), SUM(DistanceKm))`.

### 2.8 `FactWarehouseTask` — 540,000 rows · transaction grain: one task line

Keys: `WarehouseTaskKey`(PK) · `TaskNo` · `OrderNo`(degenerate) ·
`TaskDateKey` · `TaskStartTs` · `TaskEndTs` · `TimeKey` ·
`WarehouseKey` · `SkuKey` · `EmployeeKey` · `CustomerKey` · `ShipmentKey`(-1 if domestic) ·
`TaskType`(Receive | Putaway | Pick | Pack | Load | Cycle Count | Replenish | VAS) ·
`ShiftKey`(int8)

Measures: `LinesProcessed`(int16) · `UnitsProcessed`(int32) · `PalletsProcessed`(float32) ·
`WeightKg`(float32) · `VolumeCbm`(float32) ·
`LabourMinutes`(float32) · `LabourHours`(float32) · `TravelMetres`(float32) ·
`DockToStockMinutes`(float32, Receive/Putaway only, else `-1`) ·
`LabourCostUsd`(float32) ·
`IsAccurate`(int8) · `ErrorCount`(int16) · `IsRework`(int8) · `IsDamagedOnHandling`(int8) ·
`IsWithinSla`(int8) · `TaskStatus`(Completed | Cancelled | Exception)

### 2.9 `FactInventorySnapshot` — 720,000 rows · **periodic snapshot**: SKU × site × day (weekly for the older 18 months, daily for the latest 12)

Keys: `InventorySnapshotKey`(PK) · `SnapshotDateKey` · `WarehouseKey` · `SkuKey` · `CustomerKey` · `CommodityKey`

Measures (all **semi-additive over date**): `OnHandUnits`(int32) · `OnHandPallets`(float32) ·
`AllocatedUnits`(int32) · `AvailableUnits`(int32) · `InTransitUnits`(int32) ·
`OnHandValueUsd`(float32) · `OnHandCbm`(float32) · `OnHandWeightKg`(float32) ·
`PalletPositionsUsed`(float32) · `PalletPositionsAvailable`(float32) ·
`DaysOfSupply`(float32) · `AgeDaysAvg`(float32) ·
`SystemCountUnits`(int32) · `PhysicalCountUnits`(int32, populated only on cycle-count days else `-1`) ·
`ShrinkageUnits`(int32) · `ObsoleteUnits`(int32) ·
`IsStockout`(int8) · `IsOverstock`(int8) · `IsExpiringWithin30d`(int8)

### 2.10 `FactExchangeRate` — 28,000 rows · periodic snapshot: currency × day

`ExchangeRateKey`(PK) · `RateDateKey` · `CurrencyKey` · `FromCurrencyCode` · `ToCurrencyCode`(always `USD`) ·
`RateToUsd`(float32) · `RateFromUsd`(float32) · `MonthAvgRateToUsd`(float32) · `IsMonthEndRate`(int8)

### 2.11 `FactTarget` — 38,000 rows · transaction grain: KPI × region × month × scenario

`TargetKey`(PK) · `TargetMonthDateKey`(first of month) · `ScenarioKey` · `KpiCode` · `KpiName` ·
`Region` · `TradeLane`(`#NA` where not applicable) · `ModeKey` · `WarehouseKey`(-1 where n/a) · `CurrencyKey` ·
`TargetValue`(float32) · `StretchValue`(float32) · `ThresholdValue`(float32) ·
`TargetUnit`(USD | FFE | TEU | Pct | Days | Hours | Count) · `IsHigherBetter`(int8)

`KpiCode` values must be drawn from the KPI dictionary codes so the join is real.

---

## 3. Behavioural requirements

### 3.1 Seasonality
- **Lunar New Year**: weeks containing 22 Jan 2023 / 10 Feb 2024 / 29 Jan 2025 / 17 Feb 2026 — Asia-origin volume falls to 0.55× baseline for 2 weeks, then rebounds to 1.18× for 2 weeks.
- **Peak season**: Aug–Oct volume 1.22× baseline; freight rate index 1.35× baseline; rollover ratio doubles.
- **Q4 rate spike**: Nov–Dec spot rates 1.4× contract.
- **Weekday effect**: gate and warehouse events 0.35× on Sundays, 0.7× on Saturdays.
- **Underlying growth**: +6% YoY volume trend.

### 3.2 Trade imbalance
Headhaul (Asia→Europe, Asia→N America, ISC→Europe) load factor 88–96%; backhaul 55–70%.
Backhaul empty share ~41%. Revenue per FFE on backhaul ~0.52× headhaul.

### 3.3 The congestion event
**14 Jul 2025 → 14 Sep 2025**, at `NLRTM` and `USLAX`, propagating:

| Effect | Change |
|---|---|
| `WaitingForBerthHours` | ×3.4 |
| `MovesPerCraneHourNet` | ×0.72 |
| `TurnaroundHours` | ×1.9 |
| `IsOnTimeArrival` rate | 0.68 → 0.31 |
| Container `DwellHours` at those ports | ×2.6 |
| `RolloverCount` | ×2.1 |
| Demurrage charge lines | ×3.1 in volume |
| Landside `TurnTimeMinutes` | ×1.7 |
| `TransitVarianceDays` on affected services | +6.4 mean |

This is the analytical set-piece: demurrage *revenue* rises sharply while the operation degrades.

### 3.4 Distributions
- Transit variance: right-skewed — lognormal(μ=0.9, σ=0.65) days added to nominal, so mean ≠ median and P90 is far right.
- Dwell hours: gamma(k=2.2, θ=18).
- Rate per FFE: lane base × lognormal(0, 0.28) × seasonal index.
- Pick lines per labour hour: normal(μ by role and tenure, σ=0.18×μ), truncated at 0.
- Pick accuracy: 99.1% baseline, dropping to 97.4% on night shift and 98.2% for agency staff in their first 6 months.
- OTIF components: DIF ~0.962, DOQ ~0.987, DOT ~0.913 → headline ~0.867.

### 3.5 Data-quality landmines (deliberate, documented in `00_docs/LANDMINES.md`)

| # | Landmine | Where | Correct handling |
|---|---|---|---|
| 1 | 4.1% nulls in optional fields | `VolumeCbm`, `RequiredTempC`, `ShelfLifeDays`, `RevisedEtaDateKey` | Keep as null; do not zero-fill |
| 2 | 312 duplicated `BookingNo` with differing detail | `FactBooking` | Dedupe on latest `BookingDateKey`, document the rule |
| 3 | Mixed casing + trailing whitespace | `DimLocation.LocationName` (8% of rows) | `Text.Trim` + `Text.Proper` |
| 4 | Two spellings of the same country | `DimLocation.CountryName` — "Viet Nam"/"Vietnam", "Korea, Republic of"/"South Korea" | Conform via a mapping table, not find-and-replace |
| 5 | 0.3% negative charge amounts | `FactFreightCharge` | These are credit notes — **must be retained** |
| 6 | 47 late-arriving dimension members | `FactShipment.CustomerKey` referencing customers whose `OnboardedDate` is after the shipment | Route to the `-1` unknown member and report the count |
| 7 | Date stored as text in one file | `FactTarget.TargetMonthDateKey` mirror CSV | Locale-aware parse; the file is `dd/MM/yyyy` |
| 8 | `DimVessel.NominalTeuCapacity` has 3 implausible outliers | `DimVessel` | Flag, do not silently drop |
| 9 | One fact partition has a column in a different order | `FactContainerMove/year=2023/month=07` | Prove that Parquet schema-on-read handles it and CSV would not |
| 10 | Leading-zero business keys | `DimSku.SkuCode` mirror CSV | Import as text, not number |

### 3.6 Referential integrity
Every fact FK must resolve to a dimension key, or be exactly `-1`. The generator emits
`02_data/_validation/integrity_report.json` proving this, plus row counts and KPI plausibility bands.

---

## 4. Validation gates

The generator must not be considered done until `validate.py` passes all of:

1. Row counts within ±0.5% of the contract figures.
2. Zero orphan FKs other than intentional `-1`.
3. Overall laden share 66–70%; backhaul empty share 39–43%.
4. Headhaul load factor mean 0.88–0.96; backhaul 0.55–0.70.
5. On-time arrival rate 0.62–0.70 outside the congestion window, 0.28–0.34 inside it.
6. Perfect order rate 0.84–0.89. OTIF 0.85–0.88.
7. Gross margin mean 0.14–0.22, with a left tail below zero (loss-making shipments must exist).
8. Every `DimMilestone.EventCode` appears in `FactContainerMove` or `FactShipmentMilestone`.
9. All 11 Incoterms appear in `FactShipment`.
10. Every `ContainerNo` passes the ISO 6346 check-digit test.
11. Every `ImoNumber` passes the IMO check-digit test.
12. Credit-note lines sum to a negative total and are 0.25–0.35% of charge lines.
13. `SUM(FactFreightCharge.RevenueAmount_usd)` reconciles to `SUM(FactShipment.Revenue_usd)` within 0.5%.
14. Congestion-window effects measurable at the stated magnitudes ±15%.
