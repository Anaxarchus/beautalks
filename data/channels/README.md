# beautalks channel database (US national + Alaska)

Research snapshot compiled **2026-11-08**. All source URLs were accessed on 2026-11-08 unless a
row says otherwise. Every row carries its own `source`. Frequencies change, especially repeaters,
airport frequencies and agency channels, so check them against the source before relying on them.

Scope: only channels inside Baofeng UV-5R / UV-5RM class ranges (RX ~136–174 and ~400–520 MHz;
UV-5RM adds 108–136 MHz AM airband RX, 200–260 and 350–390 MHz). All rows were range-checked.

## Columns

| column | meaning |
|---|---|
| `set` | dataset id |
| `name` | 7 characters or fewer (UV-5R name limit), unique across all files |
| `long_name` | descriptive name |
| `rx_mhz` / `tx_mhz` | radio receive / transmit frequency. `tx_mhz` is empty when the service defines no transmit frequency (broadcast or listen-only services: NOAA, aviation AM, marine ch 15). For repeaters, `tx_mhz` is the repeater input. |
| `mode` | `FM` (25/20 kHz), `NFM` (12.5 kHz class), `AM` (airband) |
| `rx_tone` / `tx_tone` | CTCSS such as `103.5`, DCS such as `D023N`, or empty |
| `license_note` | **Advisory only.** `none` = licence-free service; `required` = the service needs a licence or authorisation (GMRS, amateur, Part 90, federal); `rx_only_service` = a broadcast or listen service (NOAA, aviation, ATIS). The app does not enforce this column. |
| `license` | the licence or service in plain language |
| `notes` | power, bandwidth, usage, conflicts, verification notes |
| `source` | URL or URLs the row was taken from or checked against |

## Datasets

| file | rows | content | primary source |
|---|---|---|---|
| `us_frs.csv` | 22 | FRS 1–22 (NFM; ch 8–14 0.5 W ERP, others 2 W ERP) | 47 CFR 95.563/.567/.573/.575 (customsmobile.com eCFR mirror) |
| `us_gmrs.csv` | 30 | GMRS 1–22 simplex + 8 repeater pairs 15R–22R (+5 MHz input) | 47 CFR 95.1763, 95.1767 (law.cornell.edu); fcc.gov/general-mobile-radio-service-gmrs |
| `us_murs.csv` | 5 | MURS 1–5 (151.82/.88/.94 at 11.25 kHz NFM; 154.57/.60 at 20 kHz FM) | 47 CFR 95.2763, 95.2767, 95.2773 |
| `us_noaa.csv` | 7 | NOAA Weather Radio WX1–WX7 | weather.gov/ajk/nwr (NWS) |
| `ak_noaa_transmitters.csv` | 48 | Alaska NWR transmitters: call sign, site, frequency | State of Alaska EAS Plan App. H; NWS Juneau NWR page; NWS Marine Alaska NWR page; NWS Anchorage brochure |
| `us_marine.csv` | 48 | US marine VHF voice channels, with ship TX/RX (duplex channels show coast TX as `rx_mhz`) | USCG NAVCEN US VHF channel table; 47 CFR 80.369 |
| `us_interop.csv` | 83 | NIFOG/CISA interop: VCALL10, VTAC11–14, 17/17D, 33–38, VFIRE21–26, VMED28/29, VLAW31/32, UCALL40/UTAC41–43 (+D), UHF MED-1…MED-102 (+D), federal NC1/IR1–9, LE A/LE 1 | CISA "Programming Template for Interoperability Radio Channels" (ICS-217A, 12/2020) |
| `us_sar_fire.csv` | 8 | VSAR16; wildland-fire National Air Guard 168.625, National Flight Following 168.650, 5 air-tactics frequencies | CISA template; NIICD 2022 National Interagency Aviation Frequency Guide |
| `us_ham_calling.csv` | 2 | 146.520 and 446.000 national simplex | ARRL band plan; Alaska ARES guide |
| `ak_ham_repeaters.csv` | 67 | Alaska analog FM repeaters listed On-Air/Open: Anchorage, Eagle River, Mat-Su, Fairbanks area, Interior, Kenai, PWS, Kodiak, Southeast, Nome, Bethel | RepeaterBook Alaska listing (viewed 2026-11-08), with some rows cross-checked against Juneau ARC, YARA and the Alaska ARES guide |
| `us_aviation.csv` | 14 | 121.5 guard, UNICOM/MULTICOM set, 122.75 air-to-air, 123.025 helicopter, 123.1 SAR (AM, UV-5RM receive) | FAA AIM 4-1 Table 4-1-11, AIM 6-3-1; 47 CFR 87.375 |
| `ak_aviation.csv` | 26 | ANC, Merrill Field, Lake Hood, Fairbanks: ATIS/tower/ground/clearance/approach (AM) | AirNav (FAA data effective 01 Oct / 29 Oct 2026) |
| `ak_state.csv` | 6 | Alaska BLM/AICC and Division of Forestry flight following (AM), DOF tanker ramp, Chugach NF flight-following repeaters | NIICD 2022 National Interagency Aviation Frequency Guide (Alaska section) |
| `us_business.csv` | 15 | Part 90 itinerant / "dot" and "star" business frequencies | Wikipedia "Business band" (secondary source; see gaps) |

