from pathlib import Path
import sys
import json
import zipfile
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from complaint_project import normalize_text, make_splits, detect_signals, SOURCE_SHA256
from api import app, load_artifacts, predict_text
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]


def test_normalization_groups_variable_identifier_templates():
    assert normalize_text('Report XXXX account 1234 https://example.com') == normalize_text('Report XX account 9876 https://other.com')
    assert 'fraud' in normalize_text('Fraud on my XXXX account 123456')


def test_temporal_splits_are_disjoint_and_do_not_move_late_rows_into_training():
    records=[]
    for label in ('bank account','credit card'):
        for date,n in [('2025-01-15',25),('2025-02-12',5),('2025-02-20',6)]:
            for i in range(n):
                identity=f'{label}-{date}-{i}'
                records.append(dict(complaint_id=identity,date_received=date,product=label,clean_text=identity,text_hash=identity))
    splits,manifest=make_splits(pd.DataFrame(records),'full')
    assert splits['train'].date_received.max()<'2025-02-10'
    assert splits['test'].date_received.min()>='2025-02-17'
    assert len(splits['test'])==12
    assert manifest['normalized_hash_overlap']==0


def test_duplicate_leakage_is_rejected():
    rows=[dict(complaint_id=str(i),date_received='2025-01-01',product='A' if i<20 else 'B',clean_text=str(i),text_hash=str(i)) for i in range(40)]
    rows += [dict(complaint_id='valid',date_received='2025-02-12',product='A',clean_text='same',text_hash='0'),
             dict(complaint_id='test',date_received='2025-02-20',product='B',clean_text='other',text_hash='unique')]
    with pytest.raises(AssertionError,match='Duplicate leakage'):
        make_splits(pd.DataFrame(rows),'full')


def test_partial_final_week_is_excluded_from_signal_detection():
    rows=[]
    for week in pd.date_range('2025-01-06',periods=8,freq='7D'):
        rows.extend([dict(week=week.strftime('%Y-%m-%d'),product='A',issue='issue',complaints=10),
                     dict(week=week.strftime('%Y-%m-%d'),product='B',issue='other',complaints=90)])
    frame=pd.DataFrame(rows)
    frame.loc[(frame.week=='2025-02-17')&(frame['product']=='A'),'complaints']=100
    result=detect_signals(frame,'2025-01-01','2025-02-28')
    assert result['week_start']=='2025-02-17'
    assert '2025-02-24' not in result['baseline_weeks']
    assert result['items'][0]['issue']=='issue'
    assert result['items'][0]['volume_ratio']==10


@pytest.fixture(scope='module')
def artifacts():
    assert (ROOT/'models/smoke/classifier.joblib').exists(), 'Run the smoke profile before integration tests.'
    return load_artifacts(ROOT,'smoke')


def test_portable_model_and_source_manifest(artifacts):
    assert artifacts['data']['source']['source_sha256']==SOURCE_SHA256
    assert artifacts['data']['source']['database_rows']==811019
    assert artifacts['profile']=='smoke'
    text='My bank has charged an unexpected fee on my checking account and has not explained why this money was taken.'
    result=predict_text(artifacts,text)
    assert result['category'] in artifacts['model'].classes_
    assert 0<=result['score']<=1
    assert len(result['alternatives'])==3


def test_short_and_unrecognizable_inputs_require_review(artifacts):
    with pytest.raises(ValueError):
        predict_text(artifacts,'1234 XXXX')
    with pytest.raises(ValueError):
        predict_text(artifacts,' '.join(['qzjxvbl']*20))


def test_api_contract_and_validation(artifacts):
    with TestClient(app) as client:
        assert client.get('/api/health').json()['status']=='ok'
        assert client.get('/api/summary').json()['historical'] is True
        assert client.post('/api/classify',json={'text':'too short'}).status_code==422
        result=client.post('/api/classify',json={'text':'My credit card shows a purchase that I did not authorize and the card issuer has refused to investigate my dispute.'})
        assert result.status_code==200
        assert 'human_review' in result.json()


def test_export_archive_has_only_expected_result_folders(artifacts):
    with zipfile.ZipFile(ROOT/'tests/fixtures/smoke_results.zip') as z:
        assert z.testzip() is None
        assert 'models/smoke/classifier.joblib' in z.namelist()
        assert 'reports/smoke/metrics.json' in z.namelist()
        assert not any('.sqlite' in name or 'data/raw' in name for name in z.namelist())


def test_selection_uses_validation_and_test_labels_are_fixed(artifacts):
    metrics=artifacts['data']['model']
    eligible=[r for r in metrics['validation_models'] if r['model']!='majority_baseline']
    assert metrics['selected_model']==max(eligible,key=lambda r:r['macro_f1'])['model']
    assert np.array(metrics['confusion_matrix']).shape==(len(metrics['labels']),len(metrics['labels']))
    split=json.loads((ROOT/'reports/smoke/split_manifest.json').read_text())
    assert np.array(metrics['confusion_matrix']).sum()==split['splits']['test']['rows']


def test_sql_aggregates_keep_full_population_and_explicit_denominators(artifacts):
    data=artifacts['data']['analytics']
    assert sum(row['complaints'] for row in data['products'])==811019
    assert sum(row['complaints'] for row in data['daily'])==811019
    for row in data['products']:
        assert row['timely']<=row['timeliness_known']<=row['complaints']
        assert row['narratives']<=row['complaints']


def test_results_import_rejects_unsafe_paths_before_writing(tmp_path):
    from import_results import import_results
    for name in ('../escape.txt','C:/escape.txt','models/../../escape.txt'):
        bad=tmp_path/'bad.zip'
        with zipfile.ZipFile(bad,'w') as z:
            z.writestr(name,'bad')
        with pytest.raises(ValueError,match='Unsafe'):
            import_results(bad,tmp_path/'target')
    assert not (tmp_path/'escape.txt').exists()


def test_results_import_preserves_previous_files_and_validates_model(artifacts,tmp_path):
    from import_results import import_results
    output=tmp_path/'imported'
    destination=output/'models/smoke/classifier.joblib'
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b'previous version')
    result=import_results(ROOT/'tests/fixtures/smoke_results.zip',output)
    backup=Path(result['backup'])/'previous/models/smoke/classifier.joblib'
    assert backup.read_bytes()==b'previous version'
    imported=load_artifacts(output,'smoke')
    assert imported['data']['model']['selected_model']==artifacts['data']['model']['selected_model']
