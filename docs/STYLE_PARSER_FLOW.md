# Engine GUI style parser and rejected local overrides

This is an offline follow-up to [experimental style-repair issue #17](https://github.com/Indegosblade/RR3-DevOps/issues/17). The preserved original executable and original encrypted resource were inspected and executed in a bounded ARM64 emulator on 28 October 2026. No game assets, executable, device state, signatures, or releases were changed.

The original engine **rejects the malformed local style file and skips its entire ingestion**. The exact two-byte repair makes its original loader accept the document and reach the style-ingestion call. This establishes parser acceptance and control flow. Event selection and rendered appearance remain unverified.

## Exact code path

```text
style directory stack, searched from its last entry
  -> LocalStyles.xml: 0x100531118 / 0x100531130
  -> path-specific loader 0x100504624
  -> resource reader + inline GUI decryption 0x1005042a8
  -> XML buffer parser 0x1006163f8, flags 0x74
  -> parse-result success test 0x1006162c0: status == 0
      failure -> XML LOAD ERROR log -> return 0
      success -> return 1
  -> LocalStyles caller tests return at 0x10053111c / 0x100531134
      failure -> next directory; no style ingestion
      success -> 0x100530e50 -> Colours ingestion 0x100531720
```

The parser identity is tied to the consuming code, rather than inferred from the presence of an XML library in imports. Parser core `0x100617348` calls node allocator `0x100615c24`, which can call page allocator `0x10061829c`. An assertion inside that allocator references `pugixml.cpp` at `0x100618384`. The same parser's result-description table is at `0x102bd0578`. NSXMLParser/libxml2 imports elsewhere do not own this traced GUI path.

The buffer-loader call is at `0x1005045b4`; its success test is at `0x1005045c4`. On failure, the original instructions obtain the parser description, log `XML LOAD ERROR: %s (offset %d)`, and return zero. The parser may have built a partial tree before returning, but this consumer does not ingest that partial tree after the failed load.

The global style loader at `0x100530d00` loads `GlobalStyles.xml` through `0x100503ec8`, ultimately using the same `0x1005042a8` parser path. It passes global mode `1` to `0x100530e50`; the local loader passes mode `0`. The color ingestion routine inserts global definitions into its named-color map. Existing local definitions append an override to the matching color record (up to eight entries); a local name without a global entry logs that it will be used as a global default. A failed document never reaches those local updates.

## Original-instruction execution

[The read-only tracer](../scripts/trace_style_parser.py) requires the exact preserved original executable SHA-256 `05f85ca03a46ae326774fc5960c6f7d0e6a8d03a6480e168a65882d6fbeb3a0f` and the original encrypted resource SHA-256 `3af680491c7073f47271a4ed2efe1d23117d7b67bf2e4b205322cde4537c549a`. It extracts executable code and resources at runtime; the repository contains no copied parser binary or game-resource fixture.

```text
python scripts/trace_style_parser.py original.ipa --emulate --output style-parser.json
python -m unittest discover -s tests -p test_style_parser.py -v
```

`--emulate` needs Unicorn. Without it, the tool still produces the guarded static call chain and all color comparisons. The test suite runs its original-code integration checks when the preserved local IPA and Unicorn are available; otherwise it explicitly skips those checks.

| Actual input | Original parser result | Original encrypted loader | Local consumer decision |
|---|---|---|---|
| Original 1,073-byte resource | Status `11`, offset `1052`, encoding `1`: `Error parsing start element tag` | Returns `0`, reaches XML error logging | Skips style ingestion |
| Resource with exact `/>` insertion, 1,075 bytes | Status `0`: `No error` | Returns `1` | Calls style ingestion |

The first probe executes the original document constructor, buffer parser, result-success test, and result-description routine against the real decrypted bytes. The second supplies the **actual encrypted resource** at the file-read boundary and executes the original inline decryption, parser, and result/error-check path. It then passes the loader's measured return value through the original local consumer's branch and argument-setup instructions. The ingestion function is a recorded hook, so this proves admission to that function rather than its complete execution.

Hooks model bounded allocation, free/delete without address reuse, memory copies, string length, the resource-read result, the XML logging sink, and the style-ingestion call boundary. The stack-protector GOT slot is resolved to synthetic emulated memory because the Mach-O is not running under dyld. Any other external call or exhausted instruction/allocation budget fails the probe. These tests do not emulate iOS resource lookup, filesystem decompression, dyld initialization, full process lifetime, or rendering.

## Whole-file comparison changes the fallback interpretation

The final malformed `lts_popup_backing_color` matches the global value, but there are **12** local colors in this document and **seven** differ from their global definitions. Rejection therefore drops more than the final color. All 12 names have a global definition. Alpha defaults to `255` and matches for every row.

| Color name | Local RGB | Global RGB | Different |
|---|---|---|---|
| `lts_main_color` | `255,255,255` | `255,225,255` | Yes |
| `lts_secondary_color` | `255,255,255` | `255,225,255` | Yes |
| `lts_tertiary_color` | `66,3,3` | `33,33,33` | Yes |
| `lts_white_label` | `225,225,225` | `255,255,255` | Yes |
| `lts_title_backing_color` | `25,25,25` | `255,255,255` | Yes |
| `tt_row_main_color` | `100,100,100` | `100,100,100` | No |
| `tt_row_secondary_color` | `124,124,124` | `124,124,124` | No |
| `lts_main_menu_title_color` | `255,255,255` | `255,255,255` | No |
| `lts_main_menu_gradient_color` | `30,30,30` | `255,255,255` | Yes |
| `lts_main_menu_banner_secondary_color` | `255,255,255` | `255,255,255` | No |
| `lts_eventcard_unlock_text` | `225,225,225` | `237,28,36` | Yes |
| `lts_popup_backing_color` | `221,221,221` | `221,221,221` | No |

This is a comparison of the complete repaired local document and preserved GlobalStyles resource, using host XML parsing only for extraction. The engine parser acceptance above comes from original engine instructions. Since other active local directories can contribute their own overrides, these global values are a baseline, not a measured screenshot's final color.

The evidence now supports an engine-level syntax/ingestion repair if this event directory is requested. It still does not establish that this historical event is reachable, that a particular screen consumes the affected colors, or that the repair explains reported black backgrounds. Those event and visual checks remain open.
