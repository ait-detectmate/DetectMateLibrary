
# --8<-- [start:pickyou]
from detectmatelibrary.detectors.random_detector import RandomDetectorConfig

import detectmatelibrary.helper.select_component as selc

configs = [
    {
        "detectors": {
            "RandomDetector": {"method_type": "random_detector"}
        }
    },
    RandomDetectorConfig(),
]
names = ["RandomDetector", "RandomDetector"]

components = selc.selectComponents(
    configs=configs, names=names, component_type="detectors"
)
print(len(components))  # 2

# --8<-- [end:pickyou]
