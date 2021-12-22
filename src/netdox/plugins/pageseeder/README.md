### Node Plugin
---
# PageSeeder Licenses

This plugin reads PSML files from `website/ps-licenses` on your PageSeeder instance, and uses them to infer which discovered Nodes are running PageSeeder.
There is no exact template for the documents, although the properties `domain`, `license-type`, and `organization` are expected in a section with ID `details`.
- `domain` may be an XRef to a Netdox domain document, and must be present.
- `organization` must be an XRef to an organization document if present.
- `license-type` is optional.