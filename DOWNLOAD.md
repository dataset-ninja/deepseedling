Dataset **DeepSeedling** can be downloaded in [Supervisely format](https://developer.supervisely.com/api-references/supervisely-annotation-json-format):

 [Download](https://assets.supervisely.com/remote/eyJsaW5rIjogImZzOi8vYXNzZXRzLzIxMTNfRGVlcFNlZWRsaW5nL2RlZXBzZWVkbGluZy1EYXRhc2V0TmluamEudGFyIiwgInNpZyI6ICJuN1hrMHE2UFZMdEdGVy9TSWw2NlBTajQwa1QzVFJOek9HWmxKeStZZW8wPSJ9)

As an alternative, it can be downloaded with *dataset-tools* package:
``` bash
pip install --upgrade dataset-tools
```

... using following python code:
``` python
import dataset_tools as dtools

dtools.download(dataset='DeepSeedling', dst_dir='~/dataset-ninja/')
```
Make sure not to overlook the [python code example](https://developer.supervisely.com/getting-started/python-sdk-tutorials/iterate-over-a-local-project) available on the Supervisely Developer Portal. It will give you a clear idea of how to effortlessly work with the downloaded dataset.

The data in original format can be [downloaded here](https://figshare.com/ndownloader/articles/7940456?private_link=616956f8633c17ceae9b).