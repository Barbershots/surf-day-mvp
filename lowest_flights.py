import glob, numpy as np, pandas as pd
from brockenhurst import approach
import config
BLAT,BLON=config.BROCKENHURST; TLAT,TLON=config.RWY26_THRESHOLD
AIRLINE={'RYR':'Ryanair','EXS':'Jet2','TOM':'TUI Airways','TUI':'TUI fly','VIR':'Virgin Atlantic',
 'EZY':'easyJet','EJU':'easyJet Europe','EIN':'Aer Lingus','BAW':'British Airways','CFE':'BA CityFlyer',
 'WZZ':'Wizz Air','EWG':'Eurowings','DLH':'Lufthansa','KLM':'KLM','AFR':'Air France','BEL':'Brussels Airlines',
 'THY':'Turkish Airlines','PGT':'Pegasus','NJE':'NetJets','LOG':'Loganair','MMO':'Maleth Aero',
 'ELY':'El Al','TAP':'TAP Portugal','SWR':'Swiss','AUA':'Austrian','SAS':'SAS','FIN':'Finnair','URO':'European Cargo','LAV':'AlbaStar','BRO':'2Excel Aviation','CGJ':'Cega (air ambulance?)','SHF':'—'}
arr=pd.read_csv('outputs/sweep/arrivals.csv'); arr['flight_id']=arr['id'].astype('uint64')
lj=arr[arr['category']=='Large jet']
ev=pd.concat([pd.read_parquet(f) for f in glob.glob('data/eghh_events_*.parquet')],ignore_index=True)
ev['flight_id']=ev['flight_id'].astype('uint64')
ev=ev[ev['flight_id'].isin(set(lj['flight_id']))]
a=approach.annotate(ev)
low=a[a['altitude'].between(200,5000)&(a['dist_thr_nm']<12)]
side=low.groupby('flight_id')['longitude'].mean(); rwy26=set(side[side>TLON].index)
a=a[a['flight_id'].isin(rwy26)]
g=a[a['in_corridor']&(a['altitude'].between(300,5000))&(a['d_brock_km']<2.0)]
c=g.sort_values('altitude').groupby('flight_id',as_index=False).first()
c['t']=pd.to_datetime(c['event_time']).dt.tz_localize('UTC').dt.tz_convert('Europe/London')
c=c[c['t']>=pd.Timestamp('2025-01-01',tz='Europe/London')]
meta=lj.drop_duplicates('flight_id').set_index('flight_id')[['flt_id','typecode']]
c=c.join(meta,on='flight_id')
c['airline']=c['flt_id'].astype(str).str[:3].map(lambda p:AIRLINE.get(p,p))
c['altitude_ft']=c['altitude'].round().astype(int)
c['date']=c['t'].dt.strftime('%Y-%m-%d'); c['day']=c['t'].dt.strftime('%a'); c['time']=c['t'].dt.strftime('%H:%M')
c['lat']=c['latitude'].round(4); c['lon']=c['longitude'].round(4)
out=c.sort_values('altitude_ft')[['altitude_ft','flt_id','airline','typecode','date','day','time','lat','lon']]
out=out.rename(columns={'flt_id':'callsign','typecode':'type','altitude_ft':'altitude_ft_over_village'})
out.to_excel('outputs/sweep/lowest_flights_last_year.xlsx',index=False)
out.to_csv('outputs/sweep/lowest_flights_last_year.csv',index=False)
print('flights measured over the village Jan 2025-Jan 2026:',len(out),
      '| <2500ft:',(out['altitude_ft_over_village']<2500).sum(),'| <2000ft:',(out['altitude_ft_over_village']<2000).sum())
pd.set_option('display.width',200,'display.max_columns',20)
print(out.head(40).to_string(index=False))
