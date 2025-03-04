# Spellchecker

A high-precision, rule- and dictionary-based spellchecker designed for Russian-language texts. This tool emphasizes precision over recall, making it ideal for preparing clean data for pretraining and fine-tuning language models (LMs).

### Key Features

1. **Precision-First Approach**:

- The spellchecker prioritizes minimizing false positives over catching every possible error. This ensures that corrections are accurate and reliable, which is critical for preparing high-quality training data for language models.

- Incorrect fixes can introduce anomalies that degrade the performance of generative LMs on downstream tasks. This tool avoids such issues by correcting only unambiguous errors.

2. **CPU-Only, No ML Components**:

- The spellchecker operates entirely on the CPU and does not rely on machine learning models. This makes it lightweight, fast, and suitable for processing large text corpora (tens of GBs) in data preparation pipelines.

3. **Interpretability and Determinism**:

- Every correction is traceable and deterministic. You can use a debugger to identify which rule or dictionary entry caused a specific correction, ensuring full transparency and control.

4. **Extensible Dictionary and Rules**:

The spellchecker is designed for easy expansion. You can add new words to the dictionary or define custom replacement rules to adapt the tool to specific domains or use cases.

5. **Restoring Cyrillic Characters in Russian Text**:

Some Latin characters are visually identical or very similar to Cyrillic characters. When these Latin characters appear in Russian text, they can be difficult to detect visually.
However, their presence can significantly impact the quality of language model training, often leading to similar issues in generated texts.
Our experience has shown that the frequency of such defects can be high enough to negatively affect model performance.
To address this, we have developed a simple yet effective solution to restore Cyrillic characters in Russian text - see [restore_cyrillic.py](restore_cyrillic.py).


### Dictionary files

Unfortunately, due to problems with LFS quotas I can't upload the binary files of the dictionary to this repository :(

Use the [link](https://drive.google.com/file/d/1NZwLkpNcnxY15YB19M7O0KKBR2g6e0dL) to download the archive, unpack it to the root of the local copy of the repository.


### Usage

Here’s a [quick example](spellchecker_run.py) of how to use the spellchecker:

```python
from spellcheck import PoeticSpellchecker
from udpipe_parser import UdpipeParser


if __name__ == '__main__':
    parser = UdpipeParser()
    parser.load('./models')

    schecker = PoeticSpellchecker(parser)
    schecker.load('./data')

    new_text, fixups = schecker.fix("Вмести в себя все от кровенья мира")
    print(new_text)
```


### Evaluation

The spellchecker is built on the principle of absolute minimization of false positives. It corrects only those errors where the intended correction is unambiguous. While it’s impossible to eliminate false positives entirely (e.g., in cases of intentionally distorted or stylized language), the system prioritizes accuracy and reliability above all else.

##### Performance on the RUPOR Dataset

The spellchecker has been evaluated on the [RUPOR](https://github.com/Koziev/RUPOR) dataset.
Given the focus on precision, the evaluation uses the F<sub>0.5</sub> metric (which emphasizes precision over recall) instead of the traditional F<sub>1</sub> score.

| Domain               | F<sub>0.5</sub> | Precision | Recall |
|----------------------|-----------------|-----------|--------|
| RUPOR poetry         | 0.75            | 0.98      | 0.39   |
| RUPOR prose          | 0.82            | 1.0       | 0.47   |


*More detailed description is coming soon*


### License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.


### Contributing

We welcome contributions to improve the spellchecker! Here’s how you can help:

- **Expand the dictionary**: Add new words or domain-specific terms.

- **Add new rules**: Define custom replacement rules for common errors.

- **Report issues**: If you encounter any false positives or false negatives, please open an issue on GitHub.

To contribute, fork the repository, make your changes, and submit a pull request.


### Contact

For questions, suggestions, or collaborations, feel free to reach out:

Email: [mentalcomputing@gmail.com]

GitHub Issues: [Open an issue](https://github.com/Koziev/Spellchecker/issues)
