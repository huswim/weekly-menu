import json
from pathlib import Path
root=Path(__file__).parent/'dist'
a=json.loads((root/'allergies.json').read_text())
extras=[['스위트청귤','후레쉬업레몬라임'],['하루요거트사과','프룻프룻망고'],['스위트매실','스위트플럼'],['머스캣코코주스','스위트자몽'],['제주한라봉퓨레','']]
out=[]
for i,rows in enumerate(a):
 meals=[]
 for j,n in enumerate(['조식','중식','석식']):
  corners=[]
  for sec in ([n] if j==0 else [n+'A',n+'B']):
   r=[x for x in rows if x['section']==sec and x['name'] not in sum(extras,[]) and not x['name'].startswith(('건강음료/','그린샐러드&드레싱/'))]
   if r:corners.append({'label':'한식 메뉴' if j==0 else sec[-1]+' 코너','items':r[:5 if j==0 else 6]})
  extra=[x for x in rows if x['section']==n][5:] if j==0 else [x for x in rows if x['name']==extras[i][j-1]]
  meals.append({'corners':corners,'extra':extra,'allergy':[x for x in rows if x['section'].startswith(n)]})
 out.append({'day':['월','화','수','목','금'][i],'date':19+i,'meals':meals})
(root/'menu.json').write_text(json.dumps(out,ensure_ascii=False))
