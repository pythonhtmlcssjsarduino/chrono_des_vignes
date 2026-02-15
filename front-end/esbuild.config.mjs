import * as esbuild from "esbuild";
import inlineImport from 'esbuild-plugin-inline-import'
import tailwindPlugin from "esbuild-plugin-tailwindcss";
import postcss from 'postcss';
import postcssImport from 'postcss-import';
import tailwindcss from '@tailwindcss/postcss';
import fs from 'fs';
import path from 'path'

async function transformCss(content, args){
    if (args.path.endsWith('.css')) {
        const tailwind = await postcss([
            postcssImport(),
            tailwindcss({
                content:[
                    './ts/*.ts',
                ]
            }),
        ]).process(content, { from: args.path })
        const result = await esbuild.transform(tailwind.css, {loader:'css', minify:true})
        return result.code
    }
    return content
}
const tsDir = 'ts';
const entryPoints = fs.readdirSync(tsDir)
  .filter(file => file.startsWith('.') || !file.endsWith('.ts') ? false : /^[A-Z]/.test(file))
  .map(file => path.join(tsDir, file));

const commun = {
    entryPoints:entryPoints,
    outdir:'../chrono_des_vignes/static/js',
    loader:{
        '.css':'css',
        '.png':'file',
        '.svg':'file',
        '.jpg':'file',
        '.jpeg':'file',
    },
    format:'esm',
    bundle:true,
    publicPath:'/static/js',
    plugins: [
        inlineImport({
            transform:transformCss,
        }),
        tailwindPlugin({
            
        }),
    ],
}

if(process.argv.includes('--watch')){
    const watch ={
        ...commun,
        splitting: process.argv.includes('--splitting'),
        sourcemap:true,
    }
    const ctx = await esbuild.context(watch);
    ctx.watch();
    console.log('watching...');
}else{
    const build = {
        ...commun,
        splitting: true,
        sourcemap:process.argv.includes('--sourcemap'),
        minify:!process.argv.includes('--sourcemap'),
    }
    esbuild.build(build);
}