### Source URLs (all accessed 2026-11-08)
- FRS: https://www.customsmobile.com/regulations/expand/title47_chapterI-i4_part95_subpartB_section95.565 ; 95.587 https://www.law.cornell.edu/cfr/text/47/95.587 ; 95.561 https://www.law.cornell.edu/cfr/text/47/95.561
- GMRS: https://www.law.cornell.edu/cfr/text/47/95.1763 ; https://www.law.cornell.edu/cfr/text/47/95.1767 ; https://www.law.cornell.edu/cfr/text/47/95.1761 ; https://www.fcc.gov/general-mobile-radio-service-gmrs
- MURS: https://www.customsmobile.com/regulations/47/95.2763 ; https://www.customsmobile.com/regulations/title47_chapterI-i4_part95_subpartJ_section95.2773 ; https://www.customsmobile.com/regulations/expand/title47_chapterI-i4_part95_subpartJ_section95.2765
- NOAA: https://www.weather.gov/ajk/nwr ; https://www.weather.gov/marine/aknwr ; https://ready.alaska.gov/Documents/Operations/EAS/EASPlan/EAS_Appendix_H.pdf ; https://www.weather.gov/media/arh/brochures/WFOAnchoragBro.pdf ; https://www.weather.gov/afg/fairbanksradio
- Marine: https://www.navcen.uscg.gov/us-vhf-channel-information ; https://www.law.cornell.edu/cfr/text/47/80.369 ; https://www.fcc.gov/node/253699 (who needs a ship station licence)
- Interop: https://www.cisa.gov/sites/default/files/publications/Programming%20Template%20for%20Interoperability%20Radio%20Channels%20-%20FINAL%2010142021_0.pdf
- Fire/SAR: https://gacc.nifc.gov/rmcc/dispatch_centers/r2cdc/dispatch/Aviation_folder/National%20Interagency%20Aviation%20Frequency%20Guide.pdf ; https://fire.ak.blm.gov/content/aicc/aimg/Chapter%2050.pdf (2020 Alaska Interagency Mobilization Guide, Air Guard monitoring)
- Ham: https://www.arrl.org/band-plan ; https://www.qsl.net/aresalaska/training/ARES_Emergency_communications_guide.htm ; https://www.repeaterbook.com/repeaters/Display_SS.php?state_id=02 ; https://www.qsl.net/jarc/repeater.htm ; https://www.yara.ca/repeaters/repeaters_Alaska.htm
- Aviation: https://www.faa.gov/air_traffic/publications/atpubs/AIM_html/chap4_section_1.html ; https://www.faa.gov/air_traffic/publications/atpubs/AIM/aim0603.html ; https://www.customsmobile.com/regulations/expand/title47_chapterI-i4_part87_subpartM_section87.373 ; https://airnav.com/airport/ANC ; https://www.airnav.com/airport/PAMR ; https://www.airnav.com/airport/LHD ; https://www.airnav.com/airport/PAFA
- ALMR: https://dot.alaska.gov/iways/proj-ALMR.shtml ; https://wiki.radioreference.com/index.php/Alaska_Land_Mobile_Radio_(ALMR)
- Business: https://en.wikipedia.org/wiki/Business_band
- FCC equipment findings: https://www.fcc.gov/node/215896 (DA 18-980) ; https://rrra.org/post/2018/10/03/fcc-enforcement-advisory-concerning-two-way-vhfsoluhf-radios ; https://www.kb6nu.com/did-the-fcc-just-make-baofengs-illegal-short-answer-no/ ; https://www.fcc.gov/node/214864 (DA 18-801) ; https://www.arrl.org/news/fcc-turns-away-petition-to-allow-hams-to-operate-non-certificated-transmitters-on-gmrs ; https://www.repeaterbook.com/resources/articles/9-blog/12-what-is-legal-and-what-is-not-legal-for-our-chinese-radios ; https://twiar.net/?p=40946

