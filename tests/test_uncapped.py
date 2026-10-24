from pathlib import Path
import sys
import json
import hashlib
import zipfile
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from complaint_project import make_splits, compare_validation_to_capped, load_capped_reference, SOURCE_SHA256
from import_results import import_results
from api import load_artifacts


def test_uncapped_uses_every_training_row_and_preserves_holdouts():
    records=[]
    for label,training_size in [('A',15005),('B',25)]:
        for date,count in [('2025-01-01',training_size),('2025-02-12',5),('2025-02-20',6)]:
            for i in range(count):
                identity=f'{label}-{date}-{i}'
                records.append(dict(complaint_id=identity,date_received=date,product=label,clean_text=identity,text_hash=identity))
    frame=pd.DataFrame(records)
    capped,capped_manifest=make_splits(frame,'full')
    uncapped,manifest=make_splits(frame,'uncapped')
    assert len(capped['train'])==15025
    assert len(uncapped['train'])==15030
    assert manifest['training_rows_excluded_by_cap']==0
    assert manifest['train_cap_per_class'] is None
    assert capped_manifest['training_rows_excluded_by_cap']==5
    assert uncapped['validation'].equals(capped['validation'])
    assert uncapped['test'].equals(capped['test'])
    assert set(capped['train'].complaint_id).issubset(uncapped['train'].complaint_id)


@pytest.mark.parametrize('new_score,expected',[(0.7,'uncapped'),(0.6,'full'),(0.65,'full')])
def test_profile_recommendation_uses_validation_only(new_score,expected):
    reference={'selected_validation_macro_f1':0.65,'selected_model':'logistic_regression',
               'training_rows':60444,'reference_archive_sha256':'reference',
               'test':{'accuracy':1.0 if expected=='uncapped' else 0.0}}
    result=compare_validation_to_capped(reference,{'model':'logistic_regression','macro_f1':new_score})
    assert result['recommended_profile']==expected
    assert 'test metrics do not choose' in result['criterion']


def test_changed_holdout_is_rejected_before_comparison(tmp_path):
    reference={'source_sha256':SOURCE_SHA256,'holdout_membership':{
        'validation':{'rows':1,'fingerprint':'different'},'test':{'rows':1,'fingerprint':'different'}}}
    (tmp_path/'reference').mkdir()
    (tmp_path/'reference/capped_full_reference.json').write_text(json.dumps(reference))
    frame=pd.DataFrame([dict(complaint_id='x',date_received='2025-02-12',product='A',text_hash='hash')])
    with pytest.raises(ValueError,match='validation complaints differ'):
        load_capped_reference(tmp_path,{'validation':frame,'test':frame})


def test_importer_accepts_separate_uncapped_results(tmp_path):
    # The importer verifies checksums without deserializing a model.
    payload=b'checksum-only fixture, not a trained model'
    archive=tmp_path/'uncapped.zip'
    files={
        'reports/uncapped/metrics.json':json.dumps({'profile':'uncapped','execution_environment':'fixture',
               'selected_model':'fixture','test':{}}),
        'reports/data_manifest.json':json.dumps({'source_sha256':SOURCE_SHA256}),
        'models/uncapped/artifact_manifest.json':json.dumps({'profile':'uncapped','sklearn_version':'1.9.1',
               'model_sha256':hashlib.sha256(payload).hexdigest()}),
        'models/uncapped/classifier.joblib':payload,
    }
    with zipfile.ZipFile(archive,'w') as z:
        for name,content in files.items():
            z.writestr(name,content)
    result=import_results(archive,tmp_path/'imported')
    assert result['profile']=='uncapped'
    assert (tmp_path/'imported/models/uncapped/classifier.joblib').read_bytes()==payload


def test_api_does_not_ignore_a_recommendation_to_keep_capped_model(tmp_path,monkeypatch):
    monkeypatch.delenv('COMPLAINT_PROFILE',raising=False)
    path=tmp_path/'reports/uncapped/metrics.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'comparison_to_capped':{'recommended_profile':'full'}}))
    with pytest.raises(RuntimeError,match='preserved capped model'):
        load_artifacts(tmp_path)
