from detectmatelibrary.detectors.random_detector import RandomDetectorConfig

from detectmatelibrary.common.core import CoreConfig

import yaml


# %% Methods
def append_docs(docs: str, start_cmd: str, end_cmd: str, add: str) -> None:
    start_idx = docs.index(start_cmd)
    end_idx = docs.index(end_cmd)
    if start_idx < end_idx:
        raise Exception(f"'{start_cmd}' should be before '{end_cmd}'")

    return docs[:start_idx + 1] + [add] + docs[end_idx:]


def get_arguments(config: CoreConfig) -> str:
    arguments = "| Field  | Type  | Default Value| Description|\n|-------|------|-----|---|\n"
    for arg in config.get_docs():
        arguments += f"|{arg['Name']}|{arg["Type"]}|{arg["Default value"]}|{arg["Description"]}|\n"
    return arguments


def config_yaml(config: CoreConfig) -> str:
    pretty_yaml = yaml.dump(
            config.to_dict("<COMPONENT_NAME>"), indent=4, default_flow_style=False, sort_keys=False
        )
    return "```yaml\n" + pretty_yaml + "```\n"


def update_docs(config: CoreConfig, doc_path: str) -> None:
    try:
        with open(doc_path, "r") as f:
            docs = f.readlines()

        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start arguments -->\n",
            end_cmd="<!-- End arguments -->\n",
            add=get_arguments(config)
        )

        docs = append_docs(
            docs=docs,
            start_cmd="<!-- Start config -->\n",
            end_cmd="<!-- End config -->\n",
            add=config_yaml(config)
        )

        with open(doc_path, "w") as f:
            f.writelines(docs)
    except Exception as e:
        raise Exception(f"While updating {doc_path} -> {str(e)}")


# %% Documentation update
update_docs(RandomDetectorConfig(), doc_path="docs/detectors/random_detector.md")
