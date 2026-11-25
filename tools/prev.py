import re,os,sys,shutil
src,dst,base=sys.argv[1:4]
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src,dst)
names=[n for n in os.listdir(src) if n not in('.git',)]
alt='|'.join(re.escape(os.path.splitext(n)[0] if False else n) for n in names)
pat=re.compile(r'''(["'(=\s,])/((?:%s)(?=[/"'?#)\s.,]|$))'''%alt)
home=re.compile(r'''(href|action)=(["'])/\2''')
n=0
for r,_,fs in os.walk(dst):
    for f in fs:
        if f.endswith(('.html','.css','.js','.xml','.json','.webmanifest')):
            p=os.path.join(r,f); s=open(p,encoding='utf8').read()
            t=pat.sub(lambda m:m.group(1)+'/'+base+'/'+m.group(2),s)
            t=home.sub(lambda m:f'{m.group(1)}={m.group(2)}/{base}/{m.group(2)}',t)
            if t!=s: open(p,'w',encoding='utf8').write(t); n+=1
print(n,'fichiers modifiés')
