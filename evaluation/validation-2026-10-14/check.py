"""Fail on software-policy violations; summarize real runs and score exact controlled ground truth."""
import json
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.evaluate_tracks import evaluate
from football.store import Store


def main():
    output={}
    audit=json.loads((HERE / 'audit.json').read_text(encoding='utf-8'))
    store=Store(ROOT / 'test-results' / HERE.name / 'app-data')
    assert store.get('profile')['name']=='Validation 2026-10-14'
    assert not store.events('attempts')
    media={m['id']:m for m in store.events('media')}
    hashes={}
    main_ids={c['id'] for c in json.loads((HERE / 'reference.json').read_text())['clips'] if not c.get('followup')}
    assert len(main_ids)==33
    for file,digest in json.loads((HERE / 'code-version.json').read_text()).items():
        assert hashlib.sha256((ROOT / file).read_bytes()).hexdigest()==digest, f'Production code changed: {file}'
    for batch in ['detector','colour','followup','benchmark']:
        method='colour' if batch=='colour' else 'detector'
        path=HERE / f'runs-{batch}.json'
        if not path.exists():continue
        runs=json.loads(path.read_text(encoding='utf-8'))
        if batch in ['detector','colour']:
            assert len(runs['clips'])==33 and {e['id'] for e in runs['clips']}==main_ids
        assert not runs['page_errors'],runs['page_errors']
        rows=[]
        for entry in runs['clips']:
            row={'id':entry['id'],'kind':entry['kind'],'window':entry['window'],'selection':entry.get('selection')}
            run=entry.get('analysis')
            if not run:
                assert entry.get('selection',{}).get('error'),entry
                rows.append({**row,'outcome':'refused'});continue
            assert not entry.get('error'),entry['error']
            assert entry['attempts']==0,'Evaluation must never create player scores.'
            assert run['configuration']['method']==method
            source=media[run['media_id']]
            if source['id'] not in hashes:
                with (store.media / source['filename']).open('rb') as file:
                    hashes[source['id']]=hashlib.file_digest(file,'sha256').hexdigest()
            assert run['media_sha256']==source['sha256']==hashes[source['id']]
            assert run['report']['status'] in ['SUSPECT','UNMEASURABLE'],'Unset correctness limits must never pass.'
            assert not run['report']['quality']['configured'] and not run['report']['quality']['validated']
            assert run['configuration']['reseeds']==[]
            times=[s['time'] for s in run['samples']]
            assert all(a<b for a,b in zip(times,times[1:])),entry['id']
            assert len(times)==round((run['end']-run['start'])*10),entry['id']
            for prompt in entry['loss_prompts']:
                lost=prompt['time']
                if 'forward' in prompt['status']:
                    assert all(not s['found'] for s in run['samples'] if s['time']>=lost),entry['id']
                else:
                    assert all(not s['found'] for s in run['samples'] if s['time']<=lost),entry['id']
            found=[i for i,s in enumerate(run['samples']) if s['found']]
            row.update(outcome='tracked',samples=len(times),detections=len(found),coverage=run['report']['coverage'],status=run['report']['status'],elapsed_ms=entry['elapsed_ms'],loss_prompts=entry['loss_prompts'],found_indices=found,contact_proposals=run['candidates'],quality=run['report']['quality'])
            labels=HERE / (entry['id']+'-labels.json')
            if labels.exists():
                row['controlled_accuracy']=evaluate(json.loads(labels.read_text(encoding='utf-8')),run,allow_implementer=True)
                assert row['controlled_accuracy']['counts']['unlabelled']==0
            elif batch!='benchmark':
                review=audit['reviews'][batch][entry['id']]
                assert review['reviewed_indices']==found, f'Incomplete identity audit: {entry["id"]}'
                assert review['analysis_sha256']==hashlib.sha256(json.dumps(run,sort_keys=True).encode()).hexdigest()
                assert set(review['wrong_indices'])<=set(found)
                assert set(review['uncertain_indices'])<=set(found)
                assert not set(review['wrong_indices']) & set(review['uncertain_indices'])
                for i in found:
                    frame=ROOT / 'test-results' / HERE.name / 'reference-frames' / entry['id'] / f"{run['samples'][i]['time']:.3f}.png"
                    assert frame.exists(), f'Missing audit evidence: {frame}'
                row['implementer_identity_audit']={**review,'correct':len(found)-len(review['wrong_indices'])-len(review['uncertain_indices']),'wrong':len(review['wrong_indices']),'uncertain':len(review['uncertain_indices'])}
            rows.append(row)
        output[batch]={'policy_checks':'PASS','page_errors':runs['page_errors'],'clips':rows}
    cancel=json.loads((HERE / 'cancel-results.json').read_text())
    assert cancel['status']=='PASS' and cancel['before']==cancel['after'] and not cancel['page_errors']
    assert cancel['before']['attempts']==0
    (HERE / 'results.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    for method,result in output.items():
        print(method,result['policy_checks'])
        for row in result['clips']:
            print(row['id'],row['outcome'],row.get('coverage'),row.get('controlled_accuracy',{}).get('counts'))


if __name__=='__main__':main()