## Licensing and equipment findings (informational)

This is a factual summary, not legal advice. beautalks does not restrict frequencies; the
`license_note` column is advisory only.

- **Equipment authorisation in general.** FCC Enforcement Advisory 2018-03 (DA 18-980, published
  24 Sep 2018) says two-way VHF/UHF radios must be FCC-authorised before import, sale or
  operation. It also says "an amateur licensee may use his or her license to operate such radios",
  and that a radio able to operate outside the amateur bands needs an FCC equipment certification.
  In 2018 an FCC official was quoted (kb6nu.com) as saying radios without Part 95 certification
  "are not authorized for use in FRS or GMRS" and "can be used by amateurs, but only on amateur
  frequencies."
- **FRS.** FRS radios must not be capable of transmitting outside the 22 FRS channels and must have
  a non-removable antenna (47 CFR 95.587(a),(b)). Since 30 Sep 2019 no hand-held radio that covers
  FRS and other licensed services may be made or imported (95.587(e); see also 95.561(c)). A
  wide-range programmable handheld is therefore not an FRS-certified device.
- **GMRS.** A GMRS transmitter "equipped with the capabilities to operate in services that do not
  require equipment certification" (the amateur service, for example) cannot be certified for GMRS,
  and its programming controls must not be reachable by the user (95.1761(c)). In 2014 the FCC
  denied a petition to let hams use non-GMRS-certified radios on GMRS (ARRL News, 7 Jul 2014).
  Some Baofeng/BTECH models are sold as Part 95E GMRS-certified (RepeaterBook article). Whether a
  particular radio holds GMRS certification depends on its FCC ID.
- **MURS.** MURS equipment must be certified, and certification is not granted to a transmitter
  that also operates under other subparts (95.2761(c)). The limit is 2 W output (95.2767).
- **Part 90 (business, public safety).** RepeaterBook says most Baofeng models hold Part 90
  certification. FCC DA 18-801 (2018) cited a seller for marketing the "UV-5R V2+ Part 90
  transceiver" outside the scope of its authorisation. Part 90 transmitting also needs a station
  licence or authorisation for the frequency.
- **Marine.** Recreational ("voluntary") vessels operating domestically do not need a ship station
  licence to use marine VHF (FCC). Marine radios are normally certified under Part 80 (see
  47 CFR 80.203); UV-5R-class radios are not marketed as Part 80 marine radios.
- **Aviation.** Rows are listening references only. The UV-5RM receives AM airband; the UV-5R does
  not cover 108–136 MHz.
- **Amateur.** An amateur licence (Part 97) covers the ham bands. The FCC advisory text above
  addresses amateur use of these radios.
- **Related 2026 enforcement item (informational).** A March 2026 FCC notice (DOC-420097A1,
  reported by twiar.net) involved a BTech UV-Pro whose "audio relay" feature retransmitted a
  monitored public-safety channel (470.4375 MHz). This bears on features that can transmit
  automatically while a radio is set to a listen channel.
- **UV-5RM certification.** Not verified. Look up the FCC ID on the radio's label in the FCC
  equipment authorisation database to see which rule parts it is certified under.

## ALMR and other Alaska state systems

The Alaska Land Mobile Radio (ALMR) system is the statewide trunked public-safety system, run by
the State with DoD and other agencies. Users include DOT&PF, police and fire (dot.alaska.gov).
RadioReference lists it as **Project 25 Phase I trunked, VHF/700 MHz**, System ID 142, WACN BEE00.
P25 is digital, so analog FM radios such as the UV-5R/5RM cannot decode it. **No ALMR channels are
listed for that reason.** No publicly documented analog State of Alaska conventional channels were
found in an authoritative source (see gaps).

