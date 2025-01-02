# Messing with the Search Index

- `FindingModelDb` maintains a separate instance of `SearchIndex` (keyed to a `finding_models` table in LanceDB) that it can use to do semantic searches
- `FindingModelDb` class has a `semantic_search()` method that looks into the search index object and performs a hybrid search, gets the model IDs, and then brings those back as `FindingModelDb` objects.
- Using Beanie's [event-based actions](https://beanie-odm.dev/tutorial/event-based-actions/), the index is automatically updated whenever a `FindingModelDb` object has `save()` or `delete()` called on it, and makes the appropriate changes to the database.

## Setup

```python
# Maybe have to make sure we're in the right directory... 🙃
import os
from pathlib import Path

os.chdir("packages/findingmodelforge")
print(Path.cwd())

# Set up
from findingmodelforge.database import init_document_models
from findingmodelforge.models.finding_model_db import FindingModelDb, search_index
await init_document_models()
doc_count = await FindingModelDb.count()
index_count = search_index.index_count()
print(f"{doc_count} documents, {index_count} index entries")

# > 4 documents, 4 index entries

index_fms = { 
    r["model_id"]: r["name"] 
    for r in search_index.table.search().where("model_id IS NOT NULL").to_list() 
}

# > {'676d72d634391d71cadb112a': 'ACL tear',
# >  '676dc0fe02e361bc820f2e5e': 'medial meniscus tear',
# >  '6771beecabddd984f57716c5': 'pcl tear',
# >  '6776da9134b39e04fe58be88': 'lateral meniscus tear',
# >  '6776f68bd0995c05f1335027': 'medial collateral ligament tear'}

```

## Searching

```python
finding_models = await FindingModelDb.semantic_search("ligament", top_k=3)

# >[FindingModelDb(id=ObjectId('676d72d634391d71cadb112a'), revision_id=None, name='ACL tear', description='An ACL tear refers to the rupture or complete tear of the anterior cruciate ligament, a critical stabilizing ligament in the knee, often resulting from sports-related injuries and characterized by knee instability, swelling, and pain.', synonyms=['Anterior Cruciate Ligament tear', 'ACL injury', 'ACL rupture'], tags=['knee', 'mri'], attributes=[ChoiceAttribute(name='presence', description='Presence or absence of acl tear', type=<AttributeType.CHOICE: 'choice'>, values=[ChoiceValue(name='absent', description='Acl tear is absent'), ChoiceValue(name='present', description='Acl tear is present'), ChoiceValue(name='indeterminate', description='Presence of acl tear cannot be determined'), ChoiceValue(name='unknown', description='Presence of acl tear is unknown')], required=False, max_selected=1), ChoiceAttribute(name='change from prior', description='Whether and how a acl tear has changed over time', type=<AttributeType.CHOICE: 'choice'>, values=[ChoiceValue(name='unchanged', description='Acl tear is unchanged'), ChoiceValue(name='stable', description='Acl tear is stable'), ChoiceValue(name='increased', description='Acl tear has increased'), ChoiceValue(name='decreased', description='Acl tear has decreased'), ChoiceValue(name='new', description='Acl tear is new')], required=False, max_selected=1)], active=True, created_at=datetime.datetime(2024, 12, 26, 15, 14, 30, 283000), updated_at=None),
# > FindingModelDb(id=ObjectId('6771beecabddd984f57716c5'), revision_id=None, name='PCL tear', description='A posterior cruciate ligament (PCL) tear is a common knee injury resulting from excessive posterior translation of the tibia relative to the femur, often associated with significant knee instability and dysfunction.', synonyms=['Posterior Cruciate Ligament tear', 'PCL injury'], tags=['knee', 'mri'], attributes=[ChoiceAttribute(name='presence', description='Presence or absence of pcl tear', type=<AttributeType.CHOICE: 'choice'>, values=[ChoiceValue(name='absent', description='Pcl tear is absent'), ChoiceValue(name='present', description='Pcl tear is present'), ChoiceValue(name='indeterminate', description='Presence of pcl tear cannot be determined'), ChoiceValue(name='unknown', description='Presence of pcl tear is unknown')], required=False, max_selected=1), ChoiceAttribute(name='change from prior', description='Whether and how a pcl tear has changed over time', type=<AttributeType.CHOICE: 'choice'>, values=[ChoiceValue(name='unchanged', description='Pcl tear is unchanged'), ChoiceValue(name='stable', description='Pcl tear is stable'), ChoiceValue(name='increased', description='Pcl tear has increased'), ChoiceValue(name='decreased', description='Pcl tear has decreased'), ChoiceValue(name='new', description='Pcl tear is new')], required=False, max_selected=1)], active=True, created_at=datetime.datetime(2024, 12, 29, 21, 28, 12, 271000), updated_at=datetime.datetime(2025, 1, 2, 20, 31, 4, 363000)),
# > FindingModelDb(id=ObjectId('6776da9134b39e04fe58be88'), revision_id=None, name='lateral meniscus tear', description='A lateral meniscus tear is a common knee injury characterized by a disruption of the fibrocartilaginous structure on the outer aspect of the knee joint, often resulting from traumatic twisting or degeneration, and may present with joint pain, swelling, and mechanical symptoms.', synonyms=['lateral meniscus injury', 'lateral meniscus rupture', 'LM tear'], tags=['knee', 'mri'], attributes=[ChoiceAttribute(name='presence', description='Presence or absence of lateral meniscus tear', type=<AttributeType.CHOICE: 'choice'>, values=[ChoiceValue(name='absent', description='Lateral meniscus tear is absent'), ChoiceValue(name='present', description='Lateral meniscus tear is present'), ChoiceValue(name='indeterminate', description='Presence of lateral meniscus tear cannot be determined'), ChoiceValue(name='unknown', description='Presence of lateral meniscus tear is unknown')], required=False, max_selected=1), ChoiceAttribute(name='change from prior', description='Whether and how a lateral meniscus tear has changed over time', type=<AttributeType.CHOICE: 'choice'>, values=[ChoiceValue(name='unchanged', description='Lateral meniscus tear is unchanged'), ChoiceValue(name='stable', description='Lateral meniscus tear is stable'), ChoiceValue(name='increased', description='Lateral meniscus tear has increased'), ChoiceValue(name='decreased', description='Lateral meniscus tear has decreased'), ChoiceValue(name='new', description='Lateral meniscus tear is new')], required=False, max_selected=1)], active=True, created_at=datetime.datetime(2025, 1, 2, 18, 27, 29, 291000), updated_at=None)]
```

