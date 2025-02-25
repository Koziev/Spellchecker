# Spellchecker

This is a rule- and dictionary-based spellchecker for Russian-language texts with emphasize on precision over recall.


### Precision is Our Top Priority

The core principle behind this spell checker is the absolute minimization of false positives.
To achieve this, the tool is designed to correct only those errors where the intended correction is unambiguous.
While it’s impossible to completely eliminate false positives — such as in cases of intentionally distorted or stylized language — the system prioritizes accuracy and reliability above all else.
Below is a result of evaluation the spellchecker on the [RUPOR](https://github.com/Koziev/RUPOR) dataset:

| Domain               | F<sub>0.5</sub> | F<sub>1</sub> | Precision | Recall |
|----------------------|-----------------|---------------|-----------|--------|
| RUPOR poetry         | 0.75            | 0.56          | 0.98      | 0.39   |
| RUPOR prose          | 0.82            | 0.64          | 1.0       | 0.47   |


*More detailed description is coming soon*

