# Sources and benchmark landscape

SVEA separates **task licensing** from **reference-source terms**. Original
pilot wording and synthetic contexts are CC0-1.0. When an item is grounded in
an external source, its record links that source and notes that the source's
own terms remain authoritative. SVEA does not claim ownership of linked facts,
documents or datasets.

## Pilot reference sources

| Area | Source | How it is used |
|---|---|---|
| Elections | [Valmyndigheten](https://www.val.se/om-valmyndigheten) | Stable civic-role question |
| Parliament | [Sveriges riksdag](https://www.riksdagen.se/sv/sa-fungerar-riksdagen/) | Rubric points for a plain-language explanation |
| Appeals | [Sveriges Domstolar](https://www.domstol.se/amnen/overklaga-myndighetsbeslut/) | Inspiration for a fully synthetic evidence/abstention pair |
| Acute care navigation | [1177](https://www.1177.se/Sormland/sa-fungerar-varden/varden-i-sormland/nar-det-ar-fara-for-liv/) | Safety expectation for an emergency-signposting task |
| Literature | [Nobel Prize](https://www.nobelprize.org/prizes/literature/1909/lagerlof/facts/) | Stable Selma Lagerlöf fact |
| Lakes | [SMHI](https://www.smhi.se/kunskapsbanken/hydrologi/sveriges-sjoar) | Stable Swedish geography fact |
| Outdoor access | [Naturvårdsverket](https://www.naturvardsverket.se/amnesomraden/allemansratten/) | Rubric points for a balanced explanation |
| Data protection | [Integritetsskyddsmyndigheten](https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/grundlaggande-principer) | Rubric points for a migration plan |

All other pilot contexts are original synthetic records created for SVEA. They
contain fictional people, organizations, dates, addresses and identifiers.

## Existing Swedish evaluation resources

These resources informed the scope and are catalogued by the project. They are
not copied into SVEA.

### SuperLim 2.0

[SuperLim 2.0](https://github.com/spraakbanken/SuperLim-2) is a standardized
Swedish NLU collection with tasks including NLI, word-in-context, Winograd,
paraphrase, sentiment and retrieval. The collection is also available through
[Språkbanken Text on Hugging Face](https://huggingface.co/datasets/sbx/superlim-2).
Licensing and documentation are task-specific.

### SweSAT-1.0

[SweSAT-1.0](https://github.com/NLP-RISE/swesat) contains native Swedish verbal
and quantitative university entrance exam questions. Its maintainers explicitly
note that reading passages may be copyrighted and provide an upstream retrieval
flow. SVEA links to the project rather than vendoring the material.

### Swedish Medical LLM Benchmark

The [Swedish Medical LLM Benchmark](https://github.com/BirgerMoell/swedish-medical-benchmark)
contains deep Swedish medical exam and clinical-domain evaluation. SVEA's
health-literacy slice measures everyday interpretation, safe communication and
abstention; it is not a substitute for SMLB.

### EuroEval

[EuroEval](https://github.com/EuroEval/EuroEval), formerly ScandEval, provides
cross-language evaluation for model architectures and contains Swedish dataset
configurations. It is the preferred established instrument when the research
question is comparable European NLU performance.

### OpenEuroLLM evaluation tooling

[oellm-eval](https://github.com/OpenEuroLLM/oellm-eval) and related
OpenEuroLLM projects provide task registries, established harnesses and cluster
scheduling. A future SVEA adapter should orchestrate those tools and normalize
their results without changing upstream protocols.

## Source contribution requirements

New items must include a direct source URL, clear task license, access date,
review status and notes about transformation. Do not contribute copyrighted
test passages, personal data, private prompts or restricted exam material.
When reuse terms are unclear, contribute an adapter or metadata link instead of
the content.
