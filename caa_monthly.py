import subprocess, re, json
months=['january','february','march','april','may','june','july','august','september','october','november','december']
def curl(u): return subprocess.run(['curl','-sSL','--max-time','45',u],capture_output=True,text=True).stdout
res={}
for year in (2023,2024,2025):
    for mi,mon in enumerate(months,1):
        page=f"https://www.caa.co.uk/data-and-analysis/uk-aviation-market/airports/uk-airport-data/uk-airport-data-{year}/{mon}-{year}/"
        html=curl(page)
        link=None
        for a in re.finditer(r'href="(/Documents/Download/[0-9]+/[a-f0-9-]+/[0-9]+)"[^>]*>(.*?)</a>', html, re.S|re.I):
            label=re.sub(r'<[^>]+>','',a.group(2)).strip()
            if 'Table 03' in label and 'CSV' in label:
                link=a.group(1); break
        if not link:
            print(year,mi,mon,'NO-LINK',flush=True); continue
        csv=curl('https://www.caa.co.uk'+link)
        tot=None
        for line in csv.splitlines():
            if 'BOURNEMOUTH' in line.upper():
                p=line.split(','); tot=int(p[4]); break
        res[f'{year}-{mi:02d}']=tot
        print(year,mi,mon,tot,flush=True)
json.dump(res,open('caa_monthly_movements.json','w'),indent=0)
print('DONE',len(res),flush=True)