## Data conflicts recorded in rows
- **Manleyville NWR:** NWS Juneau lists KAD96 on 162.500; NWS Marine lists 162.525. The row uses 162.500 and notes the conflict.
- **Cold Bay NWR:** NWS Marine lists 162.525; the NWS Anchorage brochure lists KJY87 on 162.425. The row uses 162.525 and notes the conflict.
- **Mt. Robert Barron NWR:** the NWS Juneau page shows KZZ88 in its text but links to KZZ87. The row uses KZZ87 with a note.
- **Soldotna NWR:** the EAS Plan gives WWG39 on 162.475. The Anchorage brochure prints only a generic 162.55 header, so it was not treated as a conflict.
- **Fairbanks NWR (WXJ81):** NWS Fairbanks reports repairs and intermittent service, and NOAA Weather Radio in northern Alaska was reported down in Feb 2025 (KNOM).

## RepeaterBook data terms (important for shipping)
`ak_ham_repeaters.csv` was transcribed from RepeaterBook's public Alaska listing and carries the
attribution "Data courtesy of RepeaterBook.com". RepeaterBook's terms (rev. 13 May 2025) and API
policy prohibit redistribution, derivative datasets and offline bundling without written
permission. Approved programming clients may cache only minimal data, and distributed apps need
per-user tokens. **Do not ship this file inside the GPL app as-is.** Use it as a personal reference,
or replace it with club-published data or a user-triggered RepeaterBook API fetch once permission
is granted. Selection rules: analog FM only, status On-Air/Open. Excluded: DMR "CC" entries,
927/1293 MHz, off-air or unknown-status entries, simplex-flagged "s" entries (Nome KL0EF),
listings missing a call sign (146.64 Willow), and anomalous rows (Sitka KL7SRK 146.08+ and
446.000−, Bethel AL7YK 146.10+, where the output sits in an input or simplex segment). Offsets
follow the listed sign at the band-standard magnitude (0.6 / 1.6 / 5 MHz). The magnitude was
confirmed on detail pages for KL7AA 146.94, KL7KC 146.94, WL7CVG 147.33 and KL7AA 444.2.

## Gaps (not included because they couldn't be verified)
- **Alaska Railroad:** a 2007 RadioReference forum post gives dispatch ch1 164.625, ch7 164.985
  and Anchorage yard 165.265. These are unverified and possibly outdated or narrowbanded, so they
  are not included.
- **Denali NP rangers:** 166.300 / 100.0 comes from the same 2007 forum post and is not included.
- **Alaska Marine Highway (ferry) working channels:** no authoritative source found.
- **Alaska DNR/DOF ground tactical, AST/Wildlife Troopers conventional channels, NPS/USFS
  (other than Chugach) nets:** no current public authoritative list found. The 2020 AK Mobilization
  Guide names Air Guard and NFF but gives no frequencies. The NIICD 2022 guide notes its Alaska data
  was not updated after 2021.
- **Current Alaska ARES VHF/UHF frequencies:** the Alaska ARES plan (2002) lists only HF nets. The
  undated ARES guide lists only 146.52, 446.00 and 147.30/147.90.
- **123.45 MHz "air-to-air":** unofficial, with no FAA source, so it is omitted. The FAA's
  air-to-air frequencies are 122.75 (fixed-wing) and 123.025 (helicopter).
- **223.50 MHz:** ARRL lists 223.40–223.52 as FM simplex but no national calling frequency, so it is
  omitted. Transmit capability on 220 MHz for the UV-5RM is also unverified.
- **Alaska CTAF areas / FSS frequencies statewide, Juneau, Kenai, Wasilla, Palmer and other
  airports:** need the FAA Chart Supplement Alaska. Only ANC, MRI, LHD and FAI were sourced.
- **Sand Point NWR (WNG714):** frequency not stated explicitly in the source.
- **Business itinerant list:** taken from Wikipedia. It was not verified against the 47 CFR 90.35
  frequency table, because the eCFR/FCC pages were not reachable from this session.
- **Railroad AAR channel plan and federal LE 2–9:** LE 2–9 are P25 digital in the template and are
  omitted. The AAR plan was out of scope.
- **NWS national station list (weather.gov/nwr/stations):** not reachable from this session.
  Alaska rows rely on the State EAS Plan and NWS office pages instead.

## Regeneration
These CSVs were generated by a small script kept outside the project
(`scratchpad/tools_channels/build_channels.py`); the CSVs are the deliverable.
