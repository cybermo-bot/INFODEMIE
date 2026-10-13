import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'../apps/web');
const file=path.join(root,'package.json');
const pkg=JSON.parse(fs.readFileSync(file,'utf8'));
for(const group of ['dependencies','devDependencies'])for(const name of Object.keys(pkg[group]))pkg[group][name]=JSON.parse(fs.readFileSync(path.join(root,'node_modules',name,'package.json'),'utf8')).version;
pkg.scripts.format='prettier --write app next.config.ts tsconfig.json';
pkg.scripts['format:check']='prettier --check app next.config.ts tsconfig.json';
fs.writeFileSync(file,JSON.stringify(pkg,null,2)+'\n');
