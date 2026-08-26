from detectmatelibrary.detectors.random_detector import RandomDetectorConfig

from detectmatelibrary.common.core import CoreConfig

import yaml


def update_docs(config: CoreConfig, doc_path: str) -> None:
    arguments = "| Field  | Type  | Default Value| Description|\n|-------|------|-----|---|\n"
    for arg in config.get_docs():
        arguments += f"|{arg['Name']}|{arg["Type"]}|{arg["Default value"]}|{arg["Description"]}|\n"

    with open(doc_path, "r") as f:
        docs = f.readlines()

    start_idx = docs.index("<!-- Start arguments -->\n")
    end_idx = docs.index("<!-- End arguments -->\n")
    docs = docs[:start_idx + 1] + [arguments] + docs[end_idx:]

    pretty_yaml = yaml.dump(
        config.to_dict("<COMPONENT_NAME>"), indent=4, default_flow_style=False, sort_keys=False
    )
    pretty_yaml = "```yaml\n" + pretty_yaml + "```\n"
    start_idx = docs.index("<!-- Start config -->\n")
    end_idx = docs.index("<!-- End config -->\n")
    docs = docs[:start_idx + 1] + [pretty_yaml] + docs[end_idx:]

    with open(doc_path, "w") as f:
        f.writelines(docs)


update_docs(RandomDetectorConfig(), doc_path="docs/detectors/random_detector.md")
