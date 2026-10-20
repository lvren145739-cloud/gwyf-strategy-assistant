"""Reviewed labels for the candidate contact sheets; indices frozen to IDs first."""
from pathlib import Path
import json
r=Path('/workspace/vision-prototype/research');d=r/'v3-data';rows=json.loads((d/'candidates.json').read_text())
# rank, suit (spades/hearts/diamonds/clubs=0/1/2/3), quarter turns to upright.
labels={0:('5',1,0),1:('9',3,0),2:('BACK',4,0),3:('2',1,0),4:('5',1,0),5:('9',3,0),7:('BACK',4,0),8:('2',1,0),10:('5',1,0),11:('9',3,0),12:('2',1,0),13:('BACK',4,0),16:('2',2,0),18:('5',1,0),19:('2',1,0),20:('9',3,0),21:('2',2,0),22:('BACK',4,0),23:('A',0,0),27:('9',3,0),28:('BACK',4,0),29:('K',3,0),31:('3',1,0),33:('BACK',4,0),34:('9',2,0),35:('3',1,0),36:('Q',1,0),37:('3',1,0),38:('9',2,0),39:('10',1,0),41:('A',1,1),42:('7',3,0),43:('8',3,0),46:('2',2,0),47:('A',1,0),50:('8',3,0),51:('2',2,0),53:('J',0,0),55:('7',3,0),56:('8',3,0),57:('2',2,0),61:('8',3,0),62:('J',0,0),64:('A',1,0),66:('10',3,0),67:('J',2,0),68:('3',2,0),73:('K',2,0),80:('K',2,0),83:('K',1,0),87:('K',2,0),90:('K',1,0),93:('6',2,0),94:('8',2,0),96:('6',3,0),98:('8',0,0),102:('A',1,1),103:('9',2,0),104:('5',3,0),106:('2',1,0),107:('K',0,0),110:('K',2,1),111:('2',1,1),123:('6',1,3),124:('7',2,3),137:('7',3,0),138:('9',0,0),139:('J',2,0),152:('8',1,1),153:('7',2,1),272:('BACK',4,0),307:('A',1,1),309:('10',3,0),313:('3',2,0),331:('5',1,0),332:('9',3,0),334:('BACK',4,0),336:('2',1,0),342:('5',1,0),344:('2',1,0),346:('2',2,0),347:('A',0,0)}
# Cards with missing glyphs and merged adjacent cards are not labelled background.
ignore={49,58,59,63,81,88,99,108,109,121,122,131,145,151,155,156,168,188,191,196,213,219,220,221,234,236,237,238,239,244,254,267,270,271,308}
reviewed=[]
for i,c in enumerate(rows):
 c=dict(c)
 if i in labels:
  rank,suit,k=labels[i];c.update(rank=rank,suit=suit,rotation=k,label='back' if rank=='BACK' else 'face')
  # The complete hand around t2071 is kept out, including near-neighbour frames.
  c['split']='holdout-hand' if c['frame'].startswith('poker-a/0057') else 'train'
 elif i in ignore:c.update(label='ignore',split='ignore')
 else:c.update(label='background',split='train')
 reviewed.append(c)
(d/'reviewed-initial.json').write_text(json.dumps(reviewed,indent=2))
print(len(labels),'face/back labels,',len(ignore),'ignored ambiguous crops,',sum(x['label']=='background' for x in reviewed),'backgrounds')