## Create Entry

Just an example of creating a `FindingModelDb`; don't have to do anything, since calling `save()` automatically inserts it into the database.

```python
mcl_tear_json = """
{
  "name": "medial collateral ligament tear",
  "description": "A medial collateral ligament tear involves a partial or complete disruption of the ligament located on the inner side of the knee, often resulting from trauma or excessive valgus stress.",
  "synonyms": [
    "MCL tear",
    "Medial collateral ligament injury"
  ],
  "tags": [
    "knee",
    "mri"
  ],
  "attributes": [
    {
      "name": "presence",
      "description": "Presence or absence of medial collateral ligament tear",
      "type": "choice",
      "values": [
        {
          "name": "absent",
          "description": "Medial collateral ligament tear is absent"
        },
        {
          "name": "present",
          "description": "Medial collateral ligament tear is present"
        },
        {
          "name": "indeterminate",
          "description": "Presence of medial collateral ligament tear cannot be determined"
        },
        {
          "name": "unknown",
          "description": "Presence of medial collateral ligament tear is unknown"
        }
      ],
      "required": false,
      "max_selected": 1
    },
    {
      "name": "change from prior",
      "description": "Whether and how a medial collateral ligament tear has changed over time",
      "type": "choice",
      "values": [
        {
          "name": "unchanged",
          "description": "Medial collateral ligament tear is unchanged"
        },
        {
          "name": "stable",
          "description": "Medial collateral ligament tear is stable"
        },
        {
          "name": "increased",
          "description": "Medial collateral ligament tear has increased"
        },
        {
          "name": "decreased",
          "description": "Medial collateral ligament tear has decreased"
        },
        {
          "name": "new",
          "description": "Medial collateral ligament tear is new"
        }
      ],
      "required": false,
      "max_selected": 1
    }
  ],
  "active": true,
  "created_at": "2025-01-02T18:41:49.668000"
}
"""

# Save to the database; this should automatically update the index
mcl_tear = FindingModelDb.model_validate_json(mcl_tear_json)
mcl_tear.save()
```
