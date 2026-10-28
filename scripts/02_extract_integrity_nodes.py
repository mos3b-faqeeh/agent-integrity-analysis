import json,glob,sys,csv
J=sys.argv[1]; rows=[]
for f in glob.glob(f'{J}/*/paper*/consensus.json'):
    c=json.load(open(f))
    for key,nd in c['nodes'].items():
        if nd['gate']!='G1' or nd['role'] not in ('required','conditional','composite_member'): continue
        r=nd.get('repeat') or 1; d=f.rsplit('/',1)[0]
        v=json.load(open(f'{d}/repeat_{r:02d}/integrity_check_rubric.json'))['nodes']
        n=v.get(key.split(':',1)[1]); 
        if not n: continue
        rows.append(dict(model=c['model'],paper=c['paper'],node=key,status=nd['status'],majority=nd.get('repeat') is not None,value=n.get('value'),conf=n.get('confidence'),
                         reason=(n.get('reason') or '').replace('\n',' '),n_evidence=len(n.get('evidence') or [])))
w=csv.DictWriter(open('g1_nodes.csv','w',newline=''),fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print(len(rows),'G1 node rows;',sum(r['status']=='fail' for r in rows),'fail')
