# `findingmodelforge` Package

Contains library code for managing `FindingModel` objects.

## Models

### `FindingModel`

Basics of a finding model, including name, description, and attributes.

### `FindingModelDb`

Inherits `FindingModel`, ready for inclusion in database with timestamps, etc.

### `DescribedFinding`

Brief information on a finding, including description and synonyms.

### `DescribedFindingWithDetail`

Inherits `DescribedFinding` and adds a detailed description and citations.

## Generator Tools

### `describe_finding_name(finding_name: str) -> DescribedFinding | Any`

Takes a finding name and generates a usable description and possibly synonyms (`DescribedFinding`) using OpenAI models (requires `OPENAI_API_KEY` to be set to a valid value).

```python
from finding_model_generator import describe_finding_name

await describe_finding_name("Pneumothorax")

>>> DescribedFinding(finding_name='pneumothorax', synonyms=['PTX'], description='Pneumothorax is the presence of air in the pleural space, which can lead to partial or complete lung collapse, typically identified on imaging by the absence of vascular markings in the affected hemithorax.')
```

### `get_detail_on_finding(finding: DescribedFinding) -> DescribedFindingWithDetail | None`

Takes a described finding as above and uses Perplexity to get a lot of possible reference information, possibly
including citations (requires `PERPLEXITY_API_KEY` to be set to a valid value).

```python
from finding_model_generator import get_detail_on_finding

finding = DescribedFinding(finding_name="pneumothorax", synonyms=['PTX'],
    description='Pneumothorax is the presence...')

await get_detail_on_finding(finding)

>>> DescribedFindingWithDetail(finding_name='pneumothorax', synonyms=['PTX'], 
 description='Pneumothorax is the...'
 detail='## Pneumothorax\n\n### Appearance on Imaging Studies\n\nA pneumothorax...',
 citations=['https://pubs.rsna.org/doi/full/10.1148/rg.2020200020', 
  'https://ajronline.org/doi/full/10.2214/AJR.17.18721', ...])
```